"""
Configuration centrale du projet.
Tous les autres fichiers du projet lisent les noms de modèles ICI,
jamais écrits en dur ailleurs dans le code.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Charge les variables du fichier .env (notamment GROQ_API_KEY) dans l'environnement
load_dotenv()

# Chemin absolu vers la racine du projet, quel que soit le dossier
# depuis lequel on lance le script. __file__ = ce fichier (src/config.py),
# .parent = src/, .parent.parent = racine du projet.
BASE_DIR = Path(__file__).resolve().parent.parent

# Noms des modèles, à un seul endroit
EMBEDDING_MODEL = "distiluse-base-multilingual-cased-v2"
LLM_MODEL = "llama-3.3-70b-versatile"

# Clé API Groq, lue depuis le fichier .env
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY est manquante. Vérifie que le fichier .env existe "
        "à la racine du projet et contient GROQ_API_KEY=ta_cle."
    )

# Chemin où la base vectorielle sera sauvegardée sur disque
CHROMA_DB_PATH = str(BASE_DIR / "chroma_db")

# Chemin vers le corpus JSON
CORPUS_PATH = str(BASE_DIR / "corpus.json")
