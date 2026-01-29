# app/settings.py
import os

KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:29092"
)

RAW_TOPICS = [
    "f1.intervals.raw",
    "f1.laps.raw",
    "f1.pit.raw",
    "f1.positions.raw",
]

NORMALIZED_TOPIC = "f1.intervals.normalized"
