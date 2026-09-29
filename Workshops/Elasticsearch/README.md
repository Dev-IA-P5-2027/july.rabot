# Workshop Elasticsearch — enrichissement d'adresses postales

Adaptation en Elastic 9.5 de la série d'articles de David Pilato, écrite pour la 6.2 :

1. [Part 1](https://www.elastic.co/fr/blog/enriching-your-postal-addresses-with-the-elastic-stack-part-1) — indexer la Base d'Adresses Nationale Ouverte (BANO)
2. [Part 2](https://www.elastic.co/fr/blog/enriching-your-postal-addresses-with-the-elastic-stack-part-2) — retrouver une adresse propre à partir d'une saisie approximative
3. [Part 3](https://www.elastic.co/fr/blog/enriching-your-postal-addresses-with-the-elastic-stack-part-3) — enrichir un fichier entier via Filebeat

## L'idée

Les adresses saisies par des humains sont sales : « 23 r verdiere, rochelle ». Parfois
on n'a même qu'un point GPS. On se sert de BANO — la base publique de toutes les
adresses françaises — comme d'un annuaire de référence : on lui présente une adresse
approximative ou des coordonnées, elle rend l'adresse normalisée avec sa géolocalisation.

## Les briques

| Brique | Rôle |
|---|---|
| Elasticsearch | Stocke les 1,2 M d'adresses et les retrouve en quelques millisecondes |
| Kibana | Interface web pour explorer les données |
| Logstash | Fait le travail : reçoit une donnée, interroge Elasticsearch, renvoie la donnée enrichie |
| Filebeat | Lit un fichier ligne par ligne et l'envoie à Logstash (part 3) |

## Installation

Prérequis : Docker et Docker Compose.

```bash
# 1. Stack Elasticsearch + Kibana (genere elastic-start-local/.env avec un mot de passe aleatoire)
curl -fsSL https://elastic.co/start-local | sh
```

Le script écrase `elastic-start-local/docker-compose.yml`. Celui versionné ici contient
en plus les services **logstash** et **filebeat**, absents de `start-local` : il faut le
remettre après l'installation, puis ajouter `COMPOSE_PROFILES=logstash` au `.env` généré
(voir `.env.example` pour la liste des clés attendues).

```bash
# 2. Demarrer / arreter le stack (les trois services d'un coup)
cd elastic-start-local && ./start.sh
cd elastic-start-local && ./stop.sh
```

- Elasticsearch : http://localhost:9200
- Kibana : http://localhost:5601 (utilisateur `elastic`, mot de passe dans `elastic-start-local/.env`)
- Logstash : port 8080 (guichet part 2), port 5044 (entrée Filebeat part 3)

## Charger les données

```bash
# Template d'index : a poser AVANT tout chargement, il n'est jamais retroactif
cd elastic-start-local && source .env
curl -u "elastic:$ES_LOCAL_PASSWORD" -X PUT "$ES_LOCAL_URL/_index_template/bano" \
  -H 'Content-Type: application/json' --data-binary @../bano/bano-template.json
```

```bash
# Un index bano-XX par departement, tous regroupes sous l'alias bano
./bano/download.sh 17 44 75 && ./bano/import.sh 17 44 75
```

Les CSV ne sont pas versionnés (95 Mo) : `download.sh` les récupère depuis
[bano.openstreetmap.fr](https://bano.openstreetmap.fr). Compter ~15 s d'indexation
par département.

## Utilisation

**Part 2 — une adresse à la fois.** On POSTe un document sur le port 8080, Logstash le
renvoie enrichi sur sa sortie standard.

```bash
curl -XPOST "localhost:8080" -H "Content-Type: application/json" -d '{"name":"Joe Smith","address":{"number":"23","street_name":"r verdiere","city":"rochelle"}}'
```

```bash
docker logs --tail 25 logstash-local-dev
```

Renvoie `23 Rue Verdière, 17000 La Rochelle` avec ses coordonnées. Fonctionne aussi à
partir d'un simple point GPS.

**Part 3 — un fichier entier.** Filebeat lit un CSV de 2 499 personnes géolocalisées
approximativement, le résultat atterrit dans l'index `person-enriched`.

```bash
./bano/generate-dataset.py && ./bano/loadtest.sh 10
```

### Résultats mesurés

| | Article (6.2) | Ici (9.5.4) |
|---|---|---|
| 10 passes de 2 499 lignes | 3 min 04 s | 2 min 03 s |
| Débit | ~140 doc/s | ~204 doc/s |
| Latence pipeline | 20–40 ms/évt | 2,3 ms/évt |

2 499 personnes sur 2 499 repartent avec une rue et un numéro. Une douzaine changent de
commune : le bruit de 50 m appliqué aux coordonnées les fait basculer de l'autre côté
d'une limite communale, comportement attendu d'un rapprochement par distance.

## Arborescence

```
bano/                    le workshop (configs Logstash, templates, scripts)
elastic-start-local/     le stack Docker (compose personnalise, .env.example)
```

Le détail de chaque fichier, les requêtes à explorer dans Kibana et la liste complète des
écarts entre les articles de 2018 et Elastic 9.5 sont dans [bano/README.md](bano/README.md).
