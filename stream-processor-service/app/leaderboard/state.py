# app/leaderboard/state.py

from typing import Dict, Optional
from datetime import datetime
from .models import DriverSnapshot


class LeaderboardState:
    def __init__(self, session_key: Optional[int] = None):
        self.session_key = session_key

        self.current_lap: Optional[int] = None

        self.leader_driver_number: Optional[int] = None
        self.leader_lap: Optional[int] = None
        self.leader_last_seen_time: Optional[datetime] = None

        self.drivers: Dict[int, DriverSnapshot] = {}

        self.last_emitted_time: Optional[datetime] = None

    def clear_for_new_lap(self, new_lap: int):
        """
        Advance lap context but retain leader snapshot.
        """
        self.current_lap = new_lap

        if self.leader_driver_number is not None:
            leader_snapshot = self.drivers.get(self.leader_driver_number)
            self.drivers.clear()
            if leader_snapshot:
                self.drivers[self.leader_driver_number] = leader_snapshot
        else:
            self.drivers.clear()
