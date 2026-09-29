#!/usr/bin/env bash
# Telecharge les CSV BANO. Usage : ./download.sh 17 33 75
# Sans argument : departement 17 (celui du tutoriel Elastic).
set -euo pipefail
cd "$(dirname "$0")"
DEPTS=("${@:-17}")
mkdir -p data
for DEPT in "${DEPTS[@]}"; do
  echo "== Telechargement du departement $DEPT"
  curl -fSL --progress-bar -o "data/bano-$DEPT.csv" \
    "https://bano.openstreetmap.fr/data/bano-$DEPT.csv"
  echo "   $(wc -l < "data/bano-$DEPT.csv") adresses"
done
