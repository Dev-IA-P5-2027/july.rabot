"""DAG Airflow : chaque minute, envoie un utilisateur toutes les 10 secondes vers Kafka.

C'est le seul endroit qui lit l'environnement et choisit les implémentations.
"""

import os
from datetime import datetime, timedelta

from airflow.sdk import dag, task


@dag(
    dag_id="random_users_to_kafka",
    schedule=timedelta(minutes=1),
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 1, "retry_delay": timedelta(seconds=5)},
    tags=["workshop", "kafka"],
)
def random_users_to_kafka():
    @task
    def stream_users() -> int:
        import requests
        from confluent_kafka import Producer

        from kafka_publisher import KafkaPublisher
        from random_users import RandomUserApi, UserStreamer

        def http_get(url: str, timeout: float) -> dict:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()

        producer = Producer({"bootstrap.servers": os.environ["KAFKA_BOOTSTRAP_SERVERS"]})
        streamer = UserStreamer(
            api=RandomUserApi(http_get),
            publisher=KafkaPublisher(producer, os.environ["KAFKA_TOPIC"]),
        )
        return streamer.run(duration_s=50, interval_s=10)

    stream_users()


random_users_to_kafka()
