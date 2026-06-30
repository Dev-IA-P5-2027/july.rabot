"""
app.py
------
Interface web Gradio pour discuter avec des documents PDF (RAG).

- Au demarrage, charge automatiquement les PDF du dossier 'documents/'
  (fiches OMS sante mentale preparees par prepare_documents.py).
- Permet aussi de televerser ses propres PDF.
- Repond aux questions en se basant sur les passages recuperes, et
  affiche les sources utilisees.

Lancement :
  python app.py          -> http://localhost:7860
"""

import os

import gradio as gr

from rag import RAGSystem

# Instancie le systeme (charge les modeles une fois)
rag = RAGSystem()

# Pre-charge les documents OMS si le dossier existe
if os.path.isdir("documents"):
    n = rag.add_folder("documents")
    if n:
        print(f"Indexation de {n} passages depuis 'documents/'...")
        rag.build_index()


def index_uploaded(files):
    """Ajoute les PDF televerses puis reconstruit l'index."""
    if not files:
        return "Aucun fichier reçu."
    added = 0
    for f in files:
        path = f.name if hasattr(f, "name") else f
        if str(path).lower().endswith(".pdf"):
            added += rag.add_pdf(path)
    rag.build_index()
    return (f"{added} nouveaux passages indexes. "
            f"Total : {len(rag.chunks)} passages.")


def respond(message, history):
    """Genere une reponse RAG et l'ajoute a l'historique du chat."""
    message = (message or "").strip()
    if not message:
        return history, ""
    if rag.embeddings is None:
        reply = ("Aucun document n'est indexe. Lance d'abord "
                 "`prepare_documents.py`, ou televerse un PDF ci-dessus.")
    else:
        answer, hits = rag.answer(message)
        sources = "\n".join(
            f"• {h[0]['source']} (pertinence {h[1]:.2f})" for h in hits
        )
        reply = f"{answer}\n\n— Sources —\n{sources}"

    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply},
    ]
    return history, ""


with gr.Blocks(title="RAG - Chat avec des PDF (santé mentale OMS)") as demo:
    gr.Markdown(
        "# 💬 RAG — Discuter avec des documents PDF\n"
        "### Base de connaissances : fiches OMS sur les troubles mentaux\n"
        "Pose une question **en français** sur le contenu des documents. "
        "Le système récupère les passages pertinents (embeddings multilingues) "
        "puis génère une réponse en français (mt0)."
    )

    with gr.Row():
        upload = gr.File(label="Ajouter des PDF", file_count="multiple",
                         file_types=[".pdf"])
        index_btn = gr.Button("Indexer les PDF", variant="secondary")
    status = gr.Markdown()

    chatbot = gr.Chatbot(type="messages", height=420, label="Conversation")
    with gr.Row():
        msg = gr.Textbox(
            placeholder="Ex : Quels sont les symptômes de la dépression ?",
            label="Votre question", scale=5,
        )
        send = gr.Button("Envoyer", variant="primary", scale=1)

    gr.Examples(
        examples=[
            "Quels sont les symptômes de la dépression ?",
            "Comment soigne-t-on la schizophrénie ?",
            "Qu'est-ce que le trouble bipolaire ?",
            "Qui est le plus touché par la dépression ?",
        ],
        inputs=msg,
    )

    index_btn.click(index_uploaded, inputs=upload, outputs=status)
    send.click(respond, inputs=[msg, chatbot], outputs=[chatbot, msg])
    msg.submit(respond, inputs=[msg, chatbot], outputs=[chatbot, msg])


if __name__ == "__main__":
    demo.launch()
