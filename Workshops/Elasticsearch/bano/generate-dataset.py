#!/usr/bin/env python3
"""Genere le jeu de personnes de la part 3.

L'article utilise un person_dataset.csv qui n'est pas publie. On en fabrique un
equivalent en echantillonnant de vraies adresses BANO (44 et 75, comme dans
l'article) et en bruitant les coordonnees d'environ 50 m : le pipeline doit
retrouver l'adresse exacte a partir d'un point approximatif.

Usage : ./generate-dataset.py [nb_lignes] [dept ...]
"""
import csv, random, sys
from datetime import date, timedelta
from pathlib import Path

DATA = Path(__file__).parent / "data"
nb = int(sys.argv[1]) if len(sys.argv) > 1 else 2499
depts = sys.argv[2:] or ["44", "75"]
random.seed(20180521)  # date de publication de l'article -> generation reproductible

PRENOMS = ["Joe", "Nail", "Lison", "Selena", "Marie", "Ahmed", "Chloe", "Youssef",
           "Emma", "Lucas", "Fatou", "Hugo", "Ines", "Noah", "Jade", "Gabriel"]
NOMS = ["Smith", "Louisa", "Nola", "Sidonie", "Curie", "Dupont", "Bensaid", "Moreau",
        "Nguyen", "Lefevre", "Diallo", "Rossi", "Garcia", "Petit", "Roux", "Faure"]

lignes = []
for dept in depts:
    with open(DATA / f"bano-{dept}.csv", encoding="utf-8") as f:
        lignes += [r for r in csv.reader(f) if len(r) == 8 and r[4] and r[3]]

echantillon = random.sample(lignes, nb)
debut = date(1950, 1, 1)
with open(DATA / "person_dataset.csv", "w", encoding="utf-8", newline="") as out:
    w = csv.writer(out)
    for i, (_id, _num, _rue, zipcode, city, _src, lat, lon) in enumerate(echantillon, 1):
        naissance = debut + timedelta(days=random.randint(0, 55 * 365))
        w.writerow([
            i,
            f"{random.choice(PRENOMS)} {random.choice(NOMS)}",
            f"{naissance} 23:00:00.000000",
            random.choice(["male", "female"]),
            random.randint(0, 4),
            city,
            "France",
            "FR",
            # bruit d'environ +/- 50 m sur chaque axe
            round(float(lat) + random.uniform(-0.00045, 0.00045), 12),
            round(float(lon) + random.uniform(-0.00065, 0.00065), 12),
            zipcode,
        ])
print(f"{nb} personnes ecrites dans {DATA / 'person_dataset.csv'}")
