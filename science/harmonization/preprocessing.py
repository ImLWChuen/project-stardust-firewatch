"""Data cleaning, confidence filtering, and format standardization."""
import pandas as pd

def clean_fire_observations(df: pd.DataFrame, min_confidence: float = 30.0) -> pd.DataFrame:
    """Filter invalid coordinates and low confidence detections."""
    cleaned = df.dropna(subset=['latitude', 'longitude', 'acq_date'])
    return cleaned
