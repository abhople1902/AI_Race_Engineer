# app/main.py

# import signal
# import sys
# from typing import List, Dict, Any

# from app.interval_normalizer.normalizer import IntervalNormalizer
# from app.consumer import RawEventConsumer
# from app.producer import NormalizedEventProducer

# from app.leaderboard.builder import LeaderboardBuilder
# from app.leaderboard.state import LeaderboardState
# from app.leaderboard.emitter import format_leaderboard

# from app.settings import KAFKA_BOOTSTRAP_SERVERS

# # Optional: keep assertions during early live testing
# DEBUG_ASSERTIONS = True
# try:
#     from app.assertions import validate_output
# except ImportError:
#     validate_output = None
#     DEBUG_ASSERTIONS = False


# def main():
#     print("Starting Stream Processor Service (Interval Normalizer)")
#     print(f"Kafka bootstrap servers: {KAFKA_BOOTSTRAP_SERVERS}")

#     # =========================
#     # Core components
#     # =========================

#     normalizer = IntervalNormalizer(session_key=None)

#     leaderboard_state = LeaderboardState()
#     leaderboard_builder = LeaderboardBuilder(leaderboard_state)

#     consumer = RawEventConsumer(group_id="interval-normalizer-debug2")
#     producer = NormalizedEventProducer()

#     running = True

#     # =========================
#     # Signal handling
#     # =========================

#     def shutdown_handler(sig, frame):
#         nonlocal running
#         print("Shutdown signal received. Stopping main loop...")
#         running = False

#     signal.signal(signal.SIGINT, shutdown_handler)
#     signal.signal(signal.SIGTERM, shutdown_handler)

#     # =========================
#     # Main processing loop
#     # =========================

#     while running:
#         try:
#             # ---- Batch poll ----
#             events: List[Dict[str, Any]] = consumer.poll_batch(max_messages=200, timeout=3.0)

#             if not events:
#                 print("[consumer] no new messages")
#                 continue

#             # ---- Process batch ----
#             print("\n\n\n----------------------")
#             for event in events:
#                 # Lazily bind session_key once
#                 if normalizer.session_state.session_key is None:
#                     normalizer.session_state.session_key = event.get("session_key")

#                 print(f"[consumer] sending event to normalize: {event}\n")
#                 result = normalizer.process_event(event)

#                 if result is not None:
#                     if DEBUG_ASSERTIONS and validate_output is not None:
#                         validate_output(
#                             result,
#                             normalizer.session_state,
#                             strict=True,
#                         )
#                     print(f"[consumer] producing to kafka: {result}\n")
#                     producer.send_normalized(result)

#                     leaderboard_event = leaderboard_builder.process_event(result)
#                     if leaderboard_event is not None:
#                         producer.send_leaderboard(
#                             format_leaderboard(leaderboard_event)
#                         )
#                 else:
#                     print("❌❌❌❌result is none")

#             # ---- Commit offsets AFTER successful batch ----
#             print("\n\n")
#             consumer.commit()

#         except Exception as e:
#             # Do NOT commit offsets on failure
#             # Kafka will replay the batch
#             print(f"[ERROR] Batch processing failed: {e}", file=sys.stderr)

#     # =========================
#     # Graceful shutdown
#     # =========================

#     print("Flushing producer and closing consumer...")
#     try:
#         producer.flush()
#     finally:
#         consumer.close()

#     print("Stream Processor Service stopped cleanly.")


# if __name__ == "__main__":
#     main()


























# app/main.py

import signal
import sys
from typing import List, Dict, Any

from app.interval_normalizer.normalizer import IntervalNormalizer
from app.consumer import RawEventConsumer
from app.consumer_normalized import NormalizedEventConsumer
from app.producer import NormalizedEventProducer

from app.leaderboard.builder import LeaderboardBuilder
from app.leaderboard.state import LeaderboardState
from app.leaderboard.emitter import format_leaderboard
from app.redis_writer import RedisWriter

from app.settings import KAFKA_BOOTSTRAP_SERVERS

from redis import Redis
import os

DEBUG_ASSERTIONS = True
try: 
    from app.assertions import validate_output
except ImportError:
    validate_output = None
    DEBUG_ASSERTIONS = False

redis_client = Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True
)

def main():
    print("Starting Stream Processor Service")
    print(f"Kafka bootstrap servers: {KAFKA_BOOTSTRAP_SERVERS}")

    # -----------------------------
    # Interval Normalizer pipeline
    # -----------------------------
    normalizer = IntervalNormalizer(session_key=None)
    raw_consumer = RawEventConsumer(group_id="interval-normalizer")
    producer = NormalizedEventProducer()

    # -----------------------------
    # Leaderboard pipeline
    # -----------------------------
    leaderboard_state = LeaderboardState()
    leaderboard_builder = LeaderboardBuilder(leaderboard_state)
    normalized_consumer = NormalizedEventConsumer(group_id="leaderboard-builder")

    redis_writer = RedisWriter(redis_client)

    try:
        redis_client.ping()
        print("Redis connection OK")
    except Exception as e:
        print(f"[FATAL] Redis not available: {e}")
        sys.exit(1)

    running = True

    def shutdown_handler(sig, frame):
        nonlocal running
        print("Shutdown signal received")
        running = False

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    while running:
        try:
            # ===== 1️⃣ Normalize raw events =====
            raw_events = raw_consumer.poll_batch(max_messages=200, timeout=1.0)

            for event in raw_events:
                if normalizer.session_state.session_key is None:
                    normalizer.session_state.session_key = event.get("session_key")

                result = normalizer.process_event(event)
                if result is not None:
                    if DEBUG_ASSERTIONS and validate_output is not None:
                        validate_output(result, normalizer.session_state, strict=True)

                    producer.send_normalized(result)

            if raw_events:
                raw_consumer.commit()

            # ===== 2️⃣ Build leaderboard from Kafka-normalized =====
            normalized_events = normalized_consumer.poll_batch(max_messages=200, timeout=1.0)

            for nevent in normalized_events:
                leaderboard_event = leaderboard_builder.process_event(nevent)
                if leaderboard_event is not None:
                    formatted = format_leaderboard(leaderboard_event)
                    producer.send_leaderboard(formatted)
                    redis_writer.write_leaderboard(formatted)

            if normalized_events:
                normalized_consumer.commit()

        except Exception as e:
            print(f"[ERROR] Processing failed: {e}", file=sys.stderr)

    # -----------------------------
    # Shutdown
    # -----------------------------
    print("Shutting down cleanly...")
    try:
        producer.flush()
    finally:
        raw_consumer.close()
        normalized_consumer.close()

    print("Stream Processor Service stopped.")


if __name__ == "__main__":
    main()
