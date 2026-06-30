from rag import RAGSystem

rag = RAGSystem()
rag.add_folder("documents")
rag.build_index()

questions = [
    "Quels sont les symptômes de la dépression ?",
    "Comment soigne-t-on la schizophrénie ?",
    "Qu'est-ce que le trouble bipolaire ?",
]

for q in questions:
    print("\n" + "=" * 70)
    print("QUESTION :", q)
    hits = rag.retrieve(q)
    print("\n--- PASSAGES RÉCUPÉRÉS ---")
    for i, (chunk, score) in enumerate(hits, 1):
        print(f"\n[{i}] source={chunk['source']}  score={score:.3f}")
        print(chunk["text"][:300])
    answer, _ = rag.answer(q)
    print("\n--- RÉPONSE GÉNÉRÉE ---")
    print(answer)