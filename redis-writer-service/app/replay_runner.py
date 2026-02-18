import time
import json
from confluent_kafka import Consumer, TopicPartition
from app.settings import KAFKA_BOOTSTRAP_SERVERS, LEADERBOARD_TOPIC


class ReplayRunner:

    def __init__(self, session_key, start_timestamp_ms, simulation_id):
        self.session_key = str(session_key)
        self.start_timestamp_ms = start_timestamp_ms
        self.simulation_id = simulation_id

        self.consumer = Consumer({
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "group.id": f"replay-{simulation_id}",
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
        })

    def run(self, writer, redis_client):
        metadata = self.consumer.list_topics(LEADERBOARD_TOPIC, timeout=10)
        partitions = metadata.topics[LEADERBOARD_TOPIC].partitions

        target_partition = None

        for p in partitions:
            tp = TopicPartition(
                LEADERBOARD_TOPIC,
                p,
                self.start_timestamp_ms,
            )
            offsets = self.consumer.offsets_for_times([tp], timeout=10)

            if offsets and offsets[0] and offsets[0].offset != -1:
                target_partition = p
                break

        if target_partition is None:
            self.consumer.close()
            return

        self.consumer.assign([TopicPartition(LEADERBOARD_TOPIC, target_partition)])

        tp = TopicPartition(
            LEADERBOARD_TOPIC,
            target_partition,
            self.start_timestamp_ms,
        )

        offsets = self.consumer.offsets_for_times([tp])
        offset = offsets[0].offset

        self.consumer.seek(
            TopicPartition(LEADERBOARD_TOPIC, target_partition, offset)
        )

        idle_polls = 0

        while True:
            msg = self.consumer.poll(1.0)

            if msg is None:
                idle_polls += 1
                if idle_polls > 5:
                    break
                continue

            idle_polls = 0

            if msg.error():
                continue

            event = json.loads(msg.value().decode("utf-8"))

            if str(event["session_key"]) != self.session_key:
                continue

            writer.write_leaderboard(
                event,
                simulation_id=self.simulation_id,
            )

            time.sleep(0.2)

        self.consumer.close()

        # Cleanup namespace
        keys = redis_client.keys(f"sim:{self.simulation_id}:*")
        if keys:
            redis_client.delete(*keys)
