# app/consumer.py

import json
from datetime import datetime
from typing import Dict, Any, Optional, List

from confluent_kafka import Consumer, Message

from app.settings import RAW_TOPICS, KAFKA_BOOTSTRAP_SERVERS


# =========================
# Timestamp utilities
# =========================

def parse_event_time(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def extract_event_time(event: Dict[str, Any]) -> Optional[datetime]:
    """
    Extract event-time from OpenF1 payload.
    Priority order is intentional.
    """
    for field in ("date", "date_start", "date_end"):
        if field in event and event[field] is not None:
            return parse_event_time(event[field])
    return None


# =========================
# Consumer
# =========================

class RawEventConsumer:
    """
    High-throughput Kafka consumer for raw OpenF1 events.
    Consumes messages in batches and normalizes them
    into the shape expected by IntervalNormalizer.
    """

    def __init__(self, group_id: str):
        self.consumer = Consumer({
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,

            # Throughput / stability tuning
            "max.poll.interval.ms": 300000,
            "session.timeout.ms": 45000,
        })

        self.consumer.subscribe(RAW_TOPICS)

    # =========================
    # Batch polling
    # =========================

    def poll_batch(
        self,
        max_messages: int = 200,
        timeout: float = 3.0,
    ) -> List[Dict[str, Any]]:
        """
        Poll Kafka for a batch of messages and return
        normalized raw events ready for processing.
        """
        messages: List[Message] = self.consumer.consume(
            num_messages=max_messages,
            timeout=timeout,
        )

        events: List[Dict[str, Any]] = []

        if not messages:
            return events

        for msg in messages:
            if msg is None:
                continue

            if msg.error():
                print(f"[consumer] Kafka error: {msg.error()}")
                continue

            try:
                payload = json.loads(msg.value().decode("utf-8"))
            except Exception as e:
                print(f"[consumer] JSON decode error: {e}")
                continue

            event_time = extract_event_time(payload)
            if event_time is None:
                continue

            topic = msg.topic()

            # Map topic → event_type
            if topic.endswith("intervals.raw"):
                event_type = "intervals"
            elif topic.endswith("laps.raw"):
                event_type = "laps"
            elif topic.endswith("pit.raw"):
                event_type = "pit"
            elif topic.endswith("positions.raw"):
                event_type = "positions"
            else:
                continue

            payload["event_type"] = event_type
            payload["event_time"] = event_time

            events.append(payload)

        return events

    # =========================
    # Offset control
    # =========================

    def commit(self):
        self.consumer.commit(asynchronous=False)

    def close(self):
        self.consumer.close()
