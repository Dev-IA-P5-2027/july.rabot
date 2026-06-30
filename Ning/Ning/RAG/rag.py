"""
rag.py
------
Coeur du systeme RAG (Retrieval-Augmented Generation) :

  1. Lit des fichiers PDF.
  2. Decoupe le texte en passages (chunks).
  3. Encode chaque passage avec un modele d'embedding HuggingFace
     (paraphrase-multilingual-mpnet-base-v2) -> recherche.
  4. Recherche les passages les plus pertinents par similarite cosinus.
  5. Genere une reponse en francais avec un LLM via Ollama (llama3.2),
     en se basant uniquement sur les passages recuperes.

La recherche se fait avec NumPy (aucune base vectorielle externe requise).
"""

import os
import glob

import numpy as np
from pypdf import PdfReader

# Modeles (modifiables) -----------------------------------------------------
# Embedding MULTILINGUE HuggingFace (recherche / retrieval).
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
# Generateur : LLM via Ollama. llama3.2 synthetise bien mieux que mt0.
# (Necessite Ollama installe + 'ollama pull llama3.2'.)
GEN_MODEL = "llama3.2"

# Decoupage ----------------------------------------------------------------
CHUNK_SIZE = 100      # nombre de mots par passage
CHUNK_OVERLAP = 20    # mots de recouvrement entre passages
TOP_K = 4             # nombre de passages recuperes par question


class RAGSystem:
    def __init__(self, embed_model=EMBED_MODEL, gen_model=GEN_MODEL):
        from sentence_transformers import SentenceTransformer

        print(f"Chargement de l'embedding : {embed_model}")
        self.embedder = SentenceTransformer(embed_model)
        self.gen_model = gen_model

        self.chunks = []        # liste de dicts : {"text": ..., "source": ...}
        self.embeddings = None  # np.ndarray (n_chunks x dim)

    # ----- Lecture & decoupage des PDF -----------------------------------

    @staticmethod
    def extract_text(pdf_path):
        """Extrait tout le texte d'un PDF."""
        reader = PdfReader(pdf_path)
        pages = [(page.extract_text() or "") for page in reader.pages]
        return "\n".join(pages)

    @staticmethod
    def chunk_text(text, source, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
        """Decoupe le texte en passages d'environ `size` mots."""
        words = text.split()
        chunks = []
        step = max(1, size - overlap)
        for i in range(0, len(words), step):
            piece = " ".join(words[i:i + size]).strip()
            if len(piece) > 40:  # ignore les fragments trop courts
                chunks.append({"text": piece, "source": source})
        return chunks

    def add_pdf(self, pdf_path):
        """Ajoute un PDF a la base de connaissances."""
        text = self.extract_text(pdf_path)
        new_chunks = self.chunk_text(text, os.path.basename(pdf_path))
        self.chunks.extend(new_chunks)
        return len(new_chunks)

    def add_folder(self, folder):
        """Ajoute tous les PDF d'un dossier."""
        total = 0
        for pdf in sorted(glob.glob(os.path.join(folder, "*.pdf"))):
            total += self.add_pdf(pdf)
        return total

    # ----- Indexation & recherche ----------------------------------------

    def build_index(self):
        """Calcule les embeddings de tous les passages."""
        if not self.chunks:
            self.embeddings = None
            return
        texts = [c["text"] for c in self.chunks]
        self.embeddings = self.embedder.encode(
            texts, normalize_embeddings=True, show_progress_bar=True
        )

    def retrieve(self, query, k=TOP_K):
        """Renvoie les k passages les plus proches de la question."""
        if self.embeddings is None:
            return []
        q = self.embedder.encode([query], normalize_embeddings=True)[0]
        scores = self.embeddings @ q            # cosinus (vecteurs normalises)
        top = np.argsort(-scores)[:k]
        return [(self.chunks[i], float(scores[i])) for i in top]

    # ----- Generation de la reponse (Ollama) -----------------------------

    def answer(self, query, k=TOP_K):
        """Recupere le contexte puis genere une reponse ancree dessus."""
        import ollama

        hits = self.retrieve(query, k)
        if not hits:
            return "Aucun document n'est indexe.", []

        context = "\n\n".join(
            f"[Source : {h[0]['source']}]\n{h[0]['text']}" for h in hits
        )
        prompt = (
            "Tu es un assistant qui répond à des questions à partir de documents "
            "de l'OMS sur la santé mentale. Réponds en français, de façon claire, "
            "structurée et concise, en utilisant UNIQUEMENT les informations du "
            "contexte ci-dessous. Si l'information ne s'y trouve pas, dis simplement "
            "que le document ne le précise pas. Ne répète pas la question et "
            "n'invente rien.\n\n"
            f"Contexte :\n{context}\n\n"
            f"Question : {query}\n\n"
            "Réponse :"
        )
        resp = ollama.chat(
            model=self.gen_model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2},
        )
        reply = resp["message"]["content"].strip()
        return reply, hits


if __name__ == "__main__":
    rag = RAGSystem()
    n = rag.add_folder("documents")
    print(f"{n} passages charges depuis 'documents/'.")
    rag.build_index()
    if rag.embeddings is not None:
        q = "Quels sont les symptômes de la dépression ?"
        ans, hits = rag.answer(q)
        print("\nQuestion :", q)
        print("Reponse  :", ans)
        print("Sources  :", [h[0]["source"] for h in hits])
