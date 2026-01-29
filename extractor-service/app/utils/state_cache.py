# app/utils/state_cache.py
from typing import Any


class StateCache:
    def __init__(self):
        self.last_leader_lap = None
        self.last_pit_ids = set()
        self.last_event_ids = set()

    def has_leader_lap_changed(self, current_lap: int) -> bool:
        if self.last_leader_lap != current_lap:
            self.last_leader_lap = current_lap
            return True
        return False

    def new_pit_detected(self, pit_data: list) -> bool:
        current_ids = {f"{p['driver_number']}_{p['lap_number']}" for p in pit_data}
        print(f"Pit data current_ids:🏁🏁🏁 {current_ids}")
        print(f"Pit data last_pit_ids:🏁🏁🏁 {self.last_pit_ids}")
        new = not current_ids.issubset(self.last_pit_ids)
        print(f"Pit data new:🏁🏁🏁 {new}")
        self.last_pit_ids = current_ids
        return new

    def new_event_detected(self, race_control_data: list) -> bool:
        current_ids = {e['message'] + e['date'] for e in race_control_data}
        # print(f"Race control current_ids:🏁🏁🏁 {current_ids}")
        # print(f"Race control last_event_ids:🏁🏁🏁 {self.last_event_ids}")
        new = not current_ids.issubset(self.last_event_ids)
        self.last_event_ids = current_ids
        return new
