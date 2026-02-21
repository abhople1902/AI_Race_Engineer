# import time
# import json
# import zlib
# import threading
# from collections import deque
# from confluent_kafka import Consumer, TopicPartition

# from app.settings import (
#     KAFKA_BOOTSTRAP_SERVERS,
#     LEADERBOARD_TOPIC,
#     RACE_CONTROL_TOPIC,
# )


# MAX_QUEUE_SIZE = 100
# LOW_WATERMARK = 500
# EMIT_INTERVAL = 5


# class ReplayRunner:

#     def __init__(self, session_key, start_timestamp_ms, simulation_id):
#         self.session_key = str(session_key)
#         self.start_timestamp_ms = start_timestamp_ms
#         self.simulation_id = simulation_id

#         print(f"[REPLAY] Initializing replay for session={self.session_key}")
#         print(f"[REPLAY] Start timestamp (ms)={self.start_timestamp_ms}")
#         print(f"[REPLAY] Simulation ID={self.simulation_id}")

#         self.consumer = Consumer({
#             "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
#             "group.id": f"replay-{simulation_id}",
#             "enable.auto.commit": False,
#             "auto.offset.reset": "earliest",
#         })

#         self.queue = deque()
#         self.stop_event = threading.Event()
#         self.loader_finished = False

#     # ---------------------------------

#     def _partition_for_session(self, partition_count: int) -> int:
#         key_bytes = self.session_key.encode("utf-8")
#         positive_hash = zlib.crc32(key_bytes) & 0x7FFFFFFF
#         partition = positive_hash % partition_count
#         print(f"[REPLAY] Resolved partition {partition} for session {self.session_key}")
#         return partition

#     def _resolve_leaderboard_start_tp(self, partition_id: int) -> TopicPartition:
#         requested = TopicPartition(
#             LEADERBOARD_TOPIC,
#             partition_id,
#             self.start_timestamp_ms,
#         )

#         resolved = self.consumer.offsets_for_times([requested], timeout=10)[0]
#         offset = resolved.offset if resolved and resolved.offset is not None else -1

#         if offset == -1:
#             print("[REPLAY] No offset found for timestamp — using high watermark")
#             _, high = self.consumer.get_watermark_offsets(
#                 TopicPartition(LEADERBOARD_TOPIC, partition_id),
#                 timeout=10,
#             )
#             offset = high

#         print(f"[REPLAY] Leaderboard start offset={offset}")
#         return TopicPartition(LEADERBOARD_TOPIC, partition_id, offset)

#     def _resolve_race_control_start_tp(self, partition_id: int) -> TopicPartition:
#         low, _ = self.consumer.get_watermark_offsets(
#             TopicPartition(RACE_CONTROL_TOPIC, partition_id),
#             timeout=10,
#         )
#         print(f"[REPLAY] RaceControl start offset={low}")
#         return TopicPartition(RACE_CONTROL_TOPIC, partition_id, low)

#     # ---------------------------------
#     # Loader Thread
#     # ---------------------------------

#     def _loader_loop(self):

#         print("[REPLAY] Loader thread started")

#         idle_polls = 0
#         total_loaded = 0

#         while not self.stop_event.is_set():

#             if len(self.queue) >= MAX_QUEUE_SIZE:
#                 print("[REPLAY] Queue full — pausing loader")
#                 time.sleep(50)
#                 continue

#             msg = self.consumer.poll(1.0)

#             if msg is None:
#                 idle_polls += 1
#                 print(f"[REPLAY] Poll returned None ({idle_polls})")

#                 if idle_polls > 5:
#                     print("[REPLAY] No more Kafka messages — loader finishing")
#                     self.loader_finished = True
#                     break

#                 continue

#             idle_polls = 0

#             if msg.error():
#                 print(f"[REPLAY] Kafka error: {msg.error()}")
#                 continue

#             try:
#                 event = json.loads(msg.value().decode("utf-8"))
#             except Exception as e:
#                 print(f"[REPLAY] JSON decode failed: {e}")
#                 continue

#             if str(event.get("session_key")) != self.session_key:
#                 continue

#             self.queue.append({
#                 "topic": msg.topic(),
#                 "event": event
#             })

#             total_loaded += 1

#             if total_loaded % 50 == 0:
#                 print(f"[REPLAY] Loaded {total_loaded} events | Queue size={len(self.queue)}")

#         print(f"[REPLAY] Loader exiting | Total loaded={total_loaded}")
#         self.loader_finished = True

#     # ---------------------------------
#     # Emitter Thread
#     # ---------------------------------

#     def _emitter_loop(self, writer):

#         print("[REPLAY] Emitter thread started")

#         total_emitted = 0

#         while not self.stop_event.is_set():

#             if self.queue:
#                 item = self.queue.popleft()

#                 if item["topic"] == LEADERBOARD_TOPIC:
#                     writer.write_leaderboard(
#                         item["event"],
#                         simulation_id=self.simulation_id,
#                     )
#                 if item["topic"] == RACE_CONTROL_TOPIC:
#                     writer.write_race_control(
#                         item["event"],
#                         simulation_id=self.simulation_id,
#                     )

#                 total_emitted += 1

#                 print(f"[REPLAY] Emitted {total_emitted} events | Queue size={len(self.queue)}")

#             else:
#                 if self.loader_finished:
#                     print("[REPLAY] Queue empty and loader finished — stopping replay")
#                     break

#             time.sleep(EMIT_INTERVAL)

#         print(f"[REPLAY] Emitter exiting | Total emitted={total_emitted}")
#         self.stop_event.set()

#     # ---------------------------------

#     def run(self, writer, redis_client):

#         print("[REPLAY] Starting run()")

#         metadata = self.consumer.list_topics(timeout=10)
#         lb_meta = metadata.topics.get(LEADERBOARD_TOPIC)
#         rc_meta = metadata.topics.get(RACE_CONTROL_TOPIC)

#         if (
#             lb_meta is None
#             or rc_meta is None
#             or not lb_meta.partitions
#             or not rc_meta.partitions
#         ):
#             print("[REPLAY] Topics not found or empty")
#             self.consumer.close()
#             return

#         lb_partition = self._partition_for_session(len(lb_meta.partitions))
#         rc_partition = self._partition_for_session(len(rc_meta.partitions))

#         assignments = [
#             self._resolve_leaderboard_start_tp(lb_partition),
#             self._resolve_race_control_start_tp(rc_partition),
#         ]

#         self.consumer.assign(assignments)

#         for tp in assignments:
#             self.consumer.seek(tp)
#             position = self.consumer.position([tp])[0]
#             print(f"[REPLAY] Seeking {tp.topic} partition {tp.partition} to offset {position.offset}")

#         loader_thread = threading.Thread(
#             target=self._loader_loop,
#             daemon=True
#         )

#         emitter_thread = threading.Thread(
#             target=self._emitter_loop,
#             args=(writer,),
#             daemon=True
#         )

#         loader_thread.start()
#         emitter_thread.start()

#         emitter_thread.join()

#         self.stop_event.set()
#         loader_thread.join()

#         print("[REPLAY] Closing Kafka consumer")
#         self.consumer.close()
#         print("[REPLAY] Replay complete")



















import time
import json
import zlib
import threading
import heapq
from confluent_kafka import Consumer, TopicPartition

from datetime import datetime

from app.stint_ingestor import StintIngestor
from app.settings import OPENF1_BASE_URL
from app.settings import (
    KAFKA_BOOTSTRAP_SERVERS,
    LEADERBOARD_TOPIC,
    RACE_CONTROL_TOPIC,
)


MAX_HEAP_SIZE = 1000
EMIT_INTERVAL = 1

stint_ingestor = StintIngestor(base_url=OPENF1_BASE_URL)


class ReplayRunner:

    def __init__(self, session_key, start_timestamp_ms, simulation_id):
        self.session_key = str(session_key)
        self.start_timestamp_ms = start_timestamp_ms
        self.simulation_id = simulation_id

        print(f"[REPLAY] Initializing replay for session={self.session_key}")
        print(f"[REPLAY] Start timestamp (ms)={self.start_timestamp_ms}")
        print(f"[REPLAY] Simulation ID={self.simulation_id}")

        self.consumer = Consumer({
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "group.id": f"replay-{simulation_id}",
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
        })

        self.heap = []
        self.sequence = 0
        self.stop_event = threading.Event()
        self.loader_finished = False

    # ------------------------------------------------

    def _partition_for_session(self, partition_count: int) -> int:
        key_bytes = self.session_key.encode("utf-8")
        positive_hash = zlib.crc32(key_bytes) & 0x7FFFFFFF
        return positive_hash % partition_count

    def _resolve_leaderboard_start_tp(self, partition_id: int) -> TopicPartition:
        requested = TopicPartition(
            LEADERBOARD_TOPIC,
            partition_id,
            self.start_timestamp_ms,
        )

        resolved = self.consumer.offsets_for_times([requested], timeout=10)[0]
        offset = resolved.offset if resolved and resolved.offset is not None else -1

        if offset == -1:
            _, high = self.consumer.get_watermark_offsets(
                TopicPartition(LEADERBOARD_TOPIC, partition_id),
                timeout=10,
            )
            offset = high

        return TopicPartition(LEADERBOARD_TOPIC, partition_id, offset)

    def _resolve_race_control_start_tp(self, partition_id: int) -> TopicPartition:
        requested = TopicPartition(
            RACE_CONTROL_TOPIC,
            partition_id,
            self.start_timestamp_ms,
        )

        resolved = self.consumer.offsets_for_times([requested], timeout=10)[0]
        offset = resolved.offset if resolved and resolved.offset is not None else -1

        if offset == -1:
            _, high = self.consumer.get_watermark_offsets(
                TopicPartition(RACE_CONTROL_TOPIC, partition_id),
                timeout=10,
            )
            offset = high

        print(f"[REPLAY] RaceControl start offset={offset}")
        return TopicPartition(RACE_CONTROL_TOPIC, partition_id, offset)

    # ------------------------------------------------
    # Loader
    # ------------------------------------------------
    def _extract_event_time(self, event):
        if "event_time" in event:
            value = event["event_time"]

            if isinstance(value, int):
                return value

            if isinstance(value, str):
                try:
                    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    return int(dt.timestamp() * 1000)
                except Exception:
                    return None

        if "date" in event:
            try:
                dt = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
                return int(dt.timestamp() * 1000)
            except Exception:
                return None

        return None

    def _loader_loop(self):

        print("[REPLAY] Loader started")
        idle_polls = 0
        total_loaded = 0
        
        stint_ingestor.load_session_stints(self.session_key)
        while not self.stop_event.is_set():

            # Prevent unbounded growth
            if len(self.heap) >= MAX_HEAP_SIZE:
                time.sleep(20)
                continue

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

            if str(event.get("session_key")) != self.session_key:
                continue

            event_time = self._extract_event_time(event)
            if event_time is None:
                continue

            heapq.heappush(
                self.heap,
                (event_time, self.sequence, msg.topic(), event)
            )
            self.sequence += 1
            total_loaded += 1

            if total_loaded % 100 == 0:
                print(f"[REPLAY] Loaded {total_loaded} events | Heap size={len(self.heap)}")

        print(f"[REPLAY] Loader finished | Total loaded={total_loaded}")
        self.loader_finished = True

    # ------------------------------------------------
    # Emitter
    # ------------------------------------------------

    def _emitter_loop(self, writer):

        print("[REPLAY] Emitter started")
        total_emitted = 0

        

        while not self.stop_event.is_set():

            if self.heap:
                event_time, _, topic, event = heapq.heappop(self.heap)

                if topic == LEADERBOARD_TOPIC:
                    writer.write_leaderboard(
                        event,
                        simulation_id=self.simulation_id,
                    )

                if topic == RACE_CONTROL_TOPIC:
                    writer.write_race_control(
                        event,
                        simulation_id=self.simulation_id,
                    )

                if "lap_number" in event and "standings" in event:
                    lap_number = event["lap_number"]
                    for entry in event["standings"]:
                        driver_number = entry["driver_number"]

                        stint = stint_ingestor.get_current_stint(
                            driver_number=driver_number,
                            lap_number=lap_number,
                        )
                        if stint is not None:
                            writer.write_stint_state(
                                session_id=self.session_key,
                                driver_number=driver_number,
                                stint=stint,
                                lap_number=lap_number,
                                simulation_id=self.simulation_id
                            )

                total_emitted += 1

                print(
                    f"[REPLAY] Emitted {total_emitted} "
                    f"(event_time={event_time}) | Heap size={len(self.heap)}"
                )

            else:
                if self.loader_finished:
                    break

            time.sleep(EMIT_INTERVAL)

        print(f"[REPLAY] Emitter finished | Total emitted={total_emitted}")
        self.stop_event.set()

    # ------------------------------------------------

    def run(self, writer, redis_client):

        print("[REPLAY] Starting replay run")

        metadata = self.consumer.list_topics(timeout=10)
        lb_meta = metadata.topics.get(LEADERBOARD_TOPIC)
        rc_meta = metadata.topics.get(RACE_CONTROL_TOPIC)

        if not lb_meta or not rc_meta:
            print("[REPLAY] Topics missing")
            self.consumer.close()
            return

        lb_partition = self._partition_for_session(len(lb_meta.partitions))
        rc_partition = self._partition_for_session(len(rc_meta.partitions))

        assignments = [
            self._resolve_leaderboard_start_tp(lb_partition),
            self._resolve_race_control_start_tp(rc_partition),
        ]

        self.consumer.assign(assignments)

        loader_thread = threading.Thread(
            target=self._loader_loop,
            daemon=True
        )

        emitter_thread = threading.Thread(
            target=self._emitter_loop,
            args=(writer,),
            daemon=True
        )

        loader_thread.start()
        emitter_thread.start()

        emitter_thread.join()
        self.stop_event.set()
        loader_thread.join()

        self.consumer.close()

        print("[REPLAY] Replay complete")