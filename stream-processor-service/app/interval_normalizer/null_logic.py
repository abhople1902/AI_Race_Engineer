# interval_normalizer/null_logic.py

from datetime import datetime, timedelta
from typing import Optional, Tuple

from app.interval_normalizer.config import (
    MAX_STALENESS_TICKS,
    POST_PIT_STABILIZATION_SECONDS,
    GapSource,
    LEADER_GAP_VALUE,
)
from app.interval_normalizer.models import DriverState, SessionState, GapConfidence


# =========================
# Resolution Result
# =========================

class ResolutionResult:
    """
    Result of resolving a raw interval.
    """
    def __init__(
        self,
        gap: Optional[float],
        confidence: GapConfidence,
        source: Optional[GapSource],
        should_emit: bool,
    ):
        self.gap = gap
        self.confidence = confidence
        self.source = source
        self.should_emit = should_emit


# =========================
# Helpers
# =========================

def _is_post_pit_unstable(
    driver_state: DriverState,
    event_time: datetime,
) -> bool:
    if not driver_state.pit_entry_time:
        return False
    return (
        not driver_state.in_pit
        and event_time - driver_state.pit_entry_time
        < timedelta(seconds=POST_PIT_STABILIZATION_SECONDS)
    )


# =========================
# Core Resolution Logic
# =========================

def resolve_interval(
    *,
    session_state: SessionState,
    driver_state: DriverState,
    raw_interval: Optional[float],
    event_time: datetime,
    lap_number: Optional[int],
) -> ResolutionResult:
    """
    Resolve a raw interval (which may be null) into a normalized gap decision.

    Returns a ResolutionResult indicating:
    - resolved gap (or None)
    - confidence
    - gap source (RAW / PROPAGATED)
    - whether an emission should occur
    """

    driver_num = driver_state.driver_number
    leader = session_state.current_leader_driver

    # =========================
    # Case A — Leader
    # =========================
    if driver_num == leader:
        driver_state.confirm_gap(LEADER_GAP_VALUE)
        return ResolutionResult(
            gap=LEADER_GAP_VALUE,
            confidence=GapConfidence.CONFIRMED,
            source=GapSource.RAW,
            should_emit=True,
        )

    # =========================
    # Case: Non-null raw interval
    # =========================
    if raw_interval is not None:
        driver_state.confirm_gap(raw_interval)
        return ResolutionResult(
            gap=raw_interval,
            confidence=GapConfidence.CONFIRMED,
            source=GapSource.RAW,
            should_emit=True,
        )

    # =========================
    # Null interval handling
    # =========================

    # Case D — Lap transition null
    if lap_number is not None and driver_state.current_lap is not None:
        if lap_number > driver_state.current_lap:
            driver_state.invalidate_gap()
            return ResolutionResult(
                gap=None,
                confidence=GapConfidence.INVALID,
                source=None,
                should_emit=False,
            )

    # Case E — Pit-related null
    if driver_state.in_pit or _is_post_pit_unstable(driver_state, event_time):
        driver_state.invalidate_gap()
        return ResolutionResult(
            gap=None,
            confidence=GapConfidence.INVALID,
            source=None,
            should_emit=False,
        )

    # Case F — Leader change null
    if leader is not None and driver_state.gap_confidence == GapConfidence.INVALID:
        return ResolutionResult(
            gap=None,
            confidence=GapConfidence.INVALID,
            source=None,
            should_emit=False,
        )

    # Case G — First-seen driver null
    if driver_state.last_valid_gap is None:
        return ResolutionResult(
            gap=None,
            confidence=GapConfidence.INVALID,
            source=None,
            should_emit=False,
        )

    # =========================
    # Case B / C — Propagation
    # =========================

    # Increment staleness
    driver_state.staleness_ticks += 1

    # Case C — Stale propagation
    if driver_state.staleness_ticks > MAX_STALENESS_TICKS:
        driver_state.invalidate_gap()
        return ResolutionResult(
            gap=None,
            confidence=GapConfidence.INVALID,
            source=None,
            should_emit=False,
        )

    # Case B — Stable propagation
    driver_state.estimate_gap()
    return ResolutionResult(
        gap=driver_state.last_valid_gap,
        confidence=GapConfidence.ESTIMATED,
        source=GapSource.PROPAGATED,
        should_emit=True,
    )
