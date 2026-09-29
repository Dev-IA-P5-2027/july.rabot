#!/usr/bin/env bash
# Indexe les CSV deja telecharges. Usage : ./import.sh 17 33 75
set -euo pipefail
BANO_DIR="$(cd "$(dirname "$0")" && pwd)"
STACK_DIR="$BANO_DIR/../elastic-start-local"
DEPTS=("${@:-17}")
for DEPT in "${DEPTS[@]}"; do
  FILE="$BANO_DIR/data/bano-$DEPT.csv"
  [ -f "$FILE" ] || { echo "Manquant : $FILE (lance $BANO_DIR/download.sh $DEPT)"; exit 1; }
  echo "== Import du departement $DEPT"
  (cd "$STACK_DIR" && REGION="$DEPT" docker compose --profile tools run --rm -T \
    -e REGION="$DEPT" logstash \
    logstash -f /usr/share/logstash/bano/import.conf) < "$FILE"
done
