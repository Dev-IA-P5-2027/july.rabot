"""
plot_results.py
---------------
Visualise les resultats SetFit a partir de results_setfit.csv :
  - une carte de chaleur du F1 (echantillons/classe x epochs)
  - une courbe du F1 en fonction du nombre d'echantillons

Sorties : setfit_heatmap.png, setfit_curve.png
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

df = pd.read_csv("results_setfit.csv")

# ---- Carte de chaleur du F1 ----------------------------------------------
pivot = df.pivot(index="samples_per_class", columns="epochs", values="f1")

fig, ax = plt.subplots(figsize=(6, 5))
im = ax.imshow(pivot.values, cmap="viridis", aspect="auto")
ax.set_xticks(range(len(pivot.columns)))
ax.set_xticklabels(pivot.columns)
ax.set_yticks(range(len(pivot.index)))
ax.set_yticklabels(pivot.index)
ax.set_xlabel("Nombre d'epochs")
ax.set_ylabel("Echantillons par classe")
ax.set_title("Score F1 (macro) selon la configuration")
for y in range(pivot.shape[0]):
    for x in range(pivot.shape[1]):
        ax.text(x, y, f"{pivot.values[y, x]:.2f}",
                ha="center", va="center", color="white", fontsize=10)
fig.colorbar(im, ax=ax, label="F1")
plt.tight_layout()
plt.savefig("setfit_heatmap.png", dpi=150, bbox_inches="tight")
print("setfit_heatmap.png enregistre")

# ---- Courbe F1 vs nombre d'echantillons ----------------------------------
fig, ax = plt.subplots(figsize=(7, 4.5))
for e in sorted(df["epochs"].unique()):
    sub = df[df["epochs"] == e].sort_values("samples_per_class")
    ax.plot(sub["samples_per_class"], sub["f1"],
            marker="o", label=f"{e} epochs")
ax.set_xlabel("Echantillons par classe")
ax.set_ylabel("F1 (macro)")
ax.set_title("Effet du nombre d'echantillons sur le F1")
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("setfit_curve.png", dpi=150, bbox_inches="tight")
print("setfit_curve.png enregistre")
