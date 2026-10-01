"""Aggregated API Router."""
from fastapi import APIRouter
from app.api import health, aoi, calendar, hotspots, harmonization, anomalies, statistics

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(aoi.router, prefix="/aoi", tags=["AOI"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["Calendar"])
api_router.include_router(hotspots.router, prefix="/hotspots", tags=["Hotspots"])
api_router.include_router(harmonization.router, prefix="/harmonization", tags=["Harmonization"])
api_router.include_router(anomalies.router, prefix="/anomalies", tags=["Anomalies"])
api_router.include_router(statistics.router, prefix="/statistics", tags=["Statistics"])
