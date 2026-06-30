"""
prepare_documents.py
--------------------
Prepare les documents PDF de la base de connaissances RAG a partir des
fiches d'information de l'OMS sur les troubles mentaux.

  - Telecharge chaque fiche (en anglais) sur who.int.
  - L'enregistre en PDF dans le dossier 'documents/'.
  - Si le telechargement echoue, cree un PDF de secours a partir d'un
    resume factuel (clairement etiquete).

Source     : https://www.who.int/news-room/fact-sheets
Licence OMS : CC BY-NC-SA 3.0 IGO (usage academique / non commercial,
              attribution a l'Organisation mondiale de la Sante).

Usage : python prepare_documents.py
"""

import os
import re
import time

import requests
from bs4 import BeautifulSoup
from fpdf import FPDF

TOPICS = {
    "depression":        "OMS - Dépression",
    "mental-disorders":  "OMS - Troubles mentaux",
    "schizophrenia":     "OMS - Schizophrénie",
    "bipolar-disorder":  "OMS - Trouble bipolaire",
    "dementia":          "OMS - Démence",
    "anxiety-disorders": "OMS - Troubles anxieux",
    "mental-health-strengthening-our-response": "OMS - Santé mentale",
    "autism-spectrum-disorders":                "OMS - Autisme",
    "adolescent-mental-health":                 "OMS - Santé mentale des adolescents",
}

# On telecharge les fiches en FRANCAIS (/fr/) pour des reponses en francais.
FR_URL = "https://www.who.int/fr/news-room/fact-sheets/detail/{slug}"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 (educational RAG)"
    )
}
OUT_DIR = "documents"


def fetch_text(url):
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()
    container = soup.find("article") or soup.find("main") or soup
    paras = [p.get_text(" ", strip=True) for p in container.find_all("p")]
    paras = [p for p in paras if len(p) > 40]
    return "\n".join(paras)


def save_pdf(title, body, path):
    """Cree un PDF simple a partir d'un titre et d'un corps de texte."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_title(title)

    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, _latin1(title))
    pdf.ln(3)

    pdf.set_font("Helvetica", size=11)
    for para in body.split("\n"):
        para = para.strip()
        if not para:
            continue
        pdf.multi_cell(0, 6, _latin1(para))
        pdf.ln(2)

    pdf.output(path)


def _latin1(text):
    """fpdf (police de base) ne gere que latin-1 : on remplace le reste."""
    return text.encode("latin-1", "replace").decode("latin-1")


# --- Texte de secours (resume factuel, redige pour le projet) -------------

FALLBACK = {
    "OMS - Dépression (résumé de secours)": (
        "La dépression est un trouble mental courant. Elle se caractérise par "
        "une humeur dépressive ou une perte de plaisir ou d'intérêt pour des "
        "activités, pendant de longues périodes. Les symptômes peuvent inclure "
        "des difficultés de concentration, un sentiment de culpabilité excessive "
        "ou de faible estime de soi, un sentiment de désespoir, des troubles du "
        "sommeil, des changements d'appétit et une fatigue importante. La "
        "dépression peut toucher tout le monde et se distingue des variations "
        "d'humeur habituelles. Des traitements psychologiques efficaces existent, "
        "et selon la gravité, un traitement médicamenteux peut aussi aider. La "
        "dépression est plus fréquente chez les femmes que chez les hommes."
    ),
    "OMS - Troubles anxieux (résumé de secours)": (
        "Les troubles anxieux se caractérisent par une peur et une inquiétude "
        "excessives ainsi que par des troubles du comportement associés. Les "
        "symptômes sont suffisamment graves pour entraîner une détresse "
        "importante ou une altération du fonctionnement. Il en existe plusieurs "
        "types, comme le trouble anxieux généralisé, le trouble panique et "
        "l'anxiété sociale. Les troubles anxieux comptent parmi les troubles "
        "mentaux les plus fréquents. Des traitements psychologiques efficaces "
        "existent, et un traitement médicamenteux peut être envisagé selon l'âge "
        "et la gravité."
    ),
    "OMS - Schizophrénie (résumé de secours)": (
        "La schizophrénie est un trouble mental qui affecte la façon dont une "
        "personne pense, ressent et se comporte. Les personnes atteintes peuvent "
        "présenter des délires persistants, des hallucinations, une pensée "
        "désorganisée et des changements de comportement. La schizophrénie "
        "débute généralement à la fin de l'adolescence ou au début de l'âge "
        "adulte. Avec un traitement, comprenant des médicaments et un soutien "
        "psychosocial, de nombreuses personnes peuvent se rétablir. Les personnes "
        "atteintes de schizophrénie font souvent face à la stigmatisation et à la "
        "discrimination."
    ),
    "OMS - Trouble bipolaire (résumé de secours)": (
        "Le trouble bipolaire est un trouble mental marqué par l'alternance de "
        "périodes de dépression et de périodes de symptômes maniaques. Pendant un "
        "épisode dépressif, la personne se sent triste, vide ou irritable. "
        "Pendant un épisode maniaque, elle peut se sentir euphorique, avoir une "
        "énergie accrue et un besoin de sommeil réduit. Un traitement efficace "
        "associe des médicaments et un soutien psychosocial."
    ),
    "OMS - Démence (résumé de secours)": (
        "La démence est un syndrome caractérisé par une détérioration des "
        "fonctions cognitives plus importante que celle attendue du vieillissement "
        "normal. Elle affecte la mémoire, la pensée, l'orientation, la "
        "compréhension et la capacité à accomplir les activités quotidiennes. La "
        "démence est l'une des principales causes de dépendance chez les personnes "
        "âgées. Bien qu'il n'existe pas de traitement curatif pour la plupart des "
        "formes, le soutien et les soins peuvent améliorer la vie des personnes "
        "concernées."
    ),
}


def build_fallback():
    print("\n[!] Telechargement OMS indisponible : creation de PDF de SECOURS.")
    print("    (Ces resumes sont factuels mais ne sont PAS les fiches")
    print("     officielles integrales de l'OMS.)\n")
    for title, body in FALLBACK.items():
        fname = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_") + ".pdf"
        save_pdf(title, body, os.path.join(OUT_DIR, fname))
        print("   cree :", fname)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    success = 0
    for slug, title in TOPICS.items():
        try:
            print(f"-> {title}")
            text = fetch_text(FR_URL.format(slug=slug))
            if len(text) < 200:
                raise ValueError("contenu trop court")
            fname = slug.replace("-", "_") + ".pdf"
            save_pdf(title, text, os.path.join(OUT_DIR, fname))
            print("   cree :", fname)
            success += 1
            time.sleep(1)
        except Exception as exc:
            print(f"   [echec] {slug}: {exc}")

    if success == 0:
        build_fallback()

    pdfs = [f for f in os.listdir(OUT_DIR) if f.endswith(".pdf")]
    print(f"\nTermine : {len(pdfs)} PDF dans '{OUT_DIR}/'")


if __name__ == "__main__":
    main()
