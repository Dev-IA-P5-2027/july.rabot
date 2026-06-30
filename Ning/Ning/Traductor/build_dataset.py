"""
build_dataset.py
----------------
Construit un corpus parallele EN->FR a partir des fiches d'information
("fact sheets") de l'OMS sur les troubles mentaux.

Source     : https://www.who.int/news-room/fact-sheets  (EN)
             https://www.who.int/fr/news-room/fact-sheets (FR)
Licence OMS : CC BY-NC-SA 3.0 IGO (usage academique / non commercial OK,
              avec attribution a l'Organisation mondiale de la Sante).

Methode :
  1. Telecharge la page EN et la page FR de chaque sujet (meme "slug").
  2. Extrait le texte principal (paragraphes).
  3. Decoupe en phrases.
  4. Aligne EN<->FR par similarite semantique (modele LaBSE), ce qui
     est robuste aux differences de structure entre les deux pages.
  5. Sauvegarde un CSV : source_en, reference_fr, similarity, topic.

Le resultat sert de jeu "original + reference humaine" pour evaluer
la traduction automatique (BLEU / ROUGE).
"""

import re
import sys
import time
import csv

import requests
from bs4 import BeautifulSoup

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

# Sujets "troubles mentaux" couverts par les fact sheets de l'OMS.
# La cle est le "slug" present dans l'URL (identique en EN et en FR).
TOPICS = {
    "depression":        "Depression / Depression",
    "mental-disorders":  "Mental disorders / Troubles mentaux",
    "schizophrenia":     "Schizophrenia / Schizophrenie",
    "bipolar-disorder":  "Bipolar disorder / Trouble bipolaire",
    "dementia":          "Dementia / Demence",
    "anxiety-disorders": "Anxiety disorders / Troubles anxieux",
}

EN_URL = "https://www.who.int/news-room/fact-sheets/detail/{slug}"
FR_URL = "https://www.who.int/fr/news-room/fact-sheets/detail/{slug}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppLeWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36 (educational MT project)"
    )
}

OUTPUT_CSV = "who_mental_health_en_fr.csv"
SIM_THRESHOLD = 0.70   # seuil de similarite pour valider une paire alignee
REQUEST_TIMEOUT = 30


# --------------------------------------------------------------------------
# Telechargement + extraction de texte
# --------------------------------------------------------------------------

def fetch_text(url):
    """Telecharge une page et renvoie son texte principal (paragraphes)."""
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"

    soup = BeautifulSoup(resp.text, "html.parser")

    # On retire les blocs non textuels
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()

    # Le contenu utile de l'OMS est dans <article> ou <main>
    container = soup.find("article") or soup.find("main") or soup

    paragraphs = [p.get_text(" ", strip=True) for p in container.find_all("p")]
    # On garde les paragraphes assez longs (evite menus, mentions legales, etc.)
    paragraphs = [p for p in paragraphs if len(p) > 40]
    return " ".join(paragraphs)


def split_sentences(text):
    """Decoupe un texte en phrases (decoupage simple mais robuste)."""
    text = re.sub(r"\s+", " ", text).strip()
    # Coupe apres . ! ? quand suivi d'un espace + majuscule (FR accents inclus)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ý])", text)
    return [s.strip() for s in parts if len(s.strip()) > 25]


# --------------------------------------------------------------------------
# Alignement semantique EN <-> FR (LaBSE)
# --------------------------------------------------------------------------

_model = None


def get_aligner():
    """Charge le modele d'embedding multilingue (une seule fois)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print("Chargement du modele d'alignement LaBSE (premiere fois = un peu long)...")
        _model = SentenceTransformer("sentence-transformers/LaBSE")
    return _model


def align(en_sents, fr_sents, topic, threshold=SIM_THRESHOLD):
    """Pour chaque phrase FR, trouve la meilleure phrase EN correspondante."""
    from sentence_transformers import util

    if not en_sents or not fr_sents:
        return []

    model = get_aligner()
    en_emb = model.encode(en_sents, convert_to_tensor=True, normalize_embeddings=True)
    fr_emb = model.encode(fr_sents, convert_to_tensor=True, normalize_embeddings=True)
    sims = util.cos_sim(fr_emb, en_emb)  # matrice [FR x EN]

    pairs = []
    used_en = set()
    for i in range(len(fr_sents)):
        j = int(sims[i].argmax())
        score = float(sims[i][j])
        if score >= threshold and j not in used_en:
            used_en.add(j)
            pairs.append({
                "source_en": en_sents[j],
                "reference_fr": fr_sents[i],
                "similarity": round(score, 3),
                "topic": topic,
            })
    return pairs


# --------------------------------------------------------------------------
# Jeu de secours (si le reseau echoue) - clairement etiquete
# --------------------------------------------------------------------------

FALLBACK_PAIRS = [
    ("Depression is a common mental disorder.",
     "La depression est un trouble mental courant."),
    ("Mental health is a state of well-being.",
     "La sante mentale est un etat de bien-etre."),
    ("Anxiety disorders are characterized by excessive fear and worry.",
     "Les troubles anxieux se caracterisent par une peur et une inquietude excessives."),
    ("Schizophrenia affects how a person thinks, feels and behaves.",
     "La schizophrenie affecte la facon dont une personne pense, ressent et se comporte."),
    ("Bipolar disorder causes shifts in mood and energy levels.",
     "Le trouble bipolaire provoque des variations de l'humeur et du niveau d'energie."),
    ("Dementia affects memory, thinking and the ability to perform daily activities.",
     "La demence affecte la memoire, la pensee et la capacite a accomplir les activites quotidiennes."),
    ("Effective treatments for mental disorders exist.",
     "Il existe des traitements efficaces contre les troubles mentaux."),
    ("Stigma and discrimination can prevent people from seeking help.",
     "La stigmatisation et la discrimination peuvent empecher les gens de demander de l'aide."),
    ("Many people with mental disorders do not receive the care they need.",
     "De nombreuses personnes atteintes de troubles mentaux ne recoivent pas les soins dont elles ont besoin."),
    ("Mental health conditions can affect anyone, regardless of age or background.",
     "Les troubles de la sante mentale peuvent toucher n'importe qui, quel que soit son age ou son origine."),
]


def use_fallback():
    print("\n[!] Telechargement OMS indisponible : utilisation du jeu de SECOURS.")
    print("    (Verifie ta connexion / reessaie : ces paires ne sont PAS")
    print("     les traductions officielles de l'OMS.)\n")
    return [
        {"source_en": en, "reference_fr": fr, "similarity": 1.0, "topic": "fallback"}
        for en, fr in FALLBACK_PAIRS
    ]


# --------------------------------------------------------------------------
# Programme principal
# --------------------------------------------------------------------------

def build():
    all_pairs = []
    for slug, topic in TOPICS.items():
        try:
            print(f"-> {topic}")
            en_text = fetch_text(EN_URL.format(slug=slug))
            fr_text = fetch_text(FR_URL.format(slug=slug))
            en_sents = split_sentences(en_text)
            fr_sents = split_sentences(fr_text)
            print(f"   EN: {len(en_sents)} phrases | FR: {len(fr_sents)} phrases")
            pairs = align(en_sents, fr_sents, topic)
            print(f"   -> {len(pairs)} paires alignees (sim >= {SIM_THRESHOLD})")
            all_pairs.extend(pairs)
            time.sleep(1)  # politesse envers le serveur
        except Exception as exc:
            print(f"   [echec] {slug}: {exc}")

    if len(all_pairs) < 10:
        all_pairs = use_fallback()

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["source_en", "reference_fr", "similarity", "topic"]
        )
        writer.writeheader()
        writer.writerows(all_pairs)

    print(f"\nTermine : {len(all_pairs)} paires ecrites dans {OUTPUT_CSV}")
    return all_pairs


if __name__ == "__main__":
    build()
