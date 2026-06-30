"""
evaluate.py
-----------
Evalue la qualite de traduction EN -> FR avec BLEU et ROUGE, en comparant :
  - le LLM Ollama aux 5 temperatures : 0, 0.2, 0.5, 0.8, 1.0
  - le modele HuggingFace opus-mt (deterministe -> une seule colonne)

Sortie :
  - results_detailed.csv : une ligne par phrase / modele / temperature
  - results_summary.csv  : scores moyens par modele / temperature
  - un tableau imprime dans la console (a copier dans le README)
"""

import csv

import sacrebleu
from rouge_score import rouge_scorer

from translate import translate_ollama, translate_hf, OLLAMA_MODEL

TEMPERATURES = [0.0, 0.2, 0.5, 0.8, 1.0]
DATASET_CSV = "who_mental_health_en_fr.csv"
MAX_SENTENCES = 60   # limite pour garder l'evaluation rapide sur Colab

_rouge = rouge_scorer.RougeScorer(["rouge1", "rougeL"], use_stemmer=True)


def score_pair(hypothesis, reference):
    """Renvoie BLEU, ROUGE-1, ROUGE-L pour une hypothese vs une reference."""
    bleu = sacrebleu.sentence_bleu(hypothesis, [reference]).score
    r = _rouge.score(reference, hypothesis)
    return {
        "BLEU": bleu,
        "ROUGE-1": r["rouge1"].fmeasure * 100,
        "ROUGE-L": r["rougeL"].fmeasure * 100,
    }


def load_dataset(path=DATASET_CSV, limit=MAX_SENTENCES):
    rows = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows[:limit]


def evaluate(run_ollama=True, run_hf=True):
    data = load_dataset()
    print(f"{len(data)} phrases chargees.\n")

    detailed = []   # lignes fines
    # accumulateurs pour la moyenne : cle = (modele, temperature)
    sums = {}
    counts = {}

    def add(model_name, temp, scores):
        key = (model_name, temp)
        if key not in sums:
            sums[key] = {"BLEU": 0.0, "ROUGE-1": 0.0, "ROUGE-L": 0.0}
            counts[key] = 0
        for k in scores:
            sums[key][k] += scores[k]
        counts[key] += 1

    for idx, row in enumerate(data, 1):
        src = row["source_en"]
        ref = row["reference_fr"]
        print(f"[{idx}/{len(data)}] {src[:60]}...")

        # --- HuggingFace (une seule fois, deterministe) ---
        if run_hf:
            try:
                hyp = translate_hf(src)
                sc = score_pair(hyp, ref)
                add("HF opus-mt", "n/a", sc)
                detailed.append({"model": "HF opus-mt", "temperature": "n/a",
                                 "source_en": src, "reference_fr": ref,
                                 "hypothesis": hyp, **sc})
            except Exception as exc:
                print("   HF echec:", exc)

        # --- Ollama (toutes les temperatures) ---
        if run_ollama:
            for temp in TEMPERATURES:
                try:
                    hyp = translate_ollama(src, temperature=temp)
                    sc = score_pair(hyp, ref)
                    add(f"Ollama {OLLAMA_MODEL}", temp, sc)
                    detailed.append({"model": f"Ollama {OLLAMA_MODEL}",
                                     "temperature": temp,
                                     "source_en": src, "reference_fr": ref,
                                     "hypothesis": hyp, **sc})
                except Exception as exc:
                    print(f"   Ollama (T={temp}) echec:", exc)

    # --- ecriture detaillee ---
    if detailed:
        with open("results_detailed.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(detailed[0].keys()))
            w.writeheader()
            w.writerows(detailed)

    # --- resume (moyennes) ---
    summary_rows = []
    for key in sorted(sums.keys(), key=lambda k: (k[0], str(k[1]))):
        n = counts[key]
        summary_rows.append({
            "model": key[0],
            "temperature": key[1],
            "BLEU": round(sums[key]["BLEU"] / n, 2),
            "ROUGE-1": round(sums[key]["ROUGE-1"] / n, 2),
            "ROUGE-L": round(sums[key]["ROUGE-L"] / n, 2),
            "n": n,
        })

    with open("results_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["model", "temperature", "BLEU",
                                          "ROUGE-1", "ROUGE-L", "n"])
        w.writeheader()
        w.writerows(summary_rows)

    print_table(summary_rows)
    return summary_rows


def print_table(rows):
    print("\n=== RESUME (scores moyens) ===\n")
    header = f"{'Modele':<18}{'Temp':>6}{'BLEU':>9}{'ROUGE-1':>10}{'ROUGE-L':>10}"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(f"{r['model']:<18}{str(r['temperature']):>6}"
              f"{r['BLEU']:>9}{r['ROUGE-1']:>10}{r['ROUGE-L']:>10}")
    print("\n(Copie ce tableau dans ton README.md)")


if __name__ == "__main__":
    evaluate()
