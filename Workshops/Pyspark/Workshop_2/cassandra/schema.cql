CREATE KEYSPACE IF NOT EXISTS spark_streaming
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

CREATE TABLE IF NOT EXISTS spark_streaming.random_users (
  id          text PRIMARY KEY,
  full_name   text,
  gender      text,
  address     text,
  city        text,
  country     text,
  postcode    text,
  latitude    double,
  longitude   double,
  email       text,
  ingested_at timestamp
);
