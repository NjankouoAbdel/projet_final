"""
Interface en ligne de commande de l'assistant Code du travail.
Boucle : saisie de la question -> affichage de la réponse, des articles
sources, et sortie propre sur commande.
"""

from rag import RAG


def main():
    print("=" * 60)
    print("Assistant Code du travail (RAG)")
    print("Pose une question sur le droit du travail français.")
    print("Tape 'quitter' (ou 'exit', 'q') pour sortir.")
    print("=" * 60)

    # L'instanciation de RAG() charge (ou crée) la base vectorielle une seule
    # fois, avant la boucle : on ne veut surtout pas la recharger à chaque
    # question, seulement l'interroger.
    print("\nChargement de l'assistant...")
    rag = RAG()
    print("Assistant prêt.\n")

    while True:
        question = input("Votre question > ").strip()

        if question.lower() in ("quitter", "exit", "q", ""):
            if question.lower() == "":
                continue  # on ignore une entrée vide, mais on ne quitte pas
            print("\nAu revoir !")
            break

        try:
            result = rag.answer_question(question)
        except Exception as e:
            # On protège la boucle : une erreur sur une question (ex: souci
            # réseau ponctuel avec Groq) ne doit pas planter tout le programme.
            print(f"\n[Erreur lors du traitement de la question : {e}]\n")
            continue

        print(f"\n{result['reponse']}\n")

        if result["articles_sources"]:
            sources = ", ".join(result["articles_sources"])
            print(f"(Articles cités : {sources})\n")
        else:
            print("(Aucun article spécifique cité dans cette réponse)\n")

        print("-" * 60)


if __name__ == "__main__":
    main()
