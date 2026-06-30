# SetFit — Classification de texte few-shot (émotions)

Classification de texte **few-shot** avec [SetFit](https://github.com/huggingface/setfit), sur le
dataset `dair-ai/emotion` (6 émotions : tristesse, joie, amour, colère, peur, surprise) — choisi
pour son lien avec le thème de la psychologie.

L'objectif est de mesurer comment la performance évolue selon **le nombre d'échantillons
d'entraînement** et **le nombre d'epochs**, en few-shot.

---

## 1. Protocole expérimental

- **Découpage** : 80 % (entraînement + évaluation) / 20 % (test). Le jeu de test est **fixe**
  et identique pour toutes les configurations.
- **Échantillons d'entraînement par classe** : 8, 10, 20, 50, 100.
- **Epochs** : 1, 5, 10.
- **Total** : 5 × 3 = **15 modèles** entraînés et évalués.
- **Métriques** : accuracy, precision, recall, F1 (moyenne macro).
- **Modèle de base** : `sentence-transformers/all-MiniLM-L6-v2` (rapide). Pour de meilleurs
  scores : `sentence-transformers/paraphrase-mpnet-base-v2`.

> Remarque : « échantillons par classe » correspond au paramètre `num_samples` de
> `sample_dataset` de SetFit, qui prélève N exemples **pour chaque classe**.

---

## 2. Contenu du dépôt

| Fichier | Rôle |
|---|---|
| `SetFit_Colab.ipynb` | Notebook prêt à lancer sur Google Colab (recommandé, GPU) |
| `setfit_experiments.py` | Script de la grille d'expériences |
| `plot_results.py` | Génère la carte de chaleur et la courbe F1 |
| `requirements.txt` | Dépendances |
| `results_setfit.csv` | Résultats (généré après exécution) |

---

## 3. Exécution

### Sur Google Colab (recommandé)
Ouvre `SetFit_Colab.ipynb`, active le **GPU** (Exécution → Modifier le type d'exécution → T4 GPU),
puis exécute les cellules dans l'ordre.

### En local
```bash
pip install -r requirements.txt
python setfit_experiments.py     # entraîne et évalue les 15 modèles
python plot_results.py           # génère les graphiques
```
Sans GPU, l'entraînement est lent (surtout 100 échantillons / 10 epochs) : Colab est conseillé.

---

## 4. Résultats (à compléter après exécution)

> Copie ici le contenu de `results_setfit.csv`.

| Échantillons/classe | Epochs | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|---|
| 8 | 1 | _…_ | _…_ | _…_ | _…_ |
| … | … | … | … | … | … |

Insère aussi les graphiques :

`![Heatmap F1](setfit_heatmap.png)`
`![Courbe F1](setfit_curve.png)`

### Analyse (à rédiger)
- **Effet du nombre d'échantillons** : la performance augmente-t-elle avec plus d'exemples ?
  (En général oui, avec des gains marqués entre 8 et 50, puis un plateau.)
- **Effet des epochs** : avec SetFit, plus d'epochs n'améliore pas toujours (la doc rappelle
  qu'« on progresse avec plus de données, pas plus d'entraînement »). Observe-t-on du
  surapprentissage à 10 epochs sur les petits échantillons ?
- **Meilleur compromis** : quelle configuration offre le meilleur F1 pour un coût raisonnable ?

---

## 5. Ce qu'il faut retenir sur SetFit
SetFit fonctionne en deux temps : un apprentissage **contrastif** qui ajuste les embeddings de
phrases (en rapprochant les exemples de même classe et en éloignant ceux de classes
différentes), puis l'entraînement d'une **tête de classification** légère. Cela permet
d'obtenir de bons résultats avec très peu d'exemples étiquetés, sans prompt ni verbaliseur.
