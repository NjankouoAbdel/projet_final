"""
Gestion de la base vectorielle ChromaDB.
La classe VectorDB sait faire deux choses seulement :
- si la base existe déjà sur disque : la recharger (pas de réencodage)
- sinon, si on lui donne des chunks : créer la base et l'encoder
"""

import os
import chromadb
from sentence_transformers import SentenceTransformer

from config import EMBEDDING_MODEL, CHROMA_DB_PATH


class VectorDB:
    def __init__(self, chunks=None):
        """
        chunks : liste de dicts {"id", "titre", "texte", "section"} (notre corpus.json),
                 nécessaire uniquement si la base n'existe pas encore sur disque.
        """
        # Un client persistant : les données écrites survivent à l'arrêt du programme.
        # Attention : cette ligne crée déjà le dossier CHROMA_DB_PATH sur disque,
        # même si aucune collection n'existe encore dedans. On ne peut donc PAS
        # se fier à "le dossier existe" pour savoir si on a déjà indexé quelque chose.
        self.client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

        # La bonne vérification : demander à Chroma la liste des collections
        # qu'il connaît déjà, et regarder si la nôtre en fait partie.
        existing_collections = [c.name for c in self.client.list_collections()]
        collection_exists = "code_du_travail" in existing_collections

        if collection_exists:
            self._load_existing()
        elif chunks:
            self._create_new(chunks)
        else:
            raise ValueError(
                "Aucune base existante trouvée sur disque, et aucun chunk fourni "
                "pour en créer une nouvelle. Fournis le corpus (chunks=...) au "
                "premier lancement."
            )

    def _create_new(self, chunks):
        """Crée la collection, encode les chunks, les insère, et retient le
        nom du modèle d'embedding dans les métadonnées de la collection."""
        print(f"Aucune base trouvée : création avec le modèle {EMBEDDING_MODEL}...")

        self.model = SentenceTransformer(EMBEDDING_MODEL)

        # Le nom du modèle est stocké DANS la collection elle-même.
        # C'est ce qui permet, au rechargement, de savoir quel modèle utiliser
        # même si la config du jour a changé entre-temps.
        self.collection = self.client.get_or_create_collection(
            name="code_du_travail",
            metadata={"embedding_model": EMBEDDING_MODEL},
        )

        ids = [chunk["id"] for chunk in chunks]
        documents = [chunk["texte"] for chunk in chunks]
        metadatas = [
            {"titre": chunk["titre"], "section": chunk["section"], "source": "Code du travail"}
            for chunk in chunks
        ]

        # normalize_embeddings=True : les vecteurs sont ramenés à une longueur de 1,
        # ce qui rend la similarité cosinus directement comparable entre les chunks.
        embeddings = self.model.encode(
            documents,
            batch_size=16,
            normalize_embeddings=True,
            show_progress_bar=True,
        )

        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings.tolist(),
            metadatas=metadatas,
        )
        print(f"{len(chunks)} articles indexés et sauvegardés dans {CHROMA_DB_PATH}")

    def _load_existing(self):
        """Recharge une base déjà indexée, sans réencoder le corpus."""
        self.collection = self.client.get_or_create_collection(name="code_du_travail")

        # On relit le nom du modèle DEPUIS la collection, pas depuis config.py,
        # pour garantir que la recherche utilise le même modèle que celui
        # utilisé lors de l'indexation (même si config.py a changé depuis).
        model_name = self.collection.metadata["embedding_model"]
        print(f"Base existante trouvée : rechargement avec le modèle {model_name}...")
        self.model = SentenceTransformer(model_name)

    def retrieve(self, question, n=3):
        """Encode la question et retourne les n chunks les plus proches."""
        question_embedding = self.model.encode([question], normalize_embeddings=True)

        results = self.collection.query(
            query_embeddings=question_embedding.tolist(),
            n_results=n,
        )
        return results


if __name__ == "__main__":
    # Test rapide en ligne de commande : python src/vector_db.py
    import json
    from config import CORPUS_PATH

    with open(CORPUS_PATH, encoding="utf-8") as f:
        corpus = json.load(f)

    db = VectorDB(chunks=corpus)

    # Jeu de test : 5 questions dont on connaît l'article attendu (Jalon 3 du sujet).
    # But : vérifier que le bon article remonte dans le top-k AVANT de brancher le LLM.
    test_cases = [
        ("Quelle est la durée légale du travail ?", "L3121-27"),
        ("Combien de jours de congés payés par mois ?", "L3141-3"),
        ("Quel est le préavis en cas de licenciement ?", "L1234-1"),
        ("Comment fonctionne la rupture conventionnelle ?", "L1237-11"),
        ("Le CDI est-il la forme normale du contrat de travail ?", "L1221-2"),
    ]

    print("\n--- Validation du retrieval (Jalon 3) ---")
    for question, expected_id in test_cases:
        results = db.retrieve(question, n=3)
        retrieved_ids = results["ids"][0]
        found = expected_id in retrieved_ids
        status = "OK" if found else "ECHEC"
        print(f"[{status}] \"{question}\" -> attendu {expected_id}, top-3 = {retrieved_ids}")
