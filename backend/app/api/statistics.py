from fastapi import APIRouter
from app.schemas.statistics import StatisticsSummaryResponse

router = APIRouter()

@router.get("/summary", response_model=StatisticsSummaryResponse)
def get_statistics():
    """Return summary statistics for total observations and harmonized cells."""
    return {"total_observations": 1250000, "harmonized_cells": 45000}
