import signal
import sys

from redis import Redis

from app.consumer_leaderboard import LeaderboardEventConsumer
from app.redis_writer import RedisWriter
from app.consumer_race_control import RaceControlConsumer
from app.settings import REDIS_HOST, REDIS_PORT

from app.stint_ingestor import StintIngestor
from app.settings import OPENF1_BASE_URL


def main():
    print("Starting Redis Writer Service")

    redis_client = Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,
    )

    try:
        redis_client.ping()
        print("Redis connection OK")
    except Exception as e:
        print(f"[FATAL] Redis unavailable: {e}")
        sys.exit(1)

    stint_ingestor = StintIngestor(
        base_url=OPENF1_BASE_URL
    )
    current_session_id = None

    consumer = LeaderboardEventConsumer(
        group_id="redis-writer"
    )
    race_control_consumer = RaceControlConsumer(
        group_id="redis-writer-race-control"
    )

    writer = RedisWriter(redis_client)

    running = True

    def shutdown_handler(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    while running:
        try:
            events = consumer.poll_batch(max_messages=200, timeout=1.0)

            rc_events = race_control_consumer.poll_batch(max_messages=200, timeout=0.5)

            for event in events:
                session_id = event["session_key"]
                lap_number = event["lap_number"]

                # Load stints once per session
                if current_session_id != session_id:
                    print("GETTING STINTS 🛞🛞🛞")
                    stint_ingestor.load_session_stints(session_id)
                    current_session_id = session_id

                # Write stint state for active drivers
                for entry in event["standings"]:
                    driver_number = entry["driver_number"]

                    stint = stint_ingestor.get_current_stint(
                        driver_number=driver_number,
                        lap_number=lap_number,
                    )

                    if stint is not None:
                        writer.write_stint_state(
                            session_id=session_id,
                            driver_number=driver_number,
                            stint=stint,
                            lap_number=lap_number,
                        )

                writer.write_leaderboard(event)

            for event in rc_events:
                writer.write_race_control(event)

            if events:
                consumer.commit()

            if rc_events:
                race_control_consumer.commit()

        except Exception as e:
            print(f"[ERROR] Redis writer failed: {e}", file=sys.stderr)

    race_control_consumer.close()
    consumer.close()
    print("Redis Writer Service stopped cleanly.")


if __name__ == "__main__":
    main()
