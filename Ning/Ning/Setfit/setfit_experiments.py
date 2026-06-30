"""
setfit_experiments.py
---------------------
Classification de texte few-shot avec SetFit.

Protocole (conforme a la consigne) :
  - Jeu de donnees : 'dair-ai/emotion' (6 emotions : tristesse, joie, amour,
    colere, peur, surprise) -- en lien avec le theme psychologie.
  - Decoupage : 80 % (entrainement + evaluation) / 20 % (test fixe).
  - On fait varier le nombre d'echantillons d'entrainement PAR CLASSE :
    8, 10, 20, 50, 100.
  - On fait varier le nombre d'epochs : 1, 5, 10.
  - Chaque variante (5 x 3 = 15 modeles) est evaluee sur LE MEME jeu de test.
  - Metriques : accuracy, precision, recall, F1 (moyenne macro).

Sortie : results_setfit.csv (une ligne par configuration).
"""

import csv
import time

from datasets import load_dataset, concatenate_datasets
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from setfit import SetFitModel, Trainer, TrainingArguments, sample_dataset

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
DATASET = "dair-ai/emotion"
# Modele de base : MiniLM = rapide (recommande pour les 15 entrainements).
# Pour de meilleurs scores : "sentence-transformers/paraphrase-mpnet-base-v2"
BASE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

SAMPLES_PER_CLASS = [8, 10, 20, 50, 100]
EPOCHS = [1, 5, 10]

TEST_SIZE = 0.20      # part reservee au test
TEST_CAP = 500        # taille du jeu de test fixe (pour garder l'eval rapide)
BATCH_SIZE = 16
SEED = 42

OUTPUT_CSV = "results_setfit.csv"


# --------------------------------------------------------------------------
# Preparation des donnees
# --------------------------------------------------------------------------
def prepare_data():
    ds = load_dataset(DATASET)
    # On combine tous les splits puis on refait un decoupage 80/20 stratifie.
    full = concatenate_datasets([ds["train"], ds["validation"], ds["test"]])
    split = full.train_test_split(
        test_size=TEST_SIZE, seed=SEED, stratify_by_column="label"
    )
    train_pool = split["train"]
    test_set = split["test"]

    # Jeu de test FIXE (meme pour toutes les configurations).
    test_set = test_set.shuffle(seed=SEED).select(
        range(min(TEST_CAP, len(test_set)))
    )
    print(f"Pool d'entrainement : {len(train_pool)} | Test fixe : {len(test_set)}")
    return train_pool, test_set


# --------------------------------------------------------------------------
# Une experience (n echantillons/classe, e epochs)
# --------------------------------------------------------------------------
def run_one(train_pool, test_texts, test_labels, n_samples, n_epochs):
    # Echantillonnage few-shot : n exemples PAR CLASSE
    train_few = sample_dataset(
        train_pool, label_column="label", num_samples=n_samples
    )

    model = SetFitModel.from_pretrained(BASE_MODEL)
    args = TrainingArguments(batch_size=BATCH_SIZE, num_epochs=n_epochs)
    trainer = Trainer(model=model, args=args, train_dataset=train_few)

    t0 = time.time()
    trainer.train()
    train_time = time.time() - t0

    preds = [int(p) for p in model.predict(test_texts)]
    acc = accuracy_score(test_labels, preds)
    prec, rec, f1, _ = precision_recall_fscore_support(
        test_labels, preds, average="macro", zero_division=0
    )
    return {
        "samples_per_class": n_samples,
        "epochs": n_epochs,
        "train_examples": len(train_few),
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "train_time_s": round(train_time, 1),
    }


# --------------------------------------------------------------------------
# Grille complete
# --------------------------------------------------------------------------
def main():
    train_pool, test_set = prepare_data()
    test_texts = test_set["text"]
    test_labels = list(test_set["label"])

    results = []
    total = len(SAMPLES_PER_CLASS) * len(EPOCHS)
    i = 0
    for n in SAMPLES_PER_CLASS:
        for e in EPOCHS:
            i += 1
            print(f"\n[{i}/{total}] {n} echantillons/classe, {e} epochs...")
            try:
                row = run_one(train_pool, test_texts, test_labels, n, e)
                results.append(row)
                print(f"   acc={row['accuracy']}  P={row['precision']}  "
                      f"R={row['recall']}  F1={row['f1']}  "
                      f"({row['train_time_s']}s)")
            except Exception as exc:
                print(f"   [echec] {exc}")

    if results:
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            w.writeheader()
            w.writerows(results)
        print(f"\nResultats ecrits dans {OUTPUT_CSV}")
        print_table(results)


def print_table(rows):
    print("\n=== RESUME ===\n")
    header = (f"{'Samples/cl':>11}{'Epochs':>8}{'Accuracy':>10}"
              f"{'Precision':>11}{'Recall':>9}{'F1':>8}")
    print(header)
    print("-" * len(header))
    for r in rows:
        print(f"{r['samples_per_class']:>11}{r['epochs']:>8}"
              f"{r['accuracy']:>10}{r['precision']:>11}"
              f"{r['recall']:>9}{r['f1']:>8}")


if __name__ == "__main__":
    main()
