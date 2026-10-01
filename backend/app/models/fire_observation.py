from dataclasses import dataclass

@dataclass
class FireObservationModel:
    id: str
    latitude: float
    longitude: float
    acq_date: str
    satellite: str
    instrument: str
    frp: float
