# Workshop 1 — Classifier les champignons avec PySpark

Story 2 (PySpark) : prédire si un champignon est **comestible** ou **toxique** à partir de
ses caractéristiques (odeur, couleur du chapeau, lamelles…), avec la librairie de machine
learning de Spark, puis exposer le meilleur modèle dans une API REST.

Méthode reprise de l'article [Pyspark MLlib | Classification using Pyspark ML](https://towardsai.com/p/l/pyspark-mllib-classification-using-pyspark-ml)
(Towards AI, septembre 2022), appliquée au dataset [Mushroom Classification](https://www.kaggle.com/datasets/uciml/mushroom-classification)
et mise à jour pour Spark 4.

## Contenu

| Fichier | Rôle |
|---|---|
| `pyspark.ipynb` | Le notebook : exploration, préparation, entraînement, évaluation, réglage, sauvegarde |
| `app.py` | L'API FastAPI qui charge le modèle et répond à `/predict` |
| `data/mushrooms.csv` | Le dataset (8 124 champignons, 22 caractéristiques) |
| `models/champignons_rf/` | Le meilleur modèle sauvegardé (pipeline complet) |
| `requirements.txt` | Les librairies Python |

## Installation

Prérequis : **Java 17 ou 21** (Spark 4 ne fonctionne plus avec Java 8 ou 11) et Python 3.10 ou plus.

```bash
sudo apt install openjdk-21-jdk-headless
java -version
```

```bash
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
```

Le paquet `pyspark` pèse environ 430 Mo : il embarque tout le moteur Spark, il n'y a rien
d'autre à installer.

## Lancer

**Le notebook**

```bash
source .venv/bin/activate
jupyter lab
```

Puis ouvrir `pyspark.ipynb` et exécuter les cellules dans l'ordre. Le réglage du modèle
(validation croisée) prend une à deux minutes.

**L'API** (l'environnement virtuel doit être activé)

```bash
uvicorn app:app
```

Documentation interactive : http://127.0.0.1:8000/docs

Exemple d'appel, avec le premier champignon du dataset (toxique) :

```bash
curl -s -X POST http://127.0.0.1:8000/predict -H "Content-Type: application/json" -d '{"cap_shape":"x","cap_surface":"s","cap_color":"n","bruises":"t","odor":"p","gill_attachment":"f","gill_spacing":"c","gill_size":"n","gill_color":"k","stalk_shape":"e","stalk_root":"e","stalk_surface_above_ring":"s","stalk_surface_below_ring":"s","stalk_color_above_ring":"w","stalk_color_below_ring":"w","veil_color":"w","ring_number":"o","ring_type":"p","spore_print_color":"k","population":"s","habitat":"u"}'
```

Réponse : `{"prediction": "toxique", "probabilite_toxique": ...}`

## Les données

- 8 124 champignons : 4 208 comestibles (`e`) et 3 916 toxiques (`p`), donc deux classes à peu près équilibrées.
- Toutes les caractéristiques sont des catégories codées par une lettre.
- Découpage : 80 % pour l'entraînement (6 573 lignes), 20 % pour le test (1 551 lignes), graine fixée à 42.

## Résultats

Mesures calculées sur le jeu de test (1 551 champignons jamais vus pendant l'entraînement).

| Modèle | Accuracy | F1 | Rappel sur les toxiques | AUC |
|---|---|---|---|---|
| Régression logistique | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| Arbre de décision (profondeur 5) | 0.9929 | 0.9929 | 0.9948 | 0.9890 |
| Forêt aléatoire (100 arbres) | 0.9865 | 0.9865 | 0.9725 | 0.9998 |
| GBT (50 itérations) | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| **Forêt aléatoire réglée (validation croisée)** | **1.0000** | **1.0000** | **1.0000** | **1.0000** |

Matrice de confusion de l'arbre de décision :

| | Prédit comestible | Prédit toxique |
|---|---|---|
| **Vraiment comestible** | 781 | 7 |
| **Vraiment toxique** | 4 | 759 |

Réglage de la forêt aléatoire : validation croisée en 3 plis sur 6 combinaisons
(nombre d'arbres 20 / 50 / 100, profondeur 5 / 10), optimisée sur le F1. C'est ce modèle
réglé qui est sauvegardé dans `models/champignons_rf/` et utilisé par l'API.

Caractéristiques les plus importantes pour ce modèle : taille des lamelles (`gill_size`),
odeur (`odor`), surface du pied au-dessus de l'anneau, type d'anneau.

## Choix faits

- **Les `?` de `stalk_root` sont gardés comme une catégorie à part entière.** 2 480 champignons
  ont cette valeur manquante, soit près d'un sur trois : les supprimer ferait perdre beaucoup
  de données, et le fait que la racine n'ait pas été observée peut lui-même être une information.
- **`veil_type` est supprimée.** Elle n'a qu'une seule valeur sur tout le dataset, elle ne
  permet donc de distinguer aucun champignon.
- **Le rappel sur les toxiques est le critère qui compte.** Les deux erreurs possibles n'ont pas
  la même gravité : jeter un champignon comestible est sans conséquence, en manger un toxique
  peut être mortel. Le rappel mesure la part des toxiques que le modèle reconnaît bien comme
  toxiques ; il doit être le plus proche possible de 1.
- **Encodage one-hot** des catégories : sans lui, la régression logistique supposerait un
  ordre entre les lettres (odeur « f » plus grande que « a »), ce qui n'a pas de sens.
- **Valeurs inconnues tolérées** (`handleInvalid="keep"`) : si l'API reçoit une lettre jamais
  vue pendant l'entraînement, le modèle répond au lieu de planter.

## Mises à jour par rapport à l'article de 2022

L'article a été écrit pour Spark 3.3 et un autre dataset (évaluation de voitures).

| Dans l'article | Ici |
|---|---|
| Installation non décrite | Java 21, PySpark 4.2.0 installé par pip (sans `findspark`) |
| Une boucle avec un `StringIndexer` par colonne | Un seul `StringIndexer` multi-colonnes (depuis Spark 3) |
| Étapes appliquées une à une, sur toutes les données | Un `Pipeline` entraîné uniquement sur le jeu d'entraînement |
| Conversion `.cast('int')` des colonnes encodées | Supprimée : elle efface l'information « catégorie » |
| Pas d'encodage one-hot | `OneHotEncoder` ajouté |
| Une colonne mal nommée qui fait planter le code | Corrigé par le `Pipeline` |
| Évaluation sans mesure précisée, étiquetée à tort « Area under ROC » | Mesures explicites : accuracy, F1, rappel par classe, AUC |
| Pas de réglage des modèles | `ParamGridBuilder` + `CrossValidator` |
| Pas de sauvegarde | Sauvegarde et rechargement du `PipelineModel` complet |
| Pas d'API | API FastAPI |

## Versions utilisées

Java 21 · Python 3.13 · PySpark 4.2.0 · FastAPI 0.162 · Uvicorn 0.54
