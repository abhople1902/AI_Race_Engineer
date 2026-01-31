# app/consumer_normalized.py

import json
from datetime import datetime
from typing import Dict, Any, List

from confluent_kafka import Consumer, Message
from app.settings import KAFKA_BOOTSTRAP_SERVERS, NORMALIZED_TOPIC


def parse_event_time(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


class NormalizedEventConsumer:
    """
    Consumer for f1.intervals.normalized.
    """

    def __init__(self, group_id: str):
        self.consumer = Consumer({
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "max.poll.interval.ms": 300000,
            "session.timeout.ms": 45000,
        })

        self.consumer.subscribe([NORMALIZED_TOPIC])

    def poll_batch(self, max_messages=200, timeout=3.0) -> List[Dict[str, Any]]:
        messages: List[Message] = self.consumer.consume(
            num_messages=max_messages,
            timeout=timeout,
        )

        events: List[Dict[str, Any]] = []

        if not messages:
            return events

        for msg in messages:
            if msg is None or msg.error():
                continue

            try:
                payload = json.loads(msg.value().decode("utf-8"))
            except Exception:
                continue

            if isinstance(payload.get("event_time"), str):
                payload["event_time"] = parse_event_time(payload["event_time"])

            events.append(payload)

        return events

    def commit(self):
        self.consumer.commit(asynchronous=False)

    def close(self):
        self.consumer.close()
