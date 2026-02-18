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

from app.settings import KAFKA_BOOTSTRAP_SERVERS

import os

DEBUG_ASSERTIONS = True
try: 
    from app.assertions import validate_output
except ImportError:
    validate_output = None
    DEBUG_ASSERTIONS = False


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
