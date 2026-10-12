import pandas as pd
from science.harmonization.temporal_normalization import deduplicate_temporal_window

def test_temporal_dedup():
    """Verify duplicate observations within the same temporal window are collapsed."""
    df = pd.DataFrame([
        {"cell_id": "c1", "acq_date": "2026-03-01", "frp": 12.0},
        {"cell_id": "c1", "acq_date": "2026-03-01", "frp": 14.0}
    ])
    deduped = deduplicate_temporal_window(df)
    assert len(deduped) == 1
