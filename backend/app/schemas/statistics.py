from pydantic import BaseModel

class StatisticsSummaryResponse(BaseModel):
    """Response schema for aggregate fire observation statistics."""

    total_observations: int
    harmonized_cells: int
