# interval_normalizer/models.py

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Set


# =========================
# Enums
# =========================

class GapConfidence(Enum):
    CONFIRMED = "CONFIRMED"
    ESTIMATED = "ESTIMATED"
    INVALID = "INVALID"


# =========================
# Driver State
# =========================

@dataclass
class DriverState:
    """
    Holds all mutable state for a single driver within a session.
    This state must be fully reconstructible via Kafka replay.
    """

    # Identity
    driver_number: int

    # Event-time tracking
    last_event_time: Optional[datetime] = None
    current_lap: Optional[int] = None

    # Gap tracking
    last_valid_gap: Optional[float] = None
    gap_confidence: GapConfidence = GapConfidence.INVALID

    # Pit tracking
    in_pit: bool = False
    pit_entry_time: Optional[datetime] = None

    # Freshness tracking
    staleness_ticks: int = 0

    def invalidate_gap(self) -> None:
        """
        Invalidate the current gap without destroying state.
        """
        self.last_valid_gap = None
        self.gap_confidence = GapConfidence.INVALID

    def confirm_gap(self, gap: float) -> None:
        """
        Accept a new confirmed gap.
        """
        self.last_valid_gap = gap
        self.gap_confidence = GapConfidence.CONFIRMED
        self.staleness_ticks = 0

    def estimate_gap(self) -> None:
        """
        Mark the current gap as estimated (propagated).
        """
        if self.last_valid_gap is not None:
            self.gap_confidence = GapConfidence.ESTIMATED


# =========================
# Session State
# =========================

@dataclass
class SessionState:
    """
    Holds all state scoped to a single session.
    """

    session_key: str

    # Driver states
    drivers: Dict[int, DriverState] = field(default_factory=dict)

    # Leader tracking
    current_leader_driver: Optional[int] = None
    leader_event_time: Optional[datetime] = None

    # Session-wide context
    current_lap_number: Optional[int] = None
    active_driver_set: Set[int] = field(default_factory=set)

    # Emission coordination
    last_emission_time: Optional[datetime] = None

    def get_or_create_driver(self, driver_number: int) -> DriverState:
        """
        Fetch existing DriverState or create a new one lazily.
        """
        if driver_number not in self.drivers:
            self.drivers[driver_number] = DriverState(
                driver_number=driver_number
            )
        self.active_driver_set.add(driver_number)
        return self.drivers[driver_number]

    def reset_leader(self, driver_number: int, event_time: datetime) -> None:
        """
        Set a new leader and record leader event-time.
        """
        self.current_leader_driver = driver_number
        self.leader_event_time = event_time

    def invalidate_all_non_leader_gaps(self) -> None:
        """
        Invalidate gaps for all drivers except the leader.
        Used on leader change.
        """
        for drv_num, state in self.drivers.items():
            if drv_num != self.current_leader_driver:
                state.invalidate_gap()
