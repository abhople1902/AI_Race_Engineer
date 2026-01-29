import json
from confluent_kafka import Producer
from utils.config import Config

class KafkaProducerWrapper:
    def __init__(self):
        self.producer = Producer({
            "bootstrap.servers": Config.KAFKA_BOOTSTRAP_SERVERS,
            "acks": "all",
            "retries": 3,
            "linger.ms": 5
        })

    def _delivery_report(self, err, msg):
        if err is not None:
            print(f"🔴 Message delivery failed: {err}")
        else:
            print(f"✅ Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

    def send(self, topic: str, key: str, value: dict):
        payload = json.dumps(value).encode("utf-8")
        self.producer.produce(
            topic=topic,
            key=str(key),
            value=payload,
            on_delivery=self._delivery_report
        )
        self.producer.poll(0)

    def flush(self):
        self.producer.flush()