from pydantic import BaseModel

class StatisticsSummaryResponse(BaseModel):
    total_observations: int
    harmonized_cells: int
