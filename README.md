# Assistant Code du travail (RAG)

Assistant juridique qui répond en langage naturel à des questions sur le droit du travail français, en citant systématiquement les articles du Code du travail sur lesquels il s'appuie.

Projet réalisé par Abdel Akim Njankouo — M2 MD5, Data & IA.

## Avertissement

> Cet assistant ne fournit pas de conseil juridique. Consultez un avocat ou l'inspection du travail pour votre situation personnelle.

Cette mention est garantie par le code (pas seulement demandée dans le prompt) : voir la section "Traçabilité et fiabilité de l'avertissement" ci-dessous.

## Architecture

```
.
├── corpus.json              # 13 articles du Code du travail, 5 thèmes
├── prompts/
│   └── system_prompt.txt    # prompt système à trous ({{Chunks}})
├── src/
│   ├── config.py            # config centralisée (modèles, chemins, clé API)
│   ├── vector_db.py          # classe VectorDB : creation/rechargement ChromaDB
│   ├── rag.py                # classe RAG : retrieval + prompt + appel Groq
│   └── cli.py                # interface en ligne de commande
├── chroma_db/                # base vectorielle persistée (ignorée par git)
├── .env                      # clé API Groq (jamais versionnée)
├── .env.example
├── .gitignore
└── requirements.txt
```

Le corpus couvre 5 thèmes : durée du travail et heures supplémentaires, congés payés, contrat de travail (CDI/CDD), licenciement, rupture conventionnelle.

## Installation

```bash
python -m venv env
# Windows :
.\env\Scripts\activate
# macOS/Linux :
source env/bin/activate

pip install -r requirements.txt
```

Copier `.env.example` en `.env` et y renseigner sa clé API Groq (obtenue sur console.groq.com) :
```
GROQ_API_KEY=ta_cle_ici
```

## Lancement

Depuis le dossier `src/` :
```bash
cd src
python cli.py
```

Au premier lancement, la base vectorielle est créée à partir de `corpus.json` (télécharge le modèle d'embedding, encode les 13 articles). Aux lancements suivants, la base existante est rechargée sans réindexation.

Poser une question, taper `quitter` (ou `exit`/`q`) pour sortir.

## Choix techniques et réponses aux questions de réflexion

### 1. Granularité du chunking

Choix retenu : **un article = un chunk**, sans découpage supplémentaire.

Les articles du Code du travail sont déjà courts, denses et autonomes (une seule règle par article dans la majorité des cas) : les découper davantage romprait des phrases en plein milieu sans gain de pertinence. Regrouper par section aurait l'avantage de donner plus de contexte au LLM en un seul chunk, mais l'inconvénient de diluer la précision du retrieval (un chunk "section entière" répond moins précisément à une question ciblée, et rend la citation d'un article précis plus ambiguë).

Une approche hybride est envisageable : indexer chaque article séparément (comme ici, pour la précision du retrieval) tout en gardant en métadonnée la section à laquelle il appartient (fait dans ce projet, champ `section`), pour permettre plus tard une recherche filtrée par thème.

### 2. Traçabilité du numéro d'article

Le numéro d'article est stocké à **deux endroits complémentaires** :
- comme identifiant du document dans ChromaDB (`ids=[chunk["id"], ...]`), donc récupérable directement dans les résultats du retrieval ;
- en clair devant chaque chunk envoyé au LLM (`[Article L3121-27 - titre - section]`, voir `RAG._format_chunks`), pour qu'il n'ait qu'à le recopier plutôt qu'à en inventer un.

Pour garantir que le LLM cite correctement : le prompt système l'exige explicitement (règle 3) et la température est basse (0.2) pour limiter l'improvisation. En complément, le code vérifie après coup quels identifiants apparaissent réellement dans le texte généré (`articles_sources` dans `RAG.answer_question`), pour n'afficher à l'utilisateur que les sources effectivement citées — pas tous les chunks envoyés, dont certains peuvent être ignorés à raison par le LLM.

Limite connue : cette vérification est une simple recherche de sous-chaîne (`"L1234-1" in answer`) ; une variante d'écriture de l'article (avec espace, point, etc.) ne serait pas détectée.

### 3. Fraîcheur du corpus

Le corpus a été constitué manuellement en juillet 2026 à partir du texte en vigueur sur Légifrance à cette date. Le droit du travail évolue (lois, ordonnances) ; ce projet ne vérifie pas automatiquement l'obsolescence des articles indexés. L'avertissement juridique final, garanti par le code sur chaque réponse, sert notamment de garde-fou pour ce risque : la personne est systématiquement renvoyée vers l'inspection du travail ou un avocat, qui disposeront du texte à jour.

Piste d'amélioration non implémentée : stocker une date de version par article et l'afficher, ou vérifier périodiquement sur Légifrance si un article a été modifié depuis son indexation.

### 4. Réponses conditionnelles

Le prompt système (règle 6) impose que, lorsque la réponse dépend de facteurs non connus du système (taille de l'entreprise, convention collective, ancienneté exacte), l'assistant donne la réponse générale qui découle des articles fournis tout en signalant explicitement les réserves, plutôt que de choisir arbitrairement une hypothèse. Exemple observé en test : sur la question du préavis de licenciement, la réponse rappelle les trois tranches d'ancienneté et précise que ces durées ne s'appliquent qu'à défaut de disposition plus favorable (convention collective, contrat de travail, usages).

### 5. Frontière du conseil juridique

Le prompt système (règle 7) distingue explicitement les questions factuelles couvertes par le Code ("combien de jours de congés ?") des questions d'interprétation sur un cas personnel ("mon licenciement est-il abusif ?"). Dans le second cas, l'assistant est instruit de ne pas se prononcer sur la situation individuelle, d'expliquer le cadre légal général tiré des articles fournis, et d'orienter vers un professionnel — ce qui est cohérent avec l'avertissement juridique final, systématiquement présent.

## Score de confiance (amélioration du Jalon 6)

À chaque question, le système calcule un score de confiance à partir de la distance cosinus du meilleur chunk retrouvé (`1 - distance`, arrondi à 2 décimales). Le seuil de 0.75 (en distance) a été calibré empiriquement sur les 5 questions de test du Jalon 3 : les 4 bonnes réponses avaient une distance ≤ 0.70, tandis que le seul échec observé (mauvais article remonté pour "Comment fonctionne la rupture conventionnelle ?") avait une distance de 0.81. En dessous du seuil de confiance, la réponse est préfixée d'un avertissement visible plutôt que bloquée, conformément à l'esprit du sujet ("avertir l'utilisateur avant de répondre").

Testé avec succès sur des questions clairement hors corpus (score de confiance observé : 0.01 à 0.24), le système reste honnête plutôt que d'inventer une réponse.

## Compte-rendu

Voir [COMPTE_RENDU.md](./COMPTE_RENDU.md) pour les difficultés rencontrées, les décisions de conception, et ce qui serait fait avec plus de temps.
