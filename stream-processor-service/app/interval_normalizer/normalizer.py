# interval_normalizer/normalizer.py

from datetime import datetime
from typing import Any, Dict, Optional

from .models import SessionState, DriverState
from .ordering import (
    should_update_driver_state,
    evaluate_leader_event_time,
    OrderingDecision,
)
from .null_logic import resolve_interval
from .config import GapConfidence, LEADER_GAP_VALUE


class IntervalNormalizer:
    """
    Core orchestration engine for interval normalization.
    This class is Kafka-agnostic and replay-safe.
    """

    def __init__(self, session_key: str):
        self.session_state = SessionState(session_key=session_key)

    # =========================
    # Public Entry Point
    # =========================

    def process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single timing-related event.

        Expected event fields (union of inputs):
        - driver_number
        - event_time (datetime)
        - lap_number (optional)
        - interval (optional)
        - event_type: intervals | laps | pit | positions
        - position (for positions events)
        """

        event_type = event.get("event_type")
        driver_number = event.get("driver_number")
        event_time: datetime = event.get("event_time")
        lap_number = event.get("lap_number")
        gap_leader = event.get("gap_to_leader")
        raw_interval = event.get("interval")

        # Lazily create driver state
        driver_state = self.session_state.get_or_create_driver(driver_number)

        # =========================
        # Ordering / acceptance
        # =========================

        should_update, ordering_decision = should_update_driver_state(
            driver_state=driver_state,
            event_time=event_time,
            lap_number=lap_number,
        )

        if not should_update:
            print("🔥🔥🔥🔥🔥")
            return None

        # =========================
        # Update basic driver timing
        # =========================

        # Update event-time only if accepted or late-accepted
        driver_state.last_event_time = event_time

        # Update lap number if present
        if lap_number is not None:
            driver_state.current_lap = lap_number
            self.session_state.current_lap_number = lap_number

        # =========================
        # Handle leader updates (from positions)
        # =========================

        if event_type == "positions":
            position = event.get("position")
            if position == 1:
                if evaluate_leader_event_time(self.session_state, event_time):
                    if self.session_state.current_leader_driver != driver_number:
                        self.session_state.reset_leader(driver_number, event_time)
                        self.session_state.invalidate_all_non_leader_gaps()

        # =========================
        # Handle pit events
        # =========================

        if event_type == "pit":
            pit_status = event.get("in_pit")
            if pit_status is True:
                driver_state.in_pit = True
                driver_state.pit_entry_time = event_time
                driver_state.invalidate_gap()
                return None
            else:
                driver_state.in_pit = False
                # pit_entry_time retained for stabilization window
                return None

        # =========================
        # Interval resolution
        # =========================

        resolution = resolve_interval(
            session_state=self.session_state,
            driver_state=driver_state,
            raw_interval=gap_leader,
            event_time=event_time,
            lap_number=lap_number,
        )

        if not resolution.should_emit:
            print("💠💠💠💠")
            return None

        if driver_state.current_lap is None:
            print("🟣🟣🟣🟣🟣")
            return None

        # Do not emit if lap regresses (cross-topic skew protection)
        last_emitted_lap = getattr(driver_state, "_last_emitted_lap", None)
        if last_emitted_lap is not None:
            if driver_state.current_lap < last_emitted_lap:
                print("🎯🎯🎯🎯🎯")
                return None


        # =========================
        # Emission deduplication
        # =========================

        if (self.session_state.last_emission_time is not None and event_time < self.session_state.last_emission_time):
            print("🤯🤯🤯🤯")
            return None

        self.session_state.last_emission_time = event_time

        # =========================
        # Build output record
        # =========================

        is_leader = (
            driver_number == self.session_state.current_leader_driver
        )

        output = {
            "session_key": self.session_state.session_key,
            "event_time": event_time,
            "driver_number": driver_number,
            "lap_number": driver_state.current_lap,
            # "interval": (
            #     LEADER_GAP_VALUE if is_leader else resolution.gap
            # ),
            "gap_to_leader": (
                LEADER_GAP_VALUE if is_leader else resolution.gap
            ),
            "confidence": resolution.confidence.value,
            "leader_driver_number": self.session_state.current_leader_driver,
            "is_leader": is_leader,
        }

        #temp?
        driver_state._last_emitted_lap = driver_state.current_lap

        return output
