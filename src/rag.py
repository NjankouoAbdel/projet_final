"""
Orchestrateur du RAG : récupère les chunks pertinents, construit le prompt,
appelle le LLM Groq, et garantit que l'avertissement juridique est toujours présent.
"""

import json
from groq import Groq

from config import GROQ_API_KEY, LLM_MODEL, CORPUS_PATH, BASE_DIR
from vector_db import VectorDB

PROMPT_PATH = str(BASE_DIR / "prompts" / "system_prompt.txt")

DISCLAIMER = (
    "Cet assistant ne fournit pas de conseil juridique. "
    "Consultez un avocat ou l'inspection du travail pour votre situation personnelle."
)


class RAG:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)

        # Au premier lancement, la base n'existe pas encore : on lui donne le corpus.
        # Si elle existe déjà, VectorDB la recharge et ignore chunks.
        with open(CORPUS_PATH, encoding="utf-8") as f:
            corpus = json.load(f)
        self.vector_db = VectorDB(chunks=corpus)

    @staticmethod
    def read_file(path):
        with open(path, encoding="utf-8") as f:
            return f.read()

    def _format_chunks(self, results):
        """Transforme le résultat brut de ChromaDB en texte numéroté avec
        métadonnées, prêt à être inséré dans le prompt. La traçabilité de
        l'article (question 2 du sujet) passe par CE numéro affiché ici :
        le LLM le recopie dans sa réponse plutôt que d'en inventer un."""
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        ids = results["ids"][0]

        formatted = []
        for i, (doc, meta, article_id) in enumerate(zip(documents, metadatas, ids), start=1):
            formatted.append(
                f"[Article {article_id} - {meta['titre']} - Section : {meta['section']}]\n{doc}"
            )
        return "\n\n".join(formatted)

    def answer_question(self, question, n_chunks=3):
        # 1. Retrieval : les chunks les plus proches de la question
        results = self.vector_db.retrieve(question, n=n_chunks)
        chunks_text = self._format_chunks(results)

        # 2. Prompt à trous : on lit le fichier à chaque question (permet de
        # modifier le prompt sans toucher au code), et on remplace le marqueur.
        system_prompt_template = self.read_file(PROMPT_PATH)
        system_prompt = system_prompt_template.replace("{{Chunks}}", chunks_text)

        # 3. Appel au LLM, température basse pour limiter l'improvisation
        response = self.client.chat.completions.create(
            model=LLM_MODEL,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
        )
        answer = response.choices[0].message.content

        # 4. Garantie déterministe de l'avertissement juridique : même si le
        # LLM l'a oublié (ça arrive), on s'assure qu'il est présent. C'est le
        # code, pas le prompt seul, qui rend cette contrainte fiable à 100%.
        if DISCLAIMER not in answer:
            answer = answer.strip() + "\n\n" + DISCLAIMER

        # 5. On ne garde, comme "sources" affichées, que les articles que le
        # LLM a réellement cités dans le texte de sa réponse — pas tous ceux
        # qu'on lui a envoyés (certains étaient hors sujet et il les a ignorés
        # à raison, cf. règle 2 du prompt). On vérifie la présence de chaque
        # identifiant d'article (ex: "L1234-1") comme sous-chaîne de la réponse.
        all_retrieved_ids = list(results["ids"][0])
        cited_ids = [
            article_id for article_id in all_retrieved_ids if article_id in answer
        ]

        return {
            "reponse": answer,
            "articles_sources": cited_ids,
        }


if __name__ == "__main__":
    # Test rapide : python src/rag.py
    rag = RAG()

    test_question = "Quelle est la durée légale du préavis pour un CDI ?"
    result = rag.answer_question(test_question)

    print(f"\nQuestion : {test_question}")
    print(f"\nRéponse :\n{result['reponse']}")
    print(f"\nArticles sources : {result['articles_sources']}")
