"""Clean and normalize raw VIIRS fire observation records."""
from __future__ import annotations

import pandas as pd

from pipeline.preprocessing.normalize_fields import _empty_canonical_dataframe
from pipeline.preprocessing.quality_control import QCConfig, filter_invalid_rows


def clean_viirs(
    df: pd.DataFrame | None = None,
    *,
    source_product: str | None = None,
    config: QCConfig | None = None,
    return_rejected: bool = False,
) -> pd.DataFrame | tuple[pd.DataFrame, pd.DataFrame]:
    """Normalize and filter raw VIIRS fire records."""
    if df is None:
        empty = _empty_canonical_dataframe()
        if return_rejected:
            rejected = empty.copy()
            rejected["rejection_reason"] = pd.Series(dtype="object")
            return empty, rejected
        return empty
    return filter_invalid_rows(
        df,
        config=config,
        return_rejected=return_rejected,
        source_product=source_product,
        sensor="VIIRS",
    )
