import json
import os
import time
from confluent_kafka import Consumer

# =========================
# CONFIG
# =========================

BOOTSTRAP_SERVERS = "localhost:29092"
SESSION_KEY = 9869

TOPICS = {
    "f1.intervals.raw": "intervals.json",
    "f1.laps.raw": "laps.json",
    "f1.pit.raw": "pit.json",
    "f1.positions.raw": "positions.json",
}

OUTPUT_DIR = "./dumped_inputs"

IDLE_TIMEOUT_SECONDS = 30

# =========================
# SETUP
# =========================

os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_consumer(group_id: str) -> Consumer:
    return Consumer({
        "bootstrap.servers": BOOTSTRAP_SERVERS,
        "group.id": group_id,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
        "session.timeout.ms": 45000,
        "max.poll.interval.ms": 300000,
    })


# =========================
# DUMP LOGIC
# =========================

print(f"Dumping Kafka data for session_key = {SESSION_KEY}")

buffers = {}

for topic, filename in TOPICS.items():
    print(f"\nConsuming topic: {topic}")

    consumer = create_consumer(group_id=f"dump-consumer-{int(time.time())}")  # Unique group ID
    consumer.subscribe([topic])

    buffers[topic] = []
    last_msg_time = time.time()
    message_count = 0
    
    # Give consumer time to join and get assignments
    print("Waiting for partition assignment...")
    time.sleep(5)

    while True:
        msg = consumer.poll(2.0)

        if msg is None:
            elapsed = time.time() - last_msg_time
            print(f"No message (idle for {elapsed:.1f}s, total messages: {message_count})")
            if elapsed > IDLE_TIMEOUT_SECONDS:
                print(f"No new messages for {IDLE_TIMEOUT_SECONDS}s → stopping {topic}")
                break
            continue

        if msg.error():
            print(f"Kafka error on {topic}: {msg.error()}")
            continue

        try:
            event = json.loads(msg.value().decode("utf-8"))
        except Exception as e:
            print(f"JSON decode error: {e}")
            continue

        last_msg_time = time.time()
        message_count += 1

        if event.get("session_key") == SESSION_KEY:
            buffers[topic].append(event)
            if len(buffers[topic]) % 100 == 0:
                print(f"Collected {len(buffers[topic])} matching records...")

    consumer.close()
    print(f"Total messages from topic: {message_count}, Matching session: {len(buffers[topic])}")

# =========================
# WRITE FILES
# =========================

for topic, filename in TOPICS.items():
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w") as f:
        json.dump(buffers[topic], f, indent=2)

    print(f"Wrote {len(buffers[topic])} records → {path}")

print("\nKafka dump complete.")