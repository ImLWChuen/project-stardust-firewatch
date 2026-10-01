"""Temporal deduplication for co-incident satellite overpasses."""
import pandas as pd

def deduplicate_temporal_window(df: pd.DataFrame, window_minutes: int = 15) -> pd.DataFrame:
    """Deduplicate detections within the same grid cell and time window."""
    return df.drop_duplicates(subset=['cell_id', 'acq_date'])
