"""
translate.py
------------
Deux traducteurs EN -> FR :
  1. Ollama   : un LLM local (ex. llama3.2), avec temperature reglable.
  2. HuggingFace : Helsinki-NLP/opus-mt-en-fr (modele dedie a la traduction).

Note : le modele HuggingFace opus-mt est deterministe ; la "temperature"
ne s'y applique pas de maniere significative (voir le rapport). La consigne
sur les temperatures concerne donc surtout le LLM Ollama.
"""

import re

# --------------------------------------------------------------------------
# 1) Ollama (LLM local)
# --------------------------------------------------------------------------

OLLAMA_MODEL = "llama3.2"   # modifiable : mistral, qwen2.5, gemma2...


def _clean_llm_output(text):
    """Retire le bavardage frequent des LLM ('Here is the translation:', etc.)."""
    text = text.strip()
    text = re.sub(r"^(here is|voici|translation|traduction)\s*:?\s*", "",
                  text, flags=re.IGNORECASE)
    # retire d'eventuels guillemets encadrants
    text = text.strip().strip('"').strip("'").strip()
    return text


def translate_ollama(text, temperature=0.2, model=OLLAMA_MODEL):
    """Traduit EN -> FR avec un LLM Ollama a la temperature donnee."""
    import ollama
    prompt = (
        "Translate the following English text into French. "
        "Return ONLY the French translation, with no explanation, "
        "no quotes, and no preamble.\n\n"
        f"English: {text}\nFrench:"
    )
    resp = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": float(temperature)},
    )
    return _clean_llm_output(resp["message"]["content"])


# --------------------------------------------------------------------------
# 2) HuggingFace (modele de traduction dedie)
# --------------------------------------------------------------------------

_hf_model = None
_hf_tokenizer = None
HF_MODEL_NAME = "Helsinki-NLP/opus-mt-en-fr"


def get_hf_translator():
    """Charge le modele et le tokenizer HuggingFace une seule fois.

    On charge le modele directement (AutoModelForSeq2SeqLM) au lieu de
    pipeline('translation', ...), car certaines versions de transformers
    ne reconnaissent pas la tache 'translation' via pipeline. Cette
    approche fonctionne quelle que soit la version installee.
    """
    global _hf_model, _hf_tokenizer
    if _hf_model is None:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        print("Chargement du modele HuggingFace opus-mt-en-fr...")
        _hf_tokenizer = AutoTokenizer.from_pretrained(HF_MODEL_NAME)
        _hf_model = AutoModelForSeq2SeqLM.from_pretrained(HF_MODEL_NAME)
    return _hf_model, _hf_tokenizer


def translate_hf(text):
    """Traduit EN -> FR avec Helsinki-NLP/opus-mt-en-fr (deterministe)."""
    model, tokenizer = get_hf_translator()
    inputs = tokenizer([text], return_tensors="pt",
                       truncation=True, max_length=512)
    outputs = model.generate(**inputs, max_length=512, num_beams=4)
    return tokenizer.decode(outputs[0], skip_special_tokens=True).strip()


if __name__ == "__main__":
    sample = "Depression is a common mental disorder."
    print("HuggingFace :", translate_hf(sample))
    try:
        print("Ollama      :", translate_ollama(sample, temperature=0.2))
    except Exception as exc:
        print("Ollama indisponible (lance 'ollama serve' + 'ollama pull "
              f"{OLLAMA_MODEL}') :", exc)
