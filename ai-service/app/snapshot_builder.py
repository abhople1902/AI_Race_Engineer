from statistics import median
from typing import Any, Dict, List

import requests

CLEAN_AIR_INTERVAL_THRESHOLD = 1.2
LEADERBOARD_WINDOW = 2


class AISnapshotBuilder:
    def __init__(self, redis_writer_base_url: str, timeout_sec: float = 5.0):
        self.redis_writer_base_url = redis_writer_base_url.rstrip("/")
        self.timeout_sec = timeout_sec

    def build_snapshot(
        self,
        session_id: int,
        driver_numbers: List[int],
        simulation_id: str | None = None,
    ) -> Dict[str, Any]:
        payload = self._fetch_leaderboard_payload(session_id, simulation_id)
        session_meta = self._get_session_meta(payload)
        leaderboard = self._get_full_leaderboard(payload)

        drivers_block = [
            self._build_driver_block(
                driver_number=driver_number,
                session_lap=session_meta["lap"],
                payload=payload,
            )
            for driver_number in driver_numbers
        ]

        leaderboard_context = self._build_leaderboard_context(
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

    def _fetch_leaderboard_payload(
        self,
        session_id: int,
        simulation_id: str | None,
    ) -> Dict[str, Any]:
        params = {"session_key": str(session_id)}
        if simulation_id:
            params["simulation_id"] = simulation_id

        url = f"{self.redis_writer_base_url}/leaderboard"
        try:
            response = requests.get(url, params=params, timeout=self.timeout_sec)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            raise RuntimeError(f"Failed to fetch leaderboard from redis-writer: {exc}") from exc

        if not isinstance(data, dict) or "leaderboard" not in data:
            raise RuntimeError("Invalid leaderboard payload from redis-writer")

        return data

    def _get_session_meta(self, payload: Dict[str, Any]) -> Dict[str, int]:
        leaderboard = payload.get("leaderboard", [])
        lap_raw = payload.get("lap")
        if lap_raw in (None, "") and leaderboard:
            lap_raw = leaderboard[0].get("lap_number", 0)

        lap = self._to_int(lap_raw, default=0)
        cars_running = self._to_int(payload.get("cars_running"), default=len(leaderboard))

        return {
            "lap": lap,
            "cars_running": cars_running,
        }

    def _build_driver_block(
        self,
        driver_number: int,
        session_lap: int,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        entry = self._find_driver_entry(payload, driver_number)
        if not entry:
            raise RuntimeError(f"Driver {driver_number} missing")

        stint = entry.get("stint") or {}
        interval_raw = entry.get("interval_to_ahead", entry.get("interval"))
        interval = self._to_float(interval_raw, default=None)

        last_pit_lap = self._to_int(stint.get("last_pit_lap"), default=0)
        stint_lap_start = self._to_int(stint.get("stint_lap_start"), default=session_lap)
        tyre_age_at_start = self._to_int(stint.get("tyre_age_at_start"), default=0)
        tyre_age_now = (session_lap - stint_lap_start) + tyre_age_at_start

        return {
            "driver_number": driver_number,
            "position": self._to_int(entry.get("position"), default=0),
            "gap_to_leader": self._to_float(entry.get("gap_to_leader"), default=0.0),
            "interval_to_ahead": interval,
            "stint": {
                "stint_number": self._to_int(stint.get("stint_number"), default=0),
                "compound": stint.get("compound", entry.get("tyre_compound", "UNKNOWN")),
                "stint_lap_start": stint_lap_start,
                "last_pit_lap": last_pit_lap,
                "tyre_age_now": tyre_age_now,
            },
            "context": {
                "laps_since_pit": session_lap - last_pit_lap,
                "is_in_clean_air": (
                    interval == 0.0
                    or (interval is not None and interval >= CLEAN_AIR_INTERVAL_THRESHOLD)
                ),
            },
        }

    def _find_driver_entry(
        self,
        payload: Dict[str, Any],
        driver_number: int,
    ) -> Dict[str, Any] | None:
        for entry in payload.get("leaderboard", []):
            if self._to_int(entry.get("driver_number"), default=-1) == driver_number:
                return entry
        return None

    def _get_full_leaderboard(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        leaderboard = []
        for entry in payload.get("leaderboard", []):
            leaderboard.append(
                {
                    "driver_number": self._to_int(entry.get("driver_number"), default=0),
                    "position": self._to_int(entry.get("position"), default=0),
                    "gap_to_leader": self._to_float(entry.get("gap_to_leader"), default=0.0),
                }
            )

        leaderboard.sort(key=lambda item: item["position"])
        return leaderboard

    def _build_leaderboard_context(
        self,
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

        gaps = [entry["gap_to_leader"] for entry in leaderboard]
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

    @staticmethod
    def _to_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_float(value: Any, default: float | None) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
