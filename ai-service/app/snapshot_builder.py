from typing import List, Dict, Any
from statistics import median
from redis import Redis

CLEAN_AIR_INTERVAL_THRESHOLD = 1.2
LEADERBOARD_WINDOW = 2  # ±2 positions


class AISnapshotBuilder:
    def __init__(self, redis: Redis):
        self.redis = redis

    # -----------------------------
    # Public API
    # -----------------------------
    def build_snapshot(
        self,
        session_id: int,
        driver_numbers: List[int],
    ) -> Dict[str, Any]:
        session_meta = self._get_session_meta(session_id)
        leaderboard = self._get_full_leaderboard(session_id)

        drivers_block = [
            self._build_driver_block(
                session_id=session_id,
                driver_number=driver_number,
                session_lap=session_meta["lap"],
            )
            for driver_number in driver_numbers
        ]

        leaderboard_context = self._build_leaderboard_context(
            session_id=session_id,
            leaderboard=leaderboard,
            focus_drivers=driver_numbers,
        )

        return {
            "session": {
                "session_key": session_id,
                "lap": session_meta["lap"],
                "cars_running": session_meta["cars_running"],
            },
            "drivers": drivers_block,
            "leaderboard_context": leaderboard_context,
        }

    # -----------------------------
    # Session
    # -----------------------------
    def _get_session_meta(self, session_id: int) -> Dict[str, int]:
        meta = self.redis.hgetall(f"session:{session_id}:meta")
        if not meta:
            raise RuntimeError("Session meta missing")

        return {
            "lap": int(meta["lap"]),
            "cars_running": int(meta["cars_running"]),
        }

    # -----------------------------
    # Driver block
    # -----------------------------
    def _build_driver_block(
        self,
        session_id: int,
        driver_number: int,
        session_lap: int,
    ) -> Dict[str, Any]:
        driver = self.redis.hgetall(
            f"session:{session_id}:driver:{driver_number}"
        )
        stint = self.redis.hgetall(
            f"session:{session_id}:driver:{driver_number}:stint"
        )

        if not driver:
            raise RuntimeError(f"Driver {driver_number} missing")
        if not stint:
            raise RuntimeError(f"Stint missing for driver {driver_number}")

        interval = driver.get("interval_to_ahead")
        interval = float(interval) if interval not in (None, "") else None

        last_pit_lap = int(stint["last_pit_lap"])
        laps_since_pit = session_lap - last_pit_lap

        tyre_age_now = (
            (session_lap - int(stint["stint_lap_start"]))
            + int(stint["tyre_age_at_start"])
        )

        return {
            "driver_number": int(driver_number),
            "position": int(driver["position"]),
            "gap_to_leader": float(driver["gap_to_leader"]),
            "interval_to_ahead": interval,
            "stint": {
                "stint_number": int(stint["stint_number"]),
                "compound": stint["compound"],
                "stint_lap_start": int(stint["stint_lap_start"]),
                "last_pit_lap": last_pit_lap,
                "tyre_age_now": tyre_age_now,
            },
            "context": {
                "laps_since_pit": laps_since_pit,
                "is_in_clean_air": (
                    interval == 0.0
                    or interval >= CLEAN_AIR_INTERVAL_THRESHOLD
                ),
            },
        }

    # -----------------------------
    # Leaderboard context
    # -----------------------------
    def _get_full_leaderboard(
        self,
        session_id: int,
    ) -> List[Dict[str, Any]]:
        raw = self.redis.zrange(
            f"session:{session_id}:leaderboard",
            0,
            -1,
            withscores=True,
        )

        leaderboard = []
        for driver_str, position in raw:
            driver_key = f"session:{session_id}:driver:{driver_str}"
            driver = self.redis.hgetall(driver_key)
            if not driver:
                continue

            leaderboard.append({
                "driver_number": int(driver_str),
                "position": int(position),
                "gap_to_leader": float(driver["gap_to_leader"]),
            })

        leaderboard.sort(key=lambda x: x["position"])
        return leaderboard

    def _build_leaderboard_context(
        self,
        session_id: int,
        leaderboard: List[Dict[str, Any]],
        focus_drivers: List[int],
    ) -> Dict[str, Any]:
        positions = {
            entry["driver_number"]: entry["position"]
            for entry in leaderboard
        }

        selected = set()

        for driver in focus_drivers:
            pos = positions.get(driver)
            if pos is None:
                continue

            for entry in leaderboard:
                if abs(entry["position"] - pos) <= LEADERBOARD_WINDOW:
                    selected.add(entry["driver_number"])

        window_entries = [
            entry
            for entry in leaderboard
            if entry["driver_number"] in selected
        ]

        gaps = [e["gap_to_leader"] for e in leaderboard]
        median_gap = median(gaps) if gaps else 0.0

        if median_gap < 8:
            density = "HIGH"
        elif median_gap < 15:
            density = "MEDIUM"
        else:
            density = "LOW"

        return {
            "window": {
                "around_drivers": focus_drivers,
                "positions": window_entries,
            },
            "field_summary": {
                "cars_running": len(leaderboard),
                "median_gap": round(median_gap, 2),
                "train_density": density,
            },
        }
