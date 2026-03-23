# from confluent_kafka import Consumer, Producer, TopicPartition
# import time
# from datetime import datetime
# import json

# LOCAL_BOOTSTRAP = "localhost:29092"

# CLOUD_BOOTSTRAP = "pkc-41p56.asia-south1.gcp.confluent.cloud:9092"
# CLOUD_API_KEY = "L5MXDTE6XXNJ3YMS"
# CLOUD_API_SECRET = "cfltgdYsasS6uTycPZDBqGFYA7uc+6rx+FCYUfxUcHUZt/HtGgmpjM+Q7PLQzGEg"

# TOPIC = "f1.race_control.raw"

# consumer = Consumer({
#     "bootstrap.servers": LOCAL_BOOTSTRAP,
#     "group.id": "migration-group",
#     "auto.offset.reset": "earliest",
#     "enable.auto.commit": False,
# })

# producer = Producer({
#     "bootstrap.servers": CLOUD_BOOTSTRAP,
#     "security.protocol": "SASL_SSL",
#     "sasl.mechanism": "PLAIN",
#     "sasl.username": CLOUD_API_KEY,
#     "sasl.password": CLOUD_API_SECRET,
# })

# consumer.subscribe([TOPIC])

# def extract_event_time(event):
#     if "event_time" in event:
#         value = event["event_time"]

#         if isinstance(value, int):
#             return value

#         if isinstance(value, str):
#             try:
#                 dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
#                 return int(dt.timestamp() * 1000)
#             except Exception:
#                 return None

#     if "date" in event:
#         try:
#             dt = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
#             return int(dt.timestamp() * 1000)
#         except Exception:
#             return None

#     return None

# print("Waiting for partition assignment...")
# while not consumer.assignment():
#     consumer.poll(0.1)

# partitions = consumer.assignment()

# # Get end offsets
# end_offsets = {}
# for tp in partitions:
#     low, high = consumer.get_watermark_offsets(tp)
#     end_offsets[(tp.topic, tp.partition)] = high

# print("Starting migration...")
# message_count = 0

# while True:
#     msg = consumer.poll(1.0)

#     if msg is None:
#         continue

#     if msg.error():
#         continue

#     # ts_ms = extract_event_time(json.loads(msg.value().decode("utf-8")))

#     producer.produce(
#         TOPIC,
#         key=msg.key(),
#         value=msg.value(),
#     )

#     producer.poll(0)
#     message_count += 1

#     # Check if reached end of partition
#     tp_key = (msg.topic(), msg.partition())
#     if msg.offset() + 1 >= end_offsets[tp_key]:
#         print(f"Finished partition {tp_key}")

#         # Remove partition from tracking
#         del end_offsets[tp_key]

#         if not end_offsets:
#             break

# producer.flush()
# consumer.close()

# print(f"Migration complete. Total messages migrated: {message_count}")





















from confluent_kafka import Consumer, Producer, TopicPartition
from datetime import datetime
import json

LOCAL_BOOTSTRAP = "localhost:29092"
CLOUD_BOOTSTRAP = "pkc-ldvr1.asia-southeast1.gcp.confluent.cloud:9092"
CLOUD_API_KEY = "E2TFOTAVENZCIKLD"
CLOUD_API_SECRET = "cfltb7yL2jsKDSeCoeJ1BlmOH44Y+QJKx+ZDZ+oF37iDziNIRAZpPyrKIiMWueDg"

TOPIC = "f1.race_control.raw"

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