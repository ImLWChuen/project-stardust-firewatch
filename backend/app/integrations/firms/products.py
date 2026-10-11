"""Backend re-exports of canonical NASA FIRMS product definitions."""
from __future__ import annotations

from pipeline.connectors.firms.products import (
    MODIS_NRT,
    MODIS_SP,
    NRT_PRODUCTS,
    PRODUCT_METADATA,
    PRODUCTS,
    SP_PRODUCTS,
    VIIRS_NOAA20_NRT,
    VIIRS_NOAA20_SP,
    VIIRS_NOAA21_NRT,
    VIIRS_SNPP_NRT,
    VIIRS_SNPP_SP,
    get_products_for_sensor,
    select_products,
    validate_product,
)

__all__ = [
    "MODIS_NRT",
    "MODIS_SP",
    "NRT_PRODUCTS",
    "PRODUCTS",
    "PRODUCT_METADATA",
    "SP_PRODUCTS",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA20_SP",
    "VIIRS_NOAA21_NRT",
    "VIIRS_SNPP_NRT",
    "VIIRS_SNPP_SP",
    "get_products_for_sensor",
    "select_products",
    "validate_product",
]
