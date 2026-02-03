import requests
from typing import Dict, List, Optional


class StintIngestor:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.stints_by_driver: Dict[int, List[dict]] = {}
        self.session_loaded: Optional[int] = None

    def load_session_stints(self, session_key: int):
        if self.session_loaded == session_key:
            return

        url = f"{self.base_url}stints?session_key={session_key}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        by_driver: Dict[int, List[dict]] = {}

        for stint in data:
            driver = stint["driver_number"]
            by_driver.setdefault(driver, []).append(stint)

        for driver, stints in by_driver.items():
            stints.sort(key=lambda s: s["stint_number"])

        self.stints_by_driver = by_driver
        self.session_loaded = session_key

    def get_current_stint(
        self,
        driver_number: int,
        lap_number: int,
    ) -> Optional[dict]:
        stints = self.stints_by_driver.get(driver_number)
        if not stints:
            return None

        for stint in stints:
            if stint["lap_start"] <= lap_number <= stint["lap_end"]:
                return stint

        return None
