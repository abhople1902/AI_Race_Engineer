from confluent_kafka import Consumer, Producer, TopicPartition
import time

LOCAL_BOOTSTRAP = "localhost:29092"

CLOUD_BOOTSTRAP = "pkc-41p56.asia-south1.gcp.confluent.cloud:9092"
CLOUD_API_KEY = "L5MXDTE6XXNJ3YMS"
CLOUD_API_SECRET = "cfltgdYsasS6uTycPZDBqGFYA7uc+6rx+FCYUfxUcHUZt/HtGgmpjM+Q7PLQzGEg"

TOPIC = "f1.race_control.raw"

consumer = Consumer({
    "bootstrap.servers": LOCAL_BOOTSTRAP,
    "group.id": "migration-group",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
})

producer = Producer({
    "bootstrap.servers": CLOUD_BOOTSTRAP,
    "security.protocol": "SASL_SSL",
    "sasl.mechanism": "PLAIN",
    "sasl.username": CLOUD_API_KEY,
    "sasl.password": CLOUD_API_SECRET,
})

consumer.subscribe([TOPIC])

print("Waiting for partition assignment...")
while not consumer.assignment():
    consumer.poll(0.1)

partitions = consumer.assignment()

# Get end offsets
end_offsets = {}
for tp in partitions:
    low, high = consumer.get_watermark_offsets(tp)
    end_offsets[(tp.topic, tp.partition)] = high

print("Starting migration...")
message_count = 0

while True:
    msg = consumer.poll(1.0)

    if msg is None:
        continue

    if msg.error():
        continue

    producer.produce(
        TOPIC,
        key=msg.key(),
        value=msg.value(),
    )

    producer.poll(0)
    message_count += 1

    # Check if reached end of partition
    tp_key = (msg.topic(), msg.partition())
    if msg.offset() + 1 >= end_offsets[tp_key]:
        print(f"Finished partition {tp_key}")

        # Remove partition from tracking
        del end_offsets[tp_key]

        if not end_offsets:
            break

producer.flush()
consumer.close()

print(f"Migration complete. Total messages migrated: {message_count}")