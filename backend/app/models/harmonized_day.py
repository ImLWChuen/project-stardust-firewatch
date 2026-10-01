from dataclasses import dataclass

@dataclass
class HarmonizedDayModel:
    cell_id: str
    date: str
    harmonized_activity_index: float
    calibrated_frp: float
