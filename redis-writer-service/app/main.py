# import signal
# import sys

# from redis import Redis

# from app.consumer_leaderboard import LeaderboardEventConsumer
# from app.redis_writer import RedisWriter
# from app.consumer_race_control import RaceControlConsumer
# from app.settings import REDIS_HOST, REDIS_PORT

# from app.stint_ingestor import StintIngestor
# from app.settings import OPENF1_BASE_URL
# from app.service_controller import ServiceMode


# current_mode = ServiceMode.LIVE
# live_thread = None



# def run_live_loop(consumer, race_control_consumer, writer, stint_ingestor):
#     current_session_id = None

#     while current_mode == ServiceMode.LIVE:
#         events = consumer.poll_batch(max_messages=200, timeout=1.0)
#         rc_events = race_control_consumer.poll_batch(max_messages=200, timeout=0.5)

#         for event in events:
#             session_id = event["session_key"]
#             lap_number = event["lap_number"]

#             if current_session_id != session_id:
#                 stint_ingestor.load_session_stints(session_id)
#                 current_session_id = session_id

#             for entry in event["standings"]:
#                 driver_number = entry["driver_number"]

#                 stint = stint_ingestor.get_current_stint(
#                     driver_number=driver_number,
#                     lap_number=lap_number,
#                 )

#                 if stint is not None:
#                     writer.write_stint_state(
#                         session_id=session_id,
#                         driver_number=driver_number,
#                         stint=stint,
#                         lap_number=lap_number,
#                     )

#             writer.write_leaderboard(event)

#         for event in rc_events:
#             writer.write_race_control(event)

#         if events:
#             consumer.commit()

#         if rc_events:
#             race_control_consumer.commit()






# def main():
#     print("Starting Redis Writer Service")

#     redis_client = Redis(
#         host=REDIS_HOST,
#         port=REDIS_PORT,
#         decode_responses=True,
#     )

#     try:
#         redis_client.ping()
#         print("Redis connection OK")
#     except Exception as e:
#         print(f"[FATAL] Redis unavailable: {e}")
#         sys.exit(1)

#     stint_ingestor = StintIngestor(
#         base_url=OPENF1_BASE_URL
#     )
#     current_session_id = None

#     consumer = LeaderboardEventConsumer(
#         group_id="redis-writer"
#     )
#     race_control_consumer = RaceControlConsumer(
#         group_id="redis-writer-race-control"
#     )

#     writer = RedisWriter(redis_client)

#     running = True

#     def shutdown_handler(sig, frame):
#         nonlocal running
#         running = False

#     signal.signal(signal.SIGINT, shutdown_handler)
#     signal.signal(signal.SIGTERM, shutdown_handler)

#     while running:
#         try:
#             events = consumer.poll_batch(max_messages=200, timeout=1.0)

#             rc_events = race_control_consumer.poll_batch(max_messages=200, timeout=0.5)

#             for event in events:
#                 session_id = event["session_key"]
#                 lap_number = event["lap_number"]

#                 # Load stints once per session
#                 if current_session_id != session_id:
#                     print("GETTING STINTS 🛞🛞🛞")
#                     stint_ingestor.load_session_stints(session_id)
#                     current_session_id = session_id

#                 # Write stint state for active drivers
#                 for entry in event["standings"]:
#                     driver_number = entry["driver_number"]

#                     stint = stint_ingestor.get_current_stint(
#                         driver_number=driver_number,
#                         lap_number=lap_number,
#                     )

#                     if stint is not None:
#                         writer.write_stint_state(
#                             session_id=session_id,
#                             driver_number=driver_number,
#                             stint=stint,
#                             lap_number=lap_number,
#                         )

#                 writer.write_leaderboard(event)

#             for event in rc_events:
#                 writer.write_race_control(event)

#             if events:
#                 consumer.commit()

#             if rc_events:
#                 race_control_consumer.commit()

#         except Exception as e:
#             print(f"[ERROR] Redis writer failed: {e}", file=sys.stderr)

#     race_control_consumer.close()
#     consumer.close()
#     print("Redis Writer Service stopped cleanly.")


# if __name__ == "__main__":
#     main()


























import signal
import sys
import threading
import uuid
from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

from redis import Redis

from app.consumer_leaderboard import LeaderboardEventConsumer
from app.consumer_race_control import RaceControlConsumer
from app.redis_writer import RedisWriter
from app.replay_runner import ReplayRunner
from app.service_controller import ServiceMode
from app.settings import REDIS_HOST, REDIS_PORT, OPENF1_BASE_URL

from app.stint_ingestor import StintIngestor


# -------------------------
# Global Service State
# -------------------------

current_mode = ServiceMode.LIVE
live_thread = None
redis_client = None
writer = None


# -------------------------
# Live Loop
# -------------------------

def run_live_loop():
    global current_mode

    stint_ingestor = StintIngestor(base_url=OPENF1_BASE_URL)

    consumer = LeaderboardEventConsumer(group_id="redis-writer")
    race_control_consumer = RaceControlConsumer(
        group_id="redis-writer-race-control"
    )

    current_session_id = None

    try:
        while current_mode == ServiceMode.LIVE:
            # Check mode before polling to avoid processing messages after mode change
            if current_mode != ServiceMode.LIVE:
                break
                
            events = consumer.poll_batch(max_messages=200, timeout=1.0)
            
            # Check mode again after polling
            if current_mode != ServiceMode.LIVE:
                break
                
            rc_events = race_control_consumer.poll_batch(max_messages=200, timeout=0.5)

            # Final check before processing
            if current_mode != ServiceMode.LIVE:
                break

            for event in events:
                session_id = event["session_key"]
                lap_number = event["lap_number"]

                if current_session_id != session_id:
                    stint_ingestor.load_session_stints(session_id)
                    current_session_id = session_id

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
    finally:
        # Ensure consumers are always closed
        consumer.close()
        race_control_consumer.close()
        print("[INFO] Live loop consumers closed")


# -------------------------
# FastAPI Control Layer
# -------------------------

app = FastAPI()


class ReplayRequest(BaseModel):
    session_key: int
    start_time: str


@app.post("/start-replay")
def start_replay(req: ReplayRequest):
    global current_mode, live_thread

    # if current_mode != ServiceMode.LIVE:
    #     return {"error": "Service not in LIVE mode"}

    # Switch mode
    current_mode = ServiceMode.REPLAY

    # Wait for live loop to exit
    if live_thread and live_thread.is_alive():
        live_thread.join(timeout=5)

    # Convert timestamp
    dt = datetime.fromisoformat(req.start_time.replace("Z", "+00:00"))
    ts_ms = int(dt.timestamp() * 1000)

    simulation_id = str(uuid.uuid4())

    runner = ReplayRunner(
        session_key=req.session_key,
        start_timestamp_ms=ts_ms,
        simulation_id=simulation_id,
    )

    threading.Thread(target=runner.run, args=(writer, redis_client), daemon=True).start()

    return {"simulation_id": simulation_id}


# -------------------------
# Main Entry
# -------------------------

def main():
    global redis_client, writer, live_thread

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

    writer = RedisWriter(redis_client)

    live_thread = threading.Thread(target=run_live_loop, daemon=True)
    live_thread.start()

    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    main()
