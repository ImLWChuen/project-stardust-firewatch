"""Analyze statistical continuity during the MODIS-to-VIIRS sensor transition period."""
import numpy as np
import pandas as pd

def compute_transition_ratio(modis_series: pd.Series, viirs_series: pd.Series) -> float:
    """Compute ratio of detection densities during coincident operational window (2012-present)."""
    m_sum = modis_series.sum()
    v_sum = viirs_series.sum()
    if m_sum == 0:
        return 0.0
    return float(v_sum / m_sum)

def test_distribution_continuity(pre_transition: pd.Series, post_transition: pd.Series) -> dict:
    """Assess statistical homogeneity across transition cutoff."""
    mean_diff = float(post_transition.mean() - pre_transition.mean())
    return {
        "mean_difference": mean_diff,
        "continuous": abs(mean_diff) < 2.0
    }
