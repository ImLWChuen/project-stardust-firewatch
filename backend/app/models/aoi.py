from dataclasses import dataclass

@dataclass
class AOIModel:
    id: str
    name: str
    country: str
    geometry: dict
