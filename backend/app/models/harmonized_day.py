from dataclasses import dataclass

@dataclass
class HarmonizedDayModel:
    """Domain model representing the harmonized, cross-sensor activity index for a grid cell on a given day."""

    cell_id: str
    date: str
    harmonized_activity_index: float
    calibrated_frp: float
