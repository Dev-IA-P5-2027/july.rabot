"""
app.py
------
Demo interactive Gradio : traduction EN -> FR avec choix du modele
(Ollama ou HuggingFace) et de la temperature.

- En local      : python app.py  -> http://localhost:7860
- Sur Colab     : demo.launch(share=True) cree un lien public temporaire.
"""

import gradio as gr

from translate import translate_ollama, translate_hf, OLLAMA_MODEL

EXAMPLES = [
    ["Depression is a common mental disorder.", f"Ollama ({OLLAMA_MODEL})", 0.2],
    ["Anxiety disorders are characterized by excessive fear and worry.",
     "HuggingFace (opus-mt)", 0.0],
    ["Many people with mental disorders do not receive the care they need.",
     f"Ollama ({OLLAMA_MODEL})", 0.5],
]


def run(text, model_choice, temperature):
    text = (text or "").strip()
    if not text:
        return "Entre un texte en anglais a traduire."
    try:
        if model_choice.startswith("Ollama"):
            return translate_ollama(text, temperature=temperature)
        return translate_hf(text)
    except Exception as exc:
        return f"Erreur : {exc}"


with gr.Blocks(title="Demo traduction EN->FR (sante mentale)") as demo:
    gr.Markdown(
        "# Demo de traduction EN -> FR\n"
        "### Domaine : troubles mentaux (donnees OMS)\n"
        "Compare un **LLM local (Ollama)** et un **modele HuggingFace (opus-mt)**, "
        "avec une temperature reglable."
    )
    with gr.Row():
        with gr.Column():
            inp = gr.Textbox(label="Texte anglais", lines=4,
                             placeholder="Depression is a common mental disorder.")
            model_choice = gr.Radio(
                [f"Ollama ({OLLAMA_MODEL})", "HuggingFace (opus-mt)"],
                value=f"Ollama ({OLLAMA_MODEL})",
                label="Modele",
            )
            temp = gr.Slider(0.0, 1.0, value=0.2, step=0.1, label="Temperature")
            btn = gr.Button("Traduire", variant="primary")
        with gr.Column():
            out = gr.Textbox(label="Traduction francaise", lines=4)

    gr.Examples(EXAMPLES, inputs=[inp, model_choice, temp])
    btn.click(run, inputs=[inp, model_choice, temp], outputs=out)
    gr.Markdown(
        "_Note : le modele HuggingFace opus-mt est deterministe ; "
        "la temperature n'affecte que le LLM Ollama._"
    )


if __name__ == "__main__":
    # share=True est necessaire sur Google Colab pour obtenir un lien public.
    demo.launch(share=True)
