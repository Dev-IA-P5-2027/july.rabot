#!/usr/bin/env bash
# Part 3 : test de charge de l'article (N passes sur le meme CSV).
# Usage : ./loadtest.sh [nb_iterations]
set -euo pipefail
BANO_DIR="$(cd "$(dirname "$0")" && pwd)"
STACK_DIR="$BANO_DIR/../elastic-start-local"
N="${1:-10}"
ATTENDU=$(wc -l < "$BANO_DIR/data/person_dataset.csv")
cd "$STACK_DIR"

compteur() {
  docker exec logstash-local-dev curl -s localhost:9600/_node/stats/pipelines/enrich-csv \
    | python3 -c "import sys,json;d=json.load(sys.stdin)['pipelines']['enrich-csv']['events'];print(d['out'],d['duration_in_millis'])"
}

read -r EV0 MS0 < <(compteur)
debut=$(date +%s.%N)
for i in $(seq 1 "$N"); do
  cible=$((EV0 + i * ATTENDU))
  cid=$(docker compose --profile tools run -d --rm filebeat 2>/dev/null)
  # Filebeat tourne en continu : on l'arrete des que le pipeline a tout absorbe.
  for _ in $(seq 1 120); do
    read -r ev _ < <(compteur)
    [ "$ev" -ge "$cible" ] && break
    sleep 1
  done
  docker rm -f "$cid" >/dev/null
  echo "Launch $i -> $ev / $cible evenements"
done
fin=$(date +%s.%N)
read -r EV1 MS1 < <(compteur)

python3 - "$debut" "$fin" "$EV0" "$EV1" "$MS0" "$MS1" "$N" "$ATTENDU" <<'PY'
import sys
d,f,e0,e1,m0,m1,n,att = (float(sys.argv[1]),float(sys.argv[2]),int(sys.argv[3]),
                         int(sys.argv[4]),int(sys.argv[5]),int(sys.argv[6]),
                         int(sys.argv[7]),int(sys.argv[8]))
mur, ev, ms = f-d, e1-e0, m1-m0
print(f"\n{n} passes de {att} lignes -> {mur:.1f} s au total, {mur/n:.1f} s par passe")
print(f"{ev} evenements enrichis -> {ev/mur:.0f} doc/s (horloge murale, demarrage des conteneurs inclus)")
if ev:
    print(f"Dont {ms/1000:.1f} s dans le pipeline Logstash : {ms/ev:.1f} ms par evenement, {ev/(ms/1000):.0f} doc/s")
PY
