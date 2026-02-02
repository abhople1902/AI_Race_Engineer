import signal
import sys

from redis import Redis

from app.consumer_leaderboard import LeaderboardEventConsumer
from app.redis_writer import RedisWriter
from app.settings import REDIS_HOST, REDIS_PORT


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

    consumer = LeaderboardEventConsumer(
        group_id="redis-writer"
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

            for event in events:
                writer.write_leaderboard(event)

            if events:
                consumer.commit()

        except Exception as e:
            print(f"[ERROR] Redis writer failed: {e}", file=sys.stderr)

    consumer.close()
    print("Redis Writer Service stopped cleanly.")


if __name__ == "__main__":
    main()
