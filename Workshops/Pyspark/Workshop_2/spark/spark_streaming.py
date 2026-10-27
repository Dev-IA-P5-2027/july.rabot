"""Lit en continu le topic Kafka des utilisateurs et les écrit dans Cassandra (Spark Structured Streaming)."""

import os
from dataclasses import dataclass

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.streaming import StreamingQuery
from pyspark.sql.types import DoubleType, StringType, StructField, StructType

USER_SCHEMA = StructType([
    StructField("id", StringType()),
    StructField("full_name", StringType()),
    StructField("gender", StringType()),
    StructField("address", StringType()),
    StructField("city", StringType()),
    StructField("country", StringType()),
    StructField("postcode", StringType()),
    StructField("latitude", DoubleType()),
    StructField("longitude", DoubleType()),
    StructField("email", StringType()),
])


@dataclass(frozen=True)
class StreamingConfig:
    kafka_bootstrap_servers: str
    kafka_topic: str
    cassandra_host: str
    cassandra_keyspace: str
    cassandra_table: str
    checkpoint_dir: str

    @classmethod
    def from_env(cls) -> "StreamingConfig":
        return cls(
            kafka_bootstrap_servers=os.environ["KAFKA_BOOTSTRAP_SERVERS"],
            kafka_topic=os.environ["KAFKA_TOPIC"],
            cassandra_host=os.environ["CASSANDRA_HOST"],
            cassandra_keyspace=os.environ["CASSANDRA_KEYSPACE"],
            cassandra_table=os.environ["CASSANDRA_TABLE"],
            checkpoint_dir=os.environ["CHECKPOINT_DIR"],
        )


def read_kafka(spark: SparkSession, config: StreamingConfig) -> DataFrame:
    return (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", config.kafka_bootstrap_servers)
        .option("subscribe", config.kafka_topic)
        .option("startingOffsets", "earliest")
        .load()
    )


def parse_users(kafka_df: DataFrame) -> DataFrame:
    """Transforme les messages Kafka (octets JSON) en colonnes de la table Cassandra."""
    return (
        kafka_df.select(
            from_json(col("value").cast("string"), USER_SCHEMA).alias("user"),
            col("timestamp").alias("ingested_at"),
        )
        .select("user.*", "ingested_at")
        .where(col("id").isNotNull())
    )


def write_cassandra(users: DataFrame, config: StreamingConfig) -> StreamingQuery:
    return (
        users.writeStream.format("org.apache.spark.sql.cassandra")
        .options(keyspace=config.cassandra_keyspace, table=config.cassandra_table)
        .option("checkpointLocation", config.checkpoint_dir)
        .outputMode("append")
        .trigger(processingTime="10 seconds")
        .start()
    )


def main() -> None:
    config = StreamingConfig.from_env()
    spark = (
        SparkSession.builder.appName("random-users-streaming")
        .config("spark.cassandra.connection.host", config.cassandra_host)
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    query = write_cassandra(parse_users(read_kafka(spark, config)), config)
    query.awaitTermination()


if __name__ == "__main__":
    main()
