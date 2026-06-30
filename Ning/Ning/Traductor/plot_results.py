"""
plot_results.py
---------------
Trace l'effet de la temperature sur la qualite de traduction (BLEU, ROUGE-1,
ROUGE-L) pour le modele Ollama, a partir de results_summary.csv.

Le modele HuggingFace (temperature 'n/a') est affiche en lignes de reference
horizontales pour comparaison.

Sortie : temperature_effect.png (a inserer dans le README).

Usage : python plot_results.py
"""

import pandas as pd
import matplotlib.pyplot as plt

CSV = "results_summary.csv"
OUTPUT = "temperature_effect.png"

# Palette rose : du framboise fonce au rose clair
PINK = {
    "BLEU":    "#AD1457",  # framboise
    "ROUGE-1": "#E91E63",  # rose
    "ROUGE-L": "#F48FB1",  # rose clair
}
HF_LINE = "#7A4E5B"  # rose-gris pour les references HuggingFace

METRICS = ["BLEU", "ROUGE-1", "ROUGE-L"]


def main():
    df = pd.read_csv(CSV)

    # Separe Ollama (temperatures numeriques) et HF (temperature 'n/a')
    df["temp_num"] = pd.to_numeric(df["temperature"], errors="coerce")
    ollama = df[df["temp_num"].notna()].sort_values("temp_num")
    hf = df[df["temp_num"].isna()]

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#FFF5F8")  # fond legerement rose

    # Courbes Ollama
    for metric in METRICS:
        ax.plot(
            ollama["temp_num"], ollama[metric],
            marker="o", markersize=8, linewidth=2.5,
            color=PINK[metric], label=f"Ollama — {metric}",
        )

    # Lignes de reference HuggingFace (si presentes)
    if not hf.empty:
        for metric in METRICS:
            val = hf[metric].iloc[0]
            ax.axhline(
                val, linestyle="--", linewidth=1.4, color=HF_LINE, alpha=0.7,
            )
            ax.text(
                ollama["temp_num"].max(), val,
                f" opus-mt {metric}: {val:.1f}",
                va="center", ha="left", fontsize=8, color=HF_LINE,
            )

    ax.set_title("Effet de la température sur la qualité de traduction",
                 fontsize=14, fontweight="bold", color="#880E4F", pad=15)
    ax.set_xlabel("Température (Ollama)", fontsize=11)
    ax.set_ylabel("Score", fontsize=11)
    ax.set_xticks(ollama["temp_num"])
    ax.grid(True, alpha=0.3, color="#E91E63")
    ax.legend(loc="lower left", frameon=True, fontsize=9)

    # Marge a droite pour les etiquettes opus-mt
    ax.set_xlim(ollama["temp_num"].min() - 0.05,
                ollama["temp_num"].max() + 0.35)

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    plt.tight_layout()
    plt.savefig(OUTPUT, dpi=150, bbox_inches="tight")
    print(f"Graphique enregistré : {OUTPUT}")


if __name__ == "__main__":
    main()
