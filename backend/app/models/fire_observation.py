from dataclasses import dataclass

@dataclass
class FireObservationModel:
    """Domain model representing a single raw satellite fire observation."""

    id: str
    latitude: float
    longitude: float
    acq_date: str
    satellite: str
    instrument: str
    frp: float
