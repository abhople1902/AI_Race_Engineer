from enum import Enum

class ServiceMode(str, Enum):
    LIVE = "live"
    REPLAY = "replay"
    IDLE = "idle"
