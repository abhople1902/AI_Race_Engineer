# interval_normalizer/config.py

from enum import Enum


# =========================
# Time & Ordering Constants
# =========================

# Allowed out-of-order window for event-time (seconds)
ALLOWED_LATENESS_SECONDS = 2

# =========================
# Staleness / Propagation
# =========================

# Maximum number of propagation ticks allowed before gap is invalidated
MAX_STALENESS_TICKS = 3

# Number of seconds after pit exit during which gaps are considered unstable
POST_PIT_STABILIZATION_SECONDS = 5


# =========================
# Confidence Enums
# =========================

class GapConfidence(Enum):
    """
    Confidence level of a normalized gap.
    """
    CONFIRMED = "CONFIRMED"   # Derived directly from non-null raw interval
    ESTIMATED = "ESTIMATED"   # Safely propagated from previous value
    INVALID = "INVALID"       # Cannot be trusted or emitted


# =========================
# Gap Source (Debug / Internal)
# =========================

class GapSource(Enum):
    """
    Internal-only classification of how a gap was produced.
    """
    RAW = "RAW"
    PROPAGATED = "PROPAGATED"


# =========================
# Emission Control
# =========================

# Prevents duplicate emissions with identical logical meaning
SUPPRESS_DUPLICATE_EMISSIONS = True

# Leader gap is always forced to this value
LEADER_GAP_VALUE = 0.0
