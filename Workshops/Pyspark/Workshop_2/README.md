# Workshop 2 — Chaîne de données en continu : Airflow, Kafka, Spark, Cassandra

Story 2 (PySpark), workshop « avec Docker » : un mini projet de data engineering de bout
en bout, où des données arrivent **en continu** et traversent quatre outils avant d'être
stockées.

Adaptation de l'article de Dogukan Ulu [Data Engineering End-to-End Project — Spark, Kafka,
Airflow, Docker, Cassandra, Python](https://medium.com/@dogukannulu) (code d'origine :
[dogukannulu/kafka_spark_structured_streaming](https://github.com/dogukannulu/kafka_spark_structured_streaming)),
écrit en 2023 et mis à jour ici avec les versions d'octobre 2026.

## L'idée

```
randomuser.me ──► Airflow ──► Kafka ──► Spark Structured Streaming ──► Cassandra
  (une API qui     (lance la    (file de    (lit les messages au fil      (base de données
   invente des      collecte     messages)   de l'eau, les met en          où les utilisateurs
   utilisateurs)    chaque                   colonnes)                     sont rangés)
                    minute)
```

1. **Airflow** lance une tâche toutes les minutes. Pendant 50 secondes, elle demande un
   nouvel utilisateur fictif à l'API randomuser.me toutes les 10 secondes, et l'envoie à Kafka.
2. **Kafka** reçoit ces messages dans le topic `random_users` et les garde à disposition.
3. **Spark Structured Streaming** lit le topic en continu ; toutes les 10 secondes, il
   transforme les nouveaux messages (du texte JSON) en lignes d'un tableau.
4. **Cassandra** reçoit ces lignes dans la table `spark_streaming.random_users`.

## Les briques

| Brique | Rôle | Adresse |
|---|---|---|
| Airflow 3.3 | Planifie et lance la collecte | http://localhost:8080 |
| Kafka 4.3 | File de messages | `localhost:9092` |
| Kafka UI | Voir les topics et les messages | http://localhost:8088 |
| Spark 3.5 | Traitement en continu Kafka → Cassandra | http://localhost:4050 (interface Spark) |
| Cassandra 5.0 | Base de données | `localhost:9042` |

## Contenu

| Fichier | Rôle |
|---|---|
| `compose.yaml` | Décrit les services et l'ordre de démarrage |
| `airflow/Dockerfile`, `airflow/requirements.txt` | Image Airflow avec la librairie Kafka |
| `airflow/dags/random_users_dag.py` | Le DAG : la planification, et le seul endroit qui lit la configuration |
| `airflow/dags/random_users.py` | Collecte d'un utilisateur, mise en forme, envoi à intervalle régulier |
| `airflow/dags/kafka_publisher.py` | Envoi des messages à Kafka |
| `spark/spark_streaming.py` | Le job Spark : lecture Kafka, mise en colonnes, écriture Cassandra |
| `cassandra/schema.cql` | Création du keyspace et de la table |
| `tests/test_random_users.py` | Tests de la collecte, avec de faux objets (sans réseau ni Kafka) |

## Lancer

Prérequis : Docker et Docker Compose. Prévoir environ 4 Go de RAM libres et 3 Go d'espace
disque pour les images.

```bash
docker compose up -d --build
```

Le premier démarrage prend plusieurs minutes : téléchargement des images, démarrage de
Cassandra (environ une minute), puis téléchargement par Spark de ses connecteurs Kafka et
Cassandra. Les services démarrent dans l'ordre grâce aux `depends_on` : Kafka et Cassandra
d'abord, puis la création du topic et de la table, puis Spark et Airflow.

Voir l'état des services :

```bash
docker compose ps -a
```

`kafka-init` et `cassandra-init` doivent être en `Exited (0)` : ils ont fini leur travail.
Les autres doivent être `Up`.

Arrêter :

```bash
docker compose down
```

Arrêter **et effacer les données** de Cassandra et l'état de Spark :

```bash
docker compose down -v
```

## Vérifier que les données circulent

**Airflow** : ouvrir http://localhost:8080. Le DAG `random_users_to_kafka` est actif dès le
démarrage, et une nouvelle exécution apparaît chaque minute. Le bouton à côté de son nom
permet de le mettre en pause.

**Kafka** : ouvrir http://localhost:8088, puis Topics → `random_users` → Messages.

Ou en ligne de commande :

```bash
docker exec kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server kafka:29092 --topic random_users --from-beginning --max-messages 3
```

**Spark** : suivre le job en direct.

```bash
docker logs -f spark-streaming
```

**Cassandra** : compter et afficher les utilisateurs arrivés.

```bash
docker exec cassandra cqlsh -e "SELECT COUNT(*) FROM spark_streaming.random_users;"
```

```bash
docker exec cassandra cqlsh -e "SELECT full_name, city, country, ingested_at FROM spark_streaming.random_users LIMIT 10;"
```

Le nombre augmente d'environ 5 utilisateurs par minute.

## Lancer les tests

```bash
uvx pytest tests
```

## Mises à jour par rapport à l'article de 2023

| Dans l'article | Problème aujourd'hui | Ici |
|---|---|---|
| Airflow 1.10.9 via l'image `puckel/docker-airflow`, à cloner et construire à part | Image abandonnée depuis 2020 ; Airflow 2 est lui-même en fin de vie depuis avril 2026 | Image officielle `apache/airflow:3.3.2`, en mode `standalone`, dans le même `compose.yaml` |
| DAG avec `PythonOperator` et `schedule_interval` | Syntaxe d'Airflow 1 et 2, retirée en Airflow 3 | Décorateurs `@dag` / `@task` de `airflow.sdk`, paramètre `schedule` |
| Kafka avec ZooKeeper (images Confluent 7.3) | Kafka 4 a supprimé ZooKeeper | `apache/kafka:4.3.1` en mode KRaft, sans ZooKeeper |
| 3 brokers Kafka, Kafka Connect, Schema Registry | Lourd pour un ordinateur portable, et inutilisé par le projet | Un seul broker |
| `provectuslabs/kafka-ui:latest` | Projet abandonné, version non figée | `kafbat/kafka-ui:v1.5.0`, sa suite maintenue |
| `bitnami/spark:3` | Bitnami a retiré ses images gratuites en 2025 | Image officielle `apache/spark` |
| JARs Spark téléchargés à la main avec `curl` dans le conteneur, versions incohérentes (Scala 2.12 et 2.13 mélangés, 3.0.0 et 3.3.0) | Le job plante au démarrage | `--packages` avec des versions alignées, téléchargées automatiquement |
| Librairie `kafka-python` 2.0.2 | Ne fonctionne plus avec les Python récents | `confluent-kafka`, maintenue par l'éditeur de Kafka |
| Topic, keyspace et table créés à la main dans des interfaces | Étapes oubliables, rien n'est reproductible | Créés automatiquement au démarrage (`kafka-init`, `cassandra-init`) |
| Réseau Docker `external` à créer soi-même | Le premier `up` échoue sans cette étape manuelle | Réseau créé par Compose |
| Le DAG est planifié une fois par jour (`0 1 * * *`) | Contredit « toutes les 10 secondes » | Une exécution par minute, un message toutes les 10 secondes |
| Un seul utilisateur récupéré, puis renvoyé 12 fois | Les « nouvelles » données sont toujours les mêmes | Un nouvel utilisateur à chaque envoi |
| Code postal converti en entier | Plante dès qu'un pays a des lettres dans ses codes postaux (Royaume-Uni, Canada…) | Code postal gardé en texte |
| `full_name` comme clé primaire | Deux homonymes s'écrasent | Identifiant unique fourni par l'API (`login.uuid`) |
| Pas de `checkpointLocation` | Le connecteur Cassandra l'exige en streaming ; Spark ne sait pas où il en est après un redémarrage | Point de reprise dans un volume Docker |
| Option `delimeter` passée à la source Kafka | N'existe pas, ignorée | Retirée |

### Pourquoi Spark 3.5 et pas Spark 4

Le reste de la Story 2 utilise Spark 4.2. Mais le connecteur Spark ↔ Cassandra de DataStax
n'existe, à ce jour, que pour Spark 3.5 (version 3.5.1). Spark 3.5 est encore maintenu
(3.5.9 en juillet 2026), donc ce job reste en 3.5, avec le connecteur Kafka de la même
version et Scala 2.12 pour les deux. À revoir quand le connecteur passera à Spark 4.

## Versions utilisées

Airflow 3.3.2 (Python 3.12) · Kafka 4.3.1 · Kafka UI 1.5.0 · Spark 3.5.9 (Java 17) ·
connecteur Kafka 3.5.9 · connecteur Cassandra 3.5.1 · Cassandra 5.0.8 · confluent-kafka 2.16.0
