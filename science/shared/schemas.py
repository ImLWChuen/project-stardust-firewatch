"""Standard internal data schemas for fire observations."""
from dataclasses import dataclass
from datetime import datetime

@dataclass
class FireObservationRecord:
    latitude: float
    longitude: float
    brightness: float
    scan: float
    track: float
    acq_date: str
    acq_time: str
    satellite: str
    instrument: str
    confidence: str
    frp: float
