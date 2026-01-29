# app/producer.py

import json
from typing import Dict, Any

from confluent_kafka import Producer

from app.settings import KAFKA_BOOTSTRAP_SERVERS, NORMALIZED_TOPIC


class NormalizedEventProducer:
    """
    Thin Kafka producer for normalized interval events.
    """

    def __init__(self):
        self.producer = Producer({
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        })

    def send(self, record: Dict[str, Any]) -> None:
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

    def flush(self):
        self.producer.flush()
