"""Data canonicalization, schema standardization, and confidence filtering."""
from typing import Dict, Any, List
import pandas as pd
import numpy as np

REQUIRED_CANONICAL_COLUMNS = [
    "latitude", "longitude", "acq_date", "acq_time", 
    "satellite", "instrument", "confidence", "frp", "daynight"
]

def canonicalize_observation(record: Dict[str, Any]) -> Dict[str, Any]:
    """Standardize individual raw fire record into canonical schema."""
    lat = float(record.get("latitude", 0.0))
    lon = float(record.get("longitude", 0.0))
    frp = float(record.get("frp", 0.0))
    acq_date = str(record.get("acq_date", "")).strip()
    acq_time = str(record.get("acq_time", "0000")).zfill(4)
    satellite = str(record.get("satellite", "Unknown")).upper()
    instrument = str(record.get("instrument", "MODIS" if "T" in satellite or "A" in satellite else "VIIRS"))
    confidence = str(record.get("confidence", "nominal"))
    daynight = str(record.get("daynight", "D")).upper()

    return {
        "latitude": lat,
        "longitude": lon,
        "acq_date": acq_date,
        "acq_time": acq_time,
        "satellite": satellite,
        "instrument": instrument,
        "confidence": confidence,
        "frp": frp,
        "daynight": daynight,
    }

def canonicalize_fire_dataframe(df: pd.DataFrame, min_confidence: float = 30.0) -> pd.DataFrame:
    """Clean, filter, and cast fire detection DataFrame to canonical format."""
    cleaned = df.dropna(subset=["latitude", "longitude", "acq_date"]).copy()
    cleaned["latitude"] = pd.to_numeric(cleaned["latitude"], errors="coerce")
    cleaned["longitude"] = pd.to_numeric(cleaned["longitude"], errors="coerce")
    cleaned = cleaned.dropna(subset=["latitude", "longitude"])
    
    # Standardize time format
    if "acq_time" in cleaned.columns:
        cleaned["acq_time"] = cleaned["acq_time"].astype(str).str.zfill(4)
        
    return cleaned
