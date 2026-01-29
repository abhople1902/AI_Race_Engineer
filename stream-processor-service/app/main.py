# app/main.py

import signal
import sys
from typing import List, Dict, Any

from app.interval_normalizer.normalizer import IntervalNormalizer
from app.consumer import RawEventConsumer
from app.producer import NormalizedEventProducer

from app.leaderboard.builder import LeaderboardBuilder
from app.leaderboard.state import LeaderboardState
from app.leaderboard.emitter import format_leaderboard

from app.settings import KAFKA_BOOTSTRAP_SERVERS

# Optional: keep assertions during early live testing
DEBUG_ASSERTIONS = True
try:
    from app.assertions import validate_output
except ImportError:
    validate_output = None
    DEBUG_ASSERTIONS = False


def main():
    print("Starting Stream Processor Service (Interval Normalizer)")
    print(f"Kafka bootstrap servers: {KAFKA_BOOTSTRAP_SERVERS}")

    # =========================
    # Core components
    # =========================

    normalizer = IntervalNormalizer(session_key=None)

    leaderboard_state = LeaderboardState()
    leaderboard_builder = LeaderboardBuilder(leaderboard_state)

    consumer = RawEventConsumer(group_id="interval-normalizer-debug2")
    producer = NormalizedEventProducer()

    running = True

    # =========================
    # Signal handling
    # =========================

    def shutdown_handler(sig, frame):
        nonlocal running
        print("Shutdown signal received. Stopping main loop...")
        running = False

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # =========================
    # Main processing loop
    # =========================

    while running:
        try:
            # ---- Batch poll ----
            events: List[Dict[str, Any]] = consumer.poll_batch(max_messages=200, timeout=3.0)

            if not events:
                print("[consumer] no new messages")
                continue

            # ---- Process batch ----
            print("\n\n\n----------------------")
            for event in events:
                # Lazily bind session_key once
                if normalizer.session_state.session_key is None:
                    normalizer.session_state.session_key = event.get("session_key")

                print(f"[consumer] sending event to normalize: {event}\n")
                result = normalizer.process_event(event)

                if result is not None:
                    if DEBUG_ASSERTIONS and validate_output is not None:
                        validate_output(
                            result,
                            normalizer.session_state,
                            strict=True,
                        )
                    print(f"[consumer] producing to kafka: {result}\n")
                    producer.send_normalized(result)

                    leaderboard_event = leaderboard_builder.process_event(result)
                    if leaderboard_event is not None:
                        producer.send_leaderboard(
                            format_leaderboard(leaderboard_event)
                        )
                else:
                    print("❌❌❌❌result is none")

            # ---- Commit offsets AFTER successful batch ----
            print("\n\n")
            consumer.commit()

        except Exception as e:
            # Do NOT commit offsets on failure
            # Kafka will replay the batch
            print(f"[ERROR] Batch processing failed: {e}", file=sys.stderr)

    # =========================
    # Graceful shutdown
    # =========================

    print("Flushing producer and closing consumer...")
    try:
        producer.flush()
    finally:
        consumer.close()

    print("Stream Processor Service stopped cleanly.")


if __name__ == "__main__":
    main()
