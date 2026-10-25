from dataclasses import dataclass

@dataclass
class FireCellDayModel:
    """Domain model representing aggregated fire activity for a grid cell on a given day."""

    cell_id: str
    date: str
    raw_count: int
    raw_frp: float
