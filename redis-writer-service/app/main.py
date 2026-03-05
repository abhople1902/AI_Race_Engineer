# import signal
# import sys
# import threading
# import uuid
# from datetime import datetime

# from fastapi import FastAPI
# from pydantic import BaseModel
# import uvicorn

# from redis import Redis

# from app.consumer_leaderboard import LeaderboardEventConsumer
# from app.consumer_race_control import RaceControlConsumer
# from app.redis_writer import RedisWriter
# from app.replay_runner import ReplayRunner
# from app.service_controller import ServiceMode
# from app.settings import REDIS_HOST, REDIS_PORT, OPENF1_BASE_URL

# from app.stint_ingestor import StintIngestor


# # -------------------------
# # Global Service State
# # -------------------------

# current_mode = ServiceMode.LIVE
# live_thread = None
# redis_client = None
# writer = None


# # -------------------------
# # Live Loop
# # -------------------------

# def run_live_loop():
#     global current_mode

#     stint_ingestor = StintIngestor(base_url=OPENF1_BASE_URL)

#     consumer = LeaderboardEventConsumer(group_id="redis-writer")
#     race_control_consumer = RaceControlConsumer(
#         group_id="redis-writer-race-control"
#     )

#     current_session_id = None

#     try:
#         while current_mode == ServiceMode.LIVE:
#             # Check mode before polling to avoid processing messages after mode change
#             if current_mode != ServiceMode.LIVE:
#                 break
                
#             events = consumer.poll_batch(max_messages=200, timeout=1.0)
            
#             # Check mode again after polling
#             if current_mode != ServiceMode.LIVE:
#                 break
                
#             rc_events = race_control_consumer.poll_batch(max_messages=200, timeout=0.5)

#             # Final check before processing
#             if current_mode != ServiceMode.LIVE:
#                 break

#             for event in events:
#                 session_id = event["session_key"]
#                 lap_number = event["lap_number"]

#                 if current_session_id != session_id:
#                     stint_ingestor.load_session_stints(session_id)
#                     current_session_id = session_id

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
#     finally:
#         # Ensure consumers are always closed
#         consumer.close()
#         race_control_consumer.close()
#         print("[INFO] Live loop consumers closed")


# # -------------------------
# # FastAPI Control Layer
# # -------------------------

# app = FastAPI()

# @app.get("/")
# def health():
#     return {"status": "Redis Writer Service running OK"}


# class ReplayRequest(BaseModel):
#     session_key: int
#     start_time: str


# @app.post("/start-replay")
# def start_replay(req: ReplayRequest):
#     global current_mode, live_thread

#     # if current_mode != ServiceMode.LIVE:
#     #     return {"error": "Service not in LIVE mode"}

#     # Switch mode
#     current_mode = ServiceMode.REPLAY

#     # Wait for live loop to exit
#     if live_thread and live_thread.is_alive():
#         live_thread.join(timeout=5)

#     # Convert timestamp
#     dt = datetime.fromisoformat(req.start_time.replace("Z", "+00:00"))
#     ts_ms = int(dt.timestamp() * 1000)

#     simulation_id = str(uuid.uuid4())

#     runner = ReplayRunner(
#         session_key=req.session_key,
#         start_timestamp_ms=ts_ms,
#         simulation_id=simulation_id,
#     )

#     threading.Thread(target=runner.run, args=(writer, redis_client), daemon=True).start()

#     return {"simulation_id": simulation_id}


# # -------------------------
# # Main Entry
# # -------------------------

# def main():
#     global redis_client, writer, live_thread

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

#     writer = RedisWriter(redis_client)

#     live_thread = threading.Thread(target=run_live_loop, daemon=True)
#     live_thread.start()

#     uvicorn.run(app, host="0.0.0.0", port=8001)


# if __name__ == "__main__":
#     main()



























import json
import sys
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

from redis import Redis

from app.redis_writer import RedisWriter
from app.replay_runner import ReplayRunner
from app.settings import REDIS_HOST, REDIS_PORT


app = FastAPI()
active_runners: dict[str, ReplayRunner] = {}
active_runners_lock = threading.Lock()

DRIVER_CODE_MAP = {
    "10": "GAS",
    "43": "COL",
    "14": "ALO",
    "18": "STR",
    "16": "LEC",
    "44": "HAM",
    "31": "OCO",
    "87": "BEA",
    "5": "BOR",
    "27": "HUL",
    "4": "NOR",
    "81": "PIA",
    "12": "ANT",
    "63": "RUS",
    "6": "HAD",
    "30": "LAW",
    "22": "TSU",
    "1": "VER",
    "23": "ALB",
    "55": "SAI",
}

TEAM_MAP = {
    "10": "Alpine",
    "43": "Alpine",
    "14": "Aston Martin",
    "18": "Aston Martin",
    "16": "Ferrari",
    "44": "Ferrari",
    "31": "Haas",
    "87": "Haas",
    "5": "Kick Sauber",
    "27": "Kick Sauber",
    "4": "McLaren",
    "81": "McLaren",
    "12": "Mercedes",
    "63": "Mercedes",
    "6": "Racing Bulls",
    "30": "Racing Bulls",
    "22": "Red Bull",
    "1": "Red Bull",
    "23": "Williams",
    "55": "Williams",
}

VALID_COMPOUNDS = {"SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET", "UNKNOWN"}


# -------------------------
# Redis Init (No Globals Beyond This)
# -------------------------

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



@app.get("/")
def health():
    return {"status": "Redis Writer Service running OK"}


class ReplayRequest(BaseModel):
    session_key: int
    start_time: str


class EndReplayRequest(BaseModel):
    simulation_id: str


def _prefix(session_key: str, simulation_id: str | None) -> str:
    if simulation_id:
        return f"sim:{simulation_id}:session:{session_key}"
    return f"live:session:{session_key}"


def _status_key(session_key: str, simulation_id: str) -> str:
    return f"sim:{simulation_id}:session:{session_key}:replay_status"


@app.get("/leaderboard")
def get_leaderboard(session_key: str, simulation_id: str | None = None) -> dict[str, Any]:
    prefix = _prefix(session_key, simulation_id)
    meta_key = f"{prefix}:meta"
    leaderboard_key = f"{prefix}:leaderboard"

    meta = redis_client.hgetall(meta_key)
    timestamp = meta.get("last_event_ts")
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    ordered = redis_client.zrange(leaderboard_key, 0, -1, withscores=True)

    leaderboard = []
    prev_gap = 0.0

    for driver_raw, position_raw in ordered:
        driver = str(driver_raw)
        position = int(position_raw)

        driver_key = f"{prefix}:driver:{driver}"
        data = redis_client.hgetall(driver_key)
        if not data or data.get("status") != "RUNNING":
            continue

        try:
            gap = float(data.get("gap_to_leader", 0.0))
        except (TypeError, ValueError):
            gap = 0.0
        try:
            interval_to_ahead = float(data.get("interval_to_ahead", 0.0))
        except (TypeError, ValueError):
            interval_to_ahead = 0.0
        try:
            lap_number = int(data.get("lap_number", meta.get("lap", 0)))
        except (TypeError, ValueError):
            lap_number = 0

        stint_key = f"{prefix}:driver:{driver}:stint"
        stint = redis_client.hgetall(stint_key)
        raw_compound = str(stint.get("compound", "UNKNOWN")).upper() if stint else "UNKNOWN"
        tyre_compound = raw_compound if raw_compound in VALID_COMPOUNDS else "UNKNOWN"

        stint_payload = None
        if stint:
            try:
                stint_payload = {
                    "stint_number": int(stint.get("stint_number", 0)),
                    "compound": stint.get("compound", "UNKNOWN"),
                    "stint_lap_start": int(stint.get("stint_lap_start", 0)),
                    "last_pit_lap": int(stint.get("last_pit_lap", 0)),
                    "tyre_age_at_start": int(stint.get("tyre_age_at_start", 0)),
                }
            except (TypeError, ValueError):
                stint_payload = None

        interval = 0.0 if position == 1 else round(gap - prev_gap, 3)
        prev_gap = gap

        leaderboard.append(
            {
                "position": position,
                "driver_number": driver,
                "driver_code": DRIVER_CODE_MAP.get(driver, driver),
                "team": TEAM_MAP.get(driver, "Unknown"),
                "gap_to_leader": gap,
                "interval": interval,
                "interval_to_ahead": interval_to_ahead,
                "lap_number": lap_number,
                "tyre_compound": tyre_compound,
                "stint": stint_payload,
            }
        )

    try:
        lap = int(meta.get("lap", 0))
    except (TypeError, ValueError):
        lap = 0
    try:
        cars_running = int(meta.get("cars_running", len(leaderboard)))
    except (TypeError, ValueError):
        cars_running = len(leaderboard)

    response = {
        "session_key": str(session_key),
        "timestamp": timestamp,
        "lap": lap,
        "cars_running": cars_running,
        "leader_driver_number": meta.get("leader_driver_number"),
        "leaderboard": leaderboard,
    }
    if simulation_id:
        status = redis_client.hget(_status_key(str(session_key), simulation_id), "status")
        if status:
            response["replay_status"] = status
    return response


@app.get("/race-control")
def get_race_control(session_key: str, simulation_id: str | None = None) -> list[dict[str, Any]]:
    key = f"{_prefix(session_key, simulation_id)}:race_control"
    messages = redis_client.lrange(key, 0, 49)

    parsed: list[dict[str, Any]] = []
    for msg in messages:
        try:
            parsed.append(json.loads(msg))
        except Exception:
            continue
    return parsed


@app.post("/start-replay")
def start_replay(req: ReplayRequest):

    dt = datetime.fromisoformat(req.start_time.replace("Z", "+00:00"))
    ts_ms = int(dt.timestamp() * 1000)

    simulation_id = str(uuid.uuid4())

    runner = ReplayRunner(
        session_key=req.session_key,
        start_timestamp_ms=ts_ms,
        simulation_id=simulation_id,
    )

    with active_runners_lock:
        active_runners[simulation_id] = runner

    def _run_and_cleanup():
        try:
            runner.run(writer, redis_client)
        finally:
            with active_runners_lock:
                active_runners.pop(simulation_id, None)

    # Run in background thread (non-blocking API)
    threading.Thread(
        target=_run_and_cleanup,
        daemon=True
    ).start()

    return {"simulation_id": simulation_id}


@app.post("/end-replay")
def end_replay(req: EndReplayRequest):
    with active_runners_lock:
        runner = active_runners.get(req.simulation_id)

    if runner is None:
        return {"simulation_id": req.simulation_id, "status": "NOT_RUNNING"}

    runner.request_stop()
    return {"simulation_id": req.simulation_id, "status": "STOP_REQUESTED"}


@app.get("/replay-status")
def replay_status(session_key: str, simulation_id: str):
    key = _status_key(session_key, simulation_id)
    payload = redis_client.hgetall(key)

    if payload:
        return {
            "simulation_id": simulation_id,
            "session_key": session_key,
            "status": payload.get("status", "UNKNOWN"),
            "updated_at": payload.get("updated_at"),
            "detail": payload.get("detail"),
        }

    with active_runners_lock:
        is_running = simulation_id in active_runners

    return {
        "simulation_id": simulation_id,
        "session_key": session_key,
        "status": "RUNNING" if is_running else "UNKNOWN",
        "updated_at": None,
        "detail": None,
    }


# -------------------------
# Entry
# -------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
