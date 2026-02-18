# app/producer.py

import json
from typing import Dict, Any
from datetime import datetime

from confluent_kafka import Producer

from app.settings import KAFKA_BOOTSTRAP_SERVERS, LEADERBOARD_TOPIC, NORMALIZED_TOPIC


class NormalizedEventProducer:
    """
    Thin Kafka producer for normalized interval events.
    """

    def __init__(self):
        self.producer = Producer({
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        })

    def send_normalized(self, record: Dict[str, Any]) -> None:
        # Convert datetime → ISO string
        payload = dict(record)
        if hasattr(payload.get("event_time"), "isoformat"):
            payload["event_time"] = payload["event_time"].isoformat()

        self.producer.produce(
            topic=NORMALIZED_TOPIC,
            value=json.dumps(payload).encode("utf-8"),
        )

        # Non-blocking flush for low-volume stream
        self.producer.poll(0)

    def send_leaderboard(self, event: dict):
        payload = dict(event)

        event_time = payload.get("event_time")
        if hasattr(event_time, "isoformat"):
            payload["event_time"] = event_time.isoformat()
            event_time = payload["event_time"]

        session_key = str(payload["session_key"])

        ts_ms = None
        if event_time:
            dt = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
            ts_ms = int(dt.timestamp() * 1000)

        self.producer.produce(
            topic=LEADERBOARD_TOPIC,
            key=session_key.encode("utf-8"),
            value=json.dumps(payload).encode("utf-8"),
            timestamp=ts_ms
        )
        self.producer.poll(0)


    def flush(self):
        self.producer.flush()
