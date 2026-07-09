# Compte-rendu — Assistant Code du travail (RAG)

Abdel Akim Njankouo — M2 MD5, Data & IA

## Difficultés rencontrées

**Bug silencieux dans la détection d'existence de la base ChromaDB.** La première version vérifiait si la base existait déjà en testant si le dossier `chroma_db/` était présent et non vide sur le disque. Cette vérification était fausse : `chromadb.PersistentClient` crée déjà des fichiers dans ce dossier dès son instanciation, avant même la création d'une collection. Le programme tentait donc systématiquement de recharger une collection inexistante, et plantait sur `metadata["embedding_model"]` (qui valait `None`). Corrigé en interrogeant directement ChromaDB (`client.list_collections()`) plutôt que le système de fichiers — une bonne illustration du principe "ne pas deviner l'état d'un système à partir d'indices indirects quand on peut lui demander directement".

**Échec de retrieval sur la rupture conventionnelle.** Détecté au Jalon 3 : la question "Comment fonctionne la rupture conventionnelle ?" ne faisait pas remonter l'article attendu (L1237-11) en tête des résultats, mais des articles génériques sur le contrat de travail. Cause probable : seulement 2 articles du corpus couvraient ce thème à ce stade, et l'écart de registre entre une question formulée familièrement et le style juridique formel des articles a pu dérouter le modèle d'embedding. Ce cas concret, plutôt que d'être ignoré, a directement motivé le choix de l'amélioration du Jalon 6.

**Environnement de développement Windows.** Plusieurs frictions pratiques sans lien direct avec le RAG lui-même : la commande `python` non reconnue par défaut (nécessitant `py`, l'exécutable étant bien installé mais absent du PATH), des fichiers téléchargés atterrissant dans `Downloads` plutôt que d'être directement dans le dossier du projet (source d'erreurs "fichier introuvable" à répétition), et une authentification `gh auth login` (GitHub CLI) qui a nécessité plusieurs tentatives avant d'aboutir.

## Décisions de conception

**Un article = un chunk**, sans découpage supplémentaire ni regroupement par section : les articles du Code du travail sont déjà courts et autonomes, un découpage plus fin romprait des phrases sans gain, un regroupement par section diluerait la précision du retrieval.

**Avertissement juridique garanti par le code, pas seulement par le prompt.** Le prompt système demande explicitement la mention finale, mais un LLM peut l'omettre occasionnellement. Le code vérifie après génération que la mention exacte est présente et l'ajoute sinon — une contrainte non-négociable du sujet ne peut pas reposer uniquement sur la bonne volonté du modèle.

**Score de confiance calibré empiriquement, pas une valeur arbitraire.** Le seuil de 0.75 (distance cosinus) a été choisi après avoir mesuré les distances réelles sur les 5 questions de test du Jalon 3 : les 4 bonnes réponses avaient une distance ≤ 0.70, le seul échec observé était à 0.81. Le seuil sépare ces deux groupes.

## Ce qui serait fait avec plus de temps

- Élargir le corpus au-delà des 13 articles actuels (l'option manuelle du sujet est explicitement plafonnée en note sur ce critère), en particulier enrichir les thèmes sous-représentés comme la rupture conventionnelle et le contrat de travail.
- Une vérification de citation plus robuste que la simple recherche de sous-chaîne, capable de reconnaître différentes écritures d'un même numéro d'article ("L. 1234-1" vs "L1234-1").
- Un suivi de fraîcheur du corpus (date de dernière vérification par article face aux évolutions du Code du travail).
- Tester la piste de la reformulation de question (rapprocher le vocabulaire familier des utilisateurs du registre juridique des articles), écartée au profit du score de confiance faute de temps.
