import time
import json
import zlib
import threading
import heapq
from confluent_kafka import Consumer, TopicPartition
from datetime import datetime, timezone

from app.stint_ingestor import StintIngestor
from app.settings import OPENF1_BASE_URL
from app.settings import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_API_KEY,
    KAFKA_API_SECRET,
    LEADERBOARD_TOPIC,
    RACE_CONTROL_TOPIC,
)

MAX_HEAP_SIZE = 1000

stint_ingestor = StintIngestor(base_url=OPENF1_BASE_URL)


class ReplayRunner:

    def __init__(self, session_key, start_timestamp_ms, simulation_id):
        self.session_key = str(session_key)
        self.start_timestamp_ms = start_timestamp_ms
        self.simulation_id = simulation_id

        print(f"[REPLAY] Initializing replay for session={self.session_key}", flush=True)
        print(f"[REPLAY] Start timestamp (ms)={self.start_timestamp_ms}", flush=True)
        print(f"[REPLAY] Simulation ID={self.simulation_id}", flush=True)

        self.consumer = Consumer({
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "security.protocol": "SASL_SSL",
            "sasl.mechanism": "PLAIN",
            "sasl.username": KAFKA_API_KEY,
            "sasl.password": KAFKA_API_SECRET,
            "ssl.endpoint.identification.algorithm": "https",
            "group.id": f"replay-{simulation_id}",
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
        })

        self.heap = []
        self.sequence = 0
        self.stop_event = threading.Event()
        self.loader_finished = False
        self.stop_requested = False

    def request_stop(self):
        self.stop_requested = True
        self.stop_event.set()

    def _status_key(self) -> str:
        return f"sim:{self.simulation_id}:session:{self.session_key}:replay_status"

    def _set_status(self, redis_client, status: str, detail: str | None = None):
        payload = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        if detail:
            payload["detail"] = detail
        redis_client.hset(self._status_key(), mapping=payload)

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

        print(f"[REPLAY] RaceControl start offset={offset}", flush=True)
        return TopicPartition(RACE_CONTROL_TOPIC, partition_id, offset)


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

        print("[REPLAY] Loader started", flush=True)
        idle_polls = 0
        total_loaded = 0
        
        stint_ingestor.load_session_stints(self.session_key)
        while not self.stop_event.is_set():

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
                print(f"[REPLAY] Loaded {total_loaded} events | Heap size={len(self.heap)}", flush=True)

        print(f"[REPLAY] Loader finished | Total loaded={total_loaded}", flush=True)
        self.loader_finished = True

    # ------------------------------------------------

    def _emitter_loop(self, writer):

        print("[REPLAY] Emitter started", flush=True)
        total_emitted = 0

        previous_event_time = None
        MIN_SLEEP = 1
        MAX_SLEEP = 10.0

        while not self.stop_event.is_set():

            if self.heap:
                event_time, _, topic, event = heapq.heappop(self.heap)
                delta_ms = 0

                if previous_event_time is not None:
                    delta_ms = event_time - previous_event_time

                    if delta_ms > 0:
                        sleep_seconds = (delta_ms / 1000.0)
                        sleep_seconds = max(MIN_SLEEP, min(MAX_SLEEP, sleep_seconds))
                        time.sleep(sleep_seconds)

                previous_event_time = event_time

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
                    f"(delta={delta_ms}) | Heap size={len(self.heap)}",
                    flush=True
                )

            else:
                if self.loader_finished:
                    break
                time.sleep(3.0)

        print(f"[REPLAY] Emitter finished | Total emitted={total_emitted}", flush=True)
        self.stop_event.set()

    # ------------------------------------------------

    def run(self, writer, redis_client):

        print("[REPLAY] Starting replay run", flush=True)
        self._set_status(redis_client, "RUNNING")

        try:
            metadata = self.consumer.list_topics(timeout=10)
            lb_meta = metadata.topics.get(LEADERBOARD_TOPIC)
            rc_meta = metadata.topics.get(RACE_CONTROL_TOPIC)

            if not lb_meta or not rc_meta:
                print("[REPLAY] Topics missing", flush=True)
                self._set_status(redis_client, "FAILED", "Topics missing")
                return

            lb_partition = self._partition_for_session(len(lb_meta.partitions))
            rc_partition = self._partition_for_session(len(rc_meta.partitions))

            assignments = [
                self._resolve_leaderboard_start_tp(lb_partition),
                self._resolve_race_control_start_tp(rc_partition),
            ]

            self.consumer.assign(assignments)

            loader_thread = threading.Thread(target=self._loader_loop, daemon=True)
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

            if self.stop_requested:
                self._set_status(redis_client, "STOPPED")
                print("[REPLAY] Replay stopped by request", flush=True)
            else:
                self._set_status(redis_client, "COMPLETED")
                print("[REPLAY] Replay complete", flush=True)
        except Exception as exc:
            self._set_status(redis_client, "FAILED", str(exc))
            print(f"[REPLAY] Failed: {exc}", flush=True)
            raise
        finally:
            self.stop_event.set()
            self.consumer.close()
