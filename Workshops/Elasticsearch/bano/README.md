# Workshop 2 — Enrichissement d'adresses postales avec BANO

Adaptation Elastic 9.5 des articles Elastic (écrits pour la 6.2) :
- [Part 1](https://www.elastic.co/fr/blog/enriching-your-postal-addresses-with-the-elastic-stack-part-1) — indexer la Base d'Adresses Nationale Ouverte
- [Part 2](https://www.elastic.co/fr/blog/enriching-your-postal-addresses-with-the-elastic-stack-part-2) — enrichir des documents via Logstash
- [Part 3](https://www.elastic.co/fr/blog/enriching-your-postal-addresses-with-the-elastic-stack-part-3) — enrichir un jeu de données existant via Filebeat

## Fichiers

| Fichier | Rôle |
|---|---|
| `bano-template.json` | Index template : mapping, analyzers (asciifolding + synonymes `r`→`rue`), alias `bano` |
| `import.conf` | Part 1 — pipeline Logstash CSV → Elasticsearch |
| `enrich.conf` | Part 2 — pipeline Logstash HTTP → recherche → document enrichi |
| `enrich-csv.conf` | Part 3 — pipeline Logstash Beats → CSV → recherche géo → `person-enriched` |
| `pipelines.yml` | Fait tourner les deux pipelines d'enrichissement en parallèle |
| `filebeat.yml` | Part 3 — Filebeat lit `data/person_dataset.csv` et l'envoie sur le port 5044 |
| `person-template.json` | Index template de `person-enriched` (`location` en `geo_point`) |
| `generate-dataset.py` | Fabrique le jeu de personnes (l'article ne le publie pas) |
| `loadtest.sh` | Test de charge de la part 3 |
| `search-by-name.json` | Template de requête : lookup par adresse texte |
| `search-by-geo.json` | Template de requête : lookup par coordonnées |
| `download.sh` | Télécharge les CSV BANO |
| `import.sh` | Indexe les CSV téléchargés |
| `data/` | CSV bruts (non versionnés) |

Le service `logstash` lui-même est défini dans `../elastic-start-local/docker-compose.yml`
(profils `logstash` pour l'enrichissement, `tools` pour l'import one-shot).

## Mise en place

Le template d'index est déjà créé et le département **17** (Charente-Maritime,
446 416 adresses) est déjà indexé. Pour repartir de zéro ou ajouter des
départements :

```bash
# 1. Créer / mettre à jour le template (une seule fois)
cd ../elastic-start-local
source .env
curl -u "elastic:$ES_LOCAL_PASSWORD" -X PUT "$ES_LOCAL_URL/_index_template/bano" \
  -H 'Content-Type: application/json' --data-binary @../bano/bano-template.json

# 2. Télécharger un ou plusieurs départements
./bano/download.sh 17 33 75

# 3. Les indexer (un index bano-XX par département, tous sous l'alias bano)
./bano/import.sh 17 33 75
```

Compter environ 20 s d'indexation et 18 Mo par département de la taille du 17.

## Utilisation

Le service `logstash` démarre avec `../elastic-start-local/start.sh` (profil activé
par `COMPOSE_PROFILES=logstash` dans le `.env`) et écoute sur le port 8080.
On lui POSTe un document, il le renvoie enrichi sur sa sortie standard.

```bash
# Enrichissement à partir d'une adresse texte approximative
curl -XPOST "localhost:8080" -H "Content-Type: application/json" -d '{
  "test_case": "Address with text",
  "name": "Joe Smith",
  "address": {"number": "23", "street_name": "r verdiere", "city": "rochelle"}
}'

# Enrichissement à partir de coordonnées
curl -XPOST "localhost:8080" -H "Content-Type: application/json" -d '{
  "test_case": "Address with geo point",
  "name": "Jane Doe",
  "location": {"lat": 46.15735, "lon": -1.1551}
}'

# Voir le résultat
docker logs -f logstash-local-dev
```

Les deux renvoient `23 Rue Verdière, 17000 La Rochelle` avec ses coordonnées.

Quand le code postal est présent, le pipeline en déduit le département
(2 chiffres, 3 pour l'outre-mer en 97x) et interroge directement `bano-17`
au lieu de l'alias `bano` — moins de données à parcourir.

## Part 3 — enrichir un jeu de données existant

L'article part d'un `person_dataset.csv` de ~2500 personnes géolocalisées
approximativement, que Filebeat pousse vers Logstash. Ce fichier n'est pas publié :
`generate-dataset.py` en fabrique un équivalent en échantillonnant de vraies
adresses BANO (44 et 75, comme dans l'article) et en bruitant les coordonnées
d'environ 50 m. Le pipeline doit donc retrouver l'adresse postale exacte à partir
d'un point approximatif.

```bash
# départements utilisés par le dataset
./bano/download.sh 44 75 && ./bano/import.sh 44 75

# template de l'index de sortie
cd elastic-start-local && source .env
curl -u "elastic:$ES_LOCAL_PASSWORD" -X PUT "$ES_LOCAL_URL/_index_template/person" \
  -H 'Content-Type: application/json' --data-binary @../bano/person-template.json
cd ..

# jeu de personnes puis test de charge (10 passes, comme l'article)
./bano/generate-dataset.py
./bano/loadtest.sh 10
```

`enrich-csv.conf` utilise volontairement la stratégie la plus lente de la part 2 —
tri par `geo_distance` sur l'alias `bano` complet (1,2 M d'adresses) — puisque
c'est celle que l'article mesure. Chaque document conserve son adresse d'entrée
sous `input_address` pour pouvoir comparer avant/après.

### Résultats mesurés

| | Article (6.2) | Ici (9.5.4) |
|---|---|---|
| 10 passes | 3 min 04 s | 2 min 03 s |
| Par passe | ~18 s | ~12 s |
| Débit horloge murale | ~140 doc/s | ~204 doc/s |
| Latence dans le pipeline | 20–40 ms/évt | 2,3 ms/évt |

Sur les 2 499 personnes, 2 499 repartent avec une rue et un numéro. 18 changent de
code postal par rapport à l'entrée : le bruit de 50 m les fait basculer sur la
commune voisine, ce qui est le comportement attendu d'un rapprochement par
distance.

## Requêtes à explorer dans Kibana → Dev Tools

```
GET _cat/indices/bano*?v&h=index,docs.count,store.size

GET bano/_search
{
  "size": 1,
  "query": {"bool": {"should": [
    {"match": {"address.number": "23"}},
    {"match": {"address.street_name": "r verdiere"}},
    {"match": {"address.city": "rochelle"}}
  ]}}
}

GET bano/_search
{
  "size": 1,
  "query": {"bool": {"filter": {"geo_distance": {
    "distance": "1km",
    "location": {"lat": 46.15735, "lon": -1.1551}
  }}}},
  "sort": [{"_geo_distance": {"location": {"lat": 46.15735, "lon": -1.1551}}}]
}
```

## Écarts avec les articles d'origine (Elastic 6.2 → 9.5)

| Article | Ici | Pourquoi |
|---|---|---|
| `_template` + `"template": ".bano-*"` | `_index_template` + `"index_patterns"` | Templates legacy dépréciés |
| `"mappings": {"doc": {...}}` | `"mappings": {"properties": ...}` | Mapping types supprimés en 8.0 |
| Index `.bano-17` | Index `bano-17` | Le préfixe `.` est réservé aux index système |
| Logstash local | Conteneur `logstash:9.5.3` | Même version que le reste du stack |
| Pas d'authentification | `user`/`password` depuis `.env` | Sécurité activée par défaut en 9.x |
| `convert` + `rename` dans un seul `mutate` | Deux `mutate` | Dans un `mutate`, `rename` s'exécute avant `convert` : lat/lon seraient restées des chaînes |
| Champs Logstash implicites | `ecs_compatibility => disabled` | Logstash 8+ range tout sous ECS, ce qui casserait la structure `address.*` |
| Filebeat input `log` + `close_eof` | input `filestream` + `close.reader.on_eof` | L'input `log` est supprimé en 9.x (« Log input is deprecated ») |
| `filebeat --once` | Filebeat en continu, arrêté par `loadtest.sh` | Avec `filestream`, `--once` déclare la collecte terminée avant que le harvester ait publié : une passe sur deux n'envoie rien |
| `rm data/registry` entre deux passes | registre en `tmpfs` dans le conteneur | Même effet, sans fichier à supprimer |
| Monitoring X-Pack pour mesurer | API `_node/stats/pipelines` de Logstash | Le monitoring interne est déprécié ; l'API donne directement le temps passé par événement |
| — | `remove_field => [..., "event"]` | Logstash 9 recopie la ligne/requête brute dans `[event][original]` même avec `ecs_compatibility => disabled` : 4× la taille de l'index et du bruit dans la sortie d'`enrich.conf` |
