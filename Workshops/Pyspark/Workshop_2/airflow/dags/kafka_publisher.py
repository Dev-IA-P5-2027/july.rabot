"""Éditeur de messages vers un topic Kafka."""

from confluent_kafka import Producer


class KafkaPublisher:
    def __init__(self, producer: Producer, topic: str):
        self._producer = producer
        self._topic = topic

    def publish(self, key: str, value: bytes) -> None:
        self._producer.produce(self._topic, key=key, value=value)
        self._producer.poll(0)

    def flush(self) -> None:
        self._producer.flush(10)
