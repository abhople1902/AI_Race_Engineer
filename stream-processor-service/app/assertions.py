# interval_normalizer/assertions.py

from typing import Dict, Optional
from datetime import datetime

from interval_normalizer.models import SessionState
from interval_normalizer.config import LEADER_GAP_VALUE


# =========================
# Assertion Error
# =========================

class IntervalAssertionError(Exception):
    pass


# =========================
# Per-driver emission tracking (local, replay-safe)
# =========================

_last_event_time_per_driver: Dict[int, datetime] = {}
_last_lap_per_driver: Dict[int, int] = {}


# =========================
# Core Validation Function
# =========================

def validate_output(
    record: Dict,
    session_state: SessionState,
    strict: bool = True,
) -> None:
    """
    Validate a single emitted normalized record against domain invariants.

    If strict=True → raises IntervalAssertionError
    If strict=False → prints warnings only
    """

    def fail(msg: str):
        if strict:
            raise IntervalAssertionError(msg)
        else:
            print(f"[ASSERTION WARNING] {msg}")

    driver = record["driver_number"]
    event_time = record["event_time"]
    gap = record["gap_to_leader"]
    confidence = record["confidence"]
    lap = record["lap_number"]
    is_leader = record["is_leader"]
    leader_driver = record["leader_driver_number"]

    # =========================
    # Leader invariants
    # =========================

    if is_leader:
        if gap != LEADER_GAP_VALUE:
            fail(
                f"Leader gap must be {LEADER_GAP_VALUE}, "
                f"got {gap} for driver {driver}"
            )

        if leader_driver != driver:
            fail(
                f"is_leader=True but leader_driver_number={leader_driver} "
                f"for driver {driver}"
            )

    # Only one leader allowed
    if leader_driver is None:
        fail("leader_driver_number must never be None in output")

    # =========================
    # Gap invariants
    # =========================

    if gap is None:
        fail("gap_to_leader must never be None in emitted output")

    if gap < 0:
        fail(
            f"gap_to_leader must be >= 0, got {gap} for driver {driver}"
        )

    if confidence == "INVALID":
        fail(
            f"INVALID confidence must never be emitted (driver {driver})"
        )

    # =========================
    # Temporal invariants
    # =========================

    last_time = _last_event_time_per_driver.get(driver)
    if last_time is not None:
        if event_time < last_time:
            fail(
                f"event_time regression for driver {driver}: "
                f"{event_time} < {last_time}"
            )

    _last_event_time_per_driver[driver] = event_time

    # =========================
    # Lap invariants
    # =========================

    if lap is None:
        fail(f"lap_number must not be None for driver {driver}")

    last_lap = _last_lap_per_driver.get(driver)
    if last_lap is not None:
        if lap < last_lap:
            fail(
                f"lap_number decreased for driver {driver}: "
                f"{lap} < {last_lap}"
            )

        if lap - last_lap > 1:
            print(
                f"[ASSERTION WARNING] Large lap jump for driver {driver}: "
                f"{last_lap} → {lap}"
            )

    _last_lap_per_driver[driver] = lap

    # =========================
    # Pit invariants (state-based)
    # =========================

    driver_state = session_state.drivers.get(driver)
    if driver_state:
        if driver_state.in_pit:
            fail(
                f"Emission occurred while driver {driver} is in pit"
            )

    # =========================
    # Session consistency
    # =========================

    if driver not in session_state.active_driver_set:
        fail(
            f"Emitted driver {driver} not in active_driver_set"
        )
