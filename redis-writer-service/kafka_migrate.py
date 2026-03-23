from confluent_kafka import Consumer, Producer, TopicPartition
from datetime import datetime
import json
import os

LOCAL_BOOTSTRAP = os.getenv("LOCAL_KAFKA_BOOTSTRAP", "localhost:29092")
CLOUD_BOOTSTRAP = os.getenv("CLOUD_KAFKA_BOOTSTRAP")
CLOUD_API_KEY = os.getenv("KAFKA_API_KEY")
CLOUD_API_SECRET = os.getenv("KAFKA_API_SECRET")

TOPIC = os.getenv("KAFKA_TOPIC", "f1.race_control.raw")

missing_env = [
    name
    for name, value in {
        "CLOUD_KAFKA_BOOTSTRAP": CLOUD_BOOTSTRAP,
        "KAFKA_API_KEY": CLOUD_API_KEY,
        "KAFKA_API_SECRET": CLOUD_API_SECRET,
    }.items()
    if not value
]

if missing_env:
    missing = ", ".join(missing_env)
    raise RuntimeError(f"Missing required environment variables: {missing}")

consumer = Consumer({
    "bootstrap.servers": LOCAL_BOOTSTRAP,
    "group.id": "migration-group",
    "enable.auto.commit": False,
})

producer = Producer({
    "bootstrap.servers": CLOUD_BOOTSTRAP,
    "security.protocol": "SASL_SSL",
    "sasl.mechanism": "PLAIN",
    "sasl.username": CLOUD_API_KEY,
    "sasl.password": CLOUD_API_SECRET,
})

def extract_event_time(event):
    if "event_time" in event:
        dt = datetime.fromisoformat(event["event_time"].replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)

    if "date" in event:
        dt = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)

    return None


metadata = consumer.list_topics(TOPIC, timeout=10)
partitions = metadata.topics[TOPIC].partitions.keys()

total_messages = 0

for p in partitions:
    print(f"Migrating partition {p}")

    tp = TopicPartition(TOPIC, p, 0)
    consumer.assign([tp])

    low, high = consumer.get_watermark_offsets(tp)
    print(f"Partition {p} offsets: {low} → {high}")

    # Fix 1: Skip empty partitions entirely
    if high == 0 or low == high:
        print(f"Partition {p} is empty, skipping.")
        continue

    while True:
        msg = consumer.poll(1.0)

        # Fix 2: Treat None as "no more messages" after checking watermarks
        if msg is None:
            current_offset = consumer.position([tp])[0].offset
            if current_offset >= high:
                print(f"Finished partition {p} (drained)")
                break
            continue

        if msg.error():
            continue

        event = json.loads(msg.value().decode("utf-8"))
        ts_ms = extract_event_time(event)

        producer.produce(
            TOPIC,
            key=msg.key(),
            value=msg.value(),
            partition=p,
            timestamp=ts_ms,
        )

        total_messages += 1

        if msg.offset() + 1 >= high:
            print(f"Finished partition {p}")
            break

producer.flush()
consumer.close()

print(f"Migration complete. Total messages migrated: {total_messages}")
