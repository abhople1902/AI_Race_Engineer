# app/emitter/snapshot_builder.py
from datetime import datetime
from utils.config import Config

def build_snapshot(
    laps: list,
    intervals: list,
    pits: list,
    positions: list,
    race_events: list
) -> dict:
    snapshot = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "lap": get_current_leader_lap(laps),
        "leader": get_leader_driver_number(positions),
        "session_key": Config.SESSION_KEY,
        "drivers": {},
        "events": extract_flags(race_events)
    }

    # Organize driver-level data
    for interval in intervals:
        driver_number = str(interval["driver_number"])
        snapshot["drivers"][driver_number] = {
            "gap_to_leader": interval.get("gap_to_leader"),
            "interval": interval.get("interval")
        }

    for pos in positions:
        driver_number = str(pos["driver_number"])
        if driver_number not in snapshot["drivers"]:
            snapshot["drivers"][driver_number] = {}
        snapshot["drivers"][driver_number]["position"] = pos["position"]

    # Last lap times, tyre data, pit count from laps + pits
    for lap in laps:
        driver_number = str(lap["driver_number"])
        if driver_number not in snapshot["drivers"]:
            snapshot["drivers"][driver_number] = {}
        snapshot["drivers"][driver_number]["last_lap_time"] = lap.get("lap_duration")

    pit_counts = count_pits(pits)
    for driver_number, count in pit_counts.items():
        if driver_number not in snapshot["drivers"]:
            snapshot["drivers"][driver_number] = {}
        snapshot["drivers"][driver_number]["pit_count"] = count

    return snapshot

# --- Helpers ---

def get_current_leader_lap(laps):
    leader_laps = [lap for lap in laps if lap.get("position") == 1]
    if leader_laps:
        return leader_laps[-1]["lap_number"]
    return None

def get_leader_driver_number(positions):
    for pos in positions:
        if pos["position"] == 1:
            return str(pos["driver_number"])
    return None

def extract_flags(race_events):
    return [
        {
            "type": "FLAG",
            "message": e.get("message", ""),
            "sector": e.get("sector", None)
        }
        for e in race_events
        if e.get("category") == "Flag"
    ]

def count_pits(pits):
    pit_map = {}
    for p in pits:
        key = str(p["driver_number"])
        pit_map[key] = pit_map.get(key, 0) + 1
    return pit_map
