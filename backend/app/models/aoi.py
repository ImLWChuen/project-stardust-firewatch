from dataclasses import dataclass

@dataclass
class AOIModel:
    """Domain model representing an area of interest."""

    id: str
    name: str
    country: str
    geometry: dict
