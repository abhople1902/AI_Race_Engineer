# app/leaderboard/builder.py

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .state import LeaderboardState
from .models import DriverSnapshot, LeaderboardEntry


EMIT_DEBOUNCE_SECONDS = 3.0
MIN_DRIVERS_TO_EMIT = 10


class LeaderboardBuilder:
    def __init__(self, state: LeaderboardState):
        self.state = state

    def process_event(self, event: Dict) -> Optional[Dict]:
        """
        Process one normalized interval event.
        Returns leaderboard payload or None.
        """
        session_key = event["session_key"]
        driver = event["driver_number"]
        lap = event["lap_number"]
        gap = event["gap_to_leader"]
        confidence = event["confidence"]
        event_time: datetime = event["event_time"]

        if self.state.session_key is None:
            self.state.session_key = session_key
        elif self.state.session_key != session_key:
            return None

        # --- Leader detection (sticky) ---
        if event.get("is_leader") is True:
            self.state.leader_driver_number = driver
            self.state.leader_lap = lap
            self.state.leader_last_seen_time = event_time

        # Bootstrap leader if missing
        if self.state.leader_driver_number is None:
            if gap == 0.0:
                self.state.leader_driver_number = driver
                self.state.leader_lap = lap
                self.state.leader_last_seen_time = event_time

        # --- Lap handling ---
        if self.state.current_lap is None:
            self.state.current_lap = lap
        elif self.state.leader_lap is not None and self.state.leader_lap > self.state.current_lap:
            self.state.clear_for_new_lap(self.state.leader_lap)

        # Accept driver only if within lap window
        if self.state.current_lap is not None:
            if lap < self.state.current_lap - 1:
                return None

        # For backmarkers
        if isinstance(gap, str):
            gap = float("inf")
        elif gap is None:
            gap = float("inf")

        # --- Update driver snapshot ---
        self.state.drivers[driver] = DriverSnapshot(
            driver_number=driver,
            gap_to_leader=gap,
            lap_number=lap,
            confidence=confidence,
            last_event_time=event_time,
        )

        # --- Decide emission ---
        if not self._should_emit(event_time):
            return None

        return self._emit_leaderboard(event_time)

    def _should_emit(self, now: datetime) -> bool:
        if self.state.leader_driver_number is None:
            return False

        if len(self.state.drivers) >= MIN_DRIVERS_TO_EMIT:
            return True

        if self.state.last_emitted_time is None:
            return True

        if (now - self.state.last_emitted_time).total_seconds() >= EMIT_DEBOUNCE_SECONDS:
            return True

        return False

    def _emit_leaderboard(self, event_time: datetime) -> Dict:
        ranked = sorted(
            self.state.drivers.values(),
            key=lambda d: d.gap_to_leader,
        )

        standings: List[LeaderboardEntry] = []
        for idx, d in enumerate(ranked):
            standings.append(
                LeaderboardEntry(
                    position=idx + 1,
                    driver_number=d.driver_number,
                    gap_to_leader=d.gap_to_leader,
                )
            )

        self.state.last_emitted_time = event_time

        return {
            "session_key": self.state.session_key,
            "lap_number": self.state.current_lap,
            "event_time": event_time,
            "leader_driver_number": self.state.leader_driver_number,
            "standings": [entry.__dict__ for entry in standings],
        }
