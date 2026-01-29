# interval_normalizer/ordering.py

from datetime import datetime, timedelta
from typing import Tuple

from app.interval_normalizer.config import ALLOWED_LATENESS_SECONDS
from app.interval_normalizer.models import DriverState, SessionState


# =========================
# Ordering Decisions
# =========================

class OrderingDecision:
    ACCEPT = "ACCEPT"
    ACCEPT_LATE = "ACCEPT_LATE"
    REJECT = "REJECT"


# =========================
# Per-Driver Event-Time Ordering
# =========================

def evaluate_driver_event_time(
    driver_state: DriverState,
    event_time: datetime,
) -> str:
    """
    Decide whether an incoming event should be accepted, accepted as late,
    or rejected based on per-driver event-time ordering rules.
    """

    # First event for this driver
    if driver_state.last_event_time is None:
        return OrderingDecision.ACCEPT

    last_time = driver_state.last_event_time
    allowed_lateness = timedelta(seconds=ALLOWED_LATENESS_SECONDS)

    # Normal in-order event
    if event_time >= last_time:
        return OrderingDecision.ACCEPT

    # Late but within tolerance
    if last_time - allowed_lateness <= event_time < last_time:
        return OrderingDecision.ACCEPT_LATE

    # Too late → reject
    return OrderingDecision.REJECT


# =========================
# Leader Ordering Rules
# =========================

def evaluate_leader_event_time(
    session_state: SessionState,
    event_time: datetime,
) -> bool:
    """
    Leader events are accepted only if they are not older than the last
    confirmed leader event-time.
    """

    if session_state.leader_event_time is None:
        return True

    return event_time >= session_state.leader_event_time


# =========================
# Lap Boundary Override
# =========================

def is_lap_advance(
    driver_state: DriverState,
    lap_number: int,
) -> bool:
    """
    Detects a lap advancement for a driver.
    Lap advancement overrides minor event-time regressions.
    """

    if driver_state.current_lap is None:
        return True

    return lap_number > driver_state.current_lap


# =========================
# Ordering Application Helper
# =========================

def should_update_driver_state(
    driver_state: DriverState,
    event_time: datetime,
    lap_number: int,
) -> Tuple[bool, str]:
    """
    High-level helper that determines whether driver state should be updated,
    taking into account both event-time ordering and lap boundaries.

    Returns:
        (should_update, ordering_decision)
    """

    # Lap advancement always allows update
    if lap_number is not None and is_lap_advance(driver_state, lap_number):
        return True, OrderingDecision.ACCEPT

    decision = evaluate_driver_event_time(driver_state, event_time)

    if decision == OrderingDecision.REJECT:
        return False, decision

    return True, decision
