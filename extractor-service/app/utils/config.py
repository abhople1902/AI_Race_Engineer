# app/utils/config.py
import os

class Config:
    OPENF1_BASE_URL = os.getenv("OPENF1_BASE_URL", "https://api.openf1.org/v1")
    MEETING_KEY = int(os.getenv("MEETING_KEY", 1273))
    SESSION_KEY = int(os.getenv("SESSION_KEY", 9869))
    POLL_INTERVAL_SEC = int(os.getenv("POLL_INTERVAL_SEC", 10))
    PROJECT_ID = os.getenv("PROJECT_ID", "default-project")
    PUBSUB_TOPIC = os.getenv("PUBSUB_TOPIC", "race_snapshots")
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
