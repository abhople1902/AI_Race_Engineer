import requests
from utils.config import Config
from datetime import datetime, timedelta

class OpenF1Client:
    def __init__(self):
        self.base_url = Config.OPENF1_BASE_URL
        self.session_key = Config.SESSION_KEY
        self.polling_step = timedelta(seconds=Config.POLL_INTERVAL_SEC)

        # self.timestamp_lower = self._get_first_timestamp()
        self.timestamp_lower = datetime.fromisoformat("2025-11-09T16:55:00.022000+00:00")

        self.timestamp_upper = self.timestamp_lower + self.polling_step


    def _get_first_timestamp(self):
        endpoints = [
            ("intervals", "date"),
            ("laps", "date_start"),
            ("pit", "date"),
            ("race_control", "date"),
            ("position", "date"),
        ]
        earliest = None
        for endpoint, field in endpoints:
            url = f"{self.base_url}/{endpoint}?session_key={self.session_key}"
            print(f"For {endpoint} endpoint, url 💠 is: {url}")
            try:
                resp = requests.get(url, timeout=5)
                resp.raise_for_status()
                data = resp.json()
                if not data:
                    continue

                for record in data:
                    ts_str = record.get(field)
                    if ts_str:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        print(f"For {endpoint} endpoint, timestamp ❇️ is: {ts}")
                        if not earliest or ts < earliest:
                            earliest = ts
                        break
            except Exception as e:
                print(f"[WARN] Failed to probe {endpoint}: {e}")
        if earliest:
            print(f"🔰 Auto-starting from: {earliest.isoformat()}")
            return earliest
        else:
            raise ValueError("Could not determine start timestamp from any endpoint.")

    def _advance_time_window(self):
        self.timestamp_lower = self.timestamp_upper
        self.timestamp_upper = self.timestamp_lower + self.polling_step

    def _format_time_range_query(self, param_name: str) -> str:
        lower = self.timestamp_lower.isoformat()
        upper = self.timestamp_upper.isoformat()
        return f"&{param_name}>={lower}&{param_name}<{upper}"




    def get_intervals(self):
        url = f"{self.base_url}/intervals?session_key={self.session_key}"
        url += self._format_time_range_query("date")
        print(f"Intervals url 💠 is: {url}")
        return self._fetch(url, "intervals")

    def get_positions(self):
        url = f"{self.base_url}/position?session_key={self.session_key}"
        url += self._format_time_range_query("date")
        return self._fetch(url, "positions")

    def get_laps(self):
        url = f"{self.base_url}/laps?session_key={self.session_key}"
        url += self._format_time_range_query("date_start")
        return self._fetch(url, "laps")

    def get_pit_data(self):
        url = f"{self.base_url}/pit?session_key={self.session_key}"
        url += self._format_time_range_query("date")
        print(f"Pit data url 💠 is: {url}")
        return self._fetch(url, "pit data")

    def get_race_control(self):
        url = f"{self.base_url}/race_control?session_key={self.session_key}"
        url += self._format_time_range_query("date")
        return self._fetch(url, "race control")




    def _fetch(self, url, label):
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[ERROR] Failed to fetch {label}: {e}")
            return []

    def advance(self):
        """Advance to next polling window — call once per loop."""
        self._advance_time_window()
