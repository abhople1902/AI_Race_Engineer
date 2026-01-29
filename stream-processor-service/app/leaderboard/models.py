# app/leaderboard/models.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class DriverSnapshot:
    driver_number: int
    gap_to_leader: float
    lap_number: int
    confidence: str
    last_event_time: datetime


@dataclass
class LeaderboardEntry:
    position: int
    driver_number: int
    gap_to_leader: float
