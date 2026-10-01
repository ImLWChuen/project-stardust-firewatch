from dataclasses import dataclass

@dataclass
class FireCellDayModel:
    cell_id: str
    date: str
    raw_count: int
    raw_frp: float
