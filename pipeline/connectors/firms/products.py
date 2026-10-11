"""Product codes and selection helpers supported by NASA FIRMS Area API."""
from __future__ import annotations

# Near Real-Time (NRT) products (available within ~3 hours of observation)
MODIS_NRT = "MODIS_NRT"
VIIRS_SNPP_NRT = "VIIRS_SNPP_NRT"
VIIRS_NOAA20_NRT = "VIIRS_NOAA20_NRT"
VIIRS_NOAA21_NRT = "VIIRS_NOAA21_NRT"

# Standard Processing (SP) science-quality archive products (~2-3 month latency)
# Note: NASA FIRMS does not provide a Standard Processing product for NOAA-21.
MODIS_SP = "MODIS_SP"
VIIRS_SNPP_SP = "VIIRS_SNPP_SP"
VIIRS_NOAA20_SP = "VIIRS_NOAA20_SP"

NRT_PRODUCTS: tuple[str, ...] = (
    MODIS_NRT,
    VIIRS_SNPP_NRT,
    VIIRS_NOAA20_NRT,
    VIIRS_NOAA21_NRT,
)

SP_PRODUCTS: tuple[str, ...] = (
    MODIS_SP,
    VIIRS_SNPP_SP,
    VIIRS_NOAA20_SP,
)

PRODUCTS: dict[str, str] = {
    MODIS_NRT: MODIS_NRT,
    MODIS_SP: MODIS_SP,
    VIIRS_SNPP_NRT: VIIRS_SNPP_NRT,
    VIIRS_SNPP_SP: VIIRS_SNPP_SP,
    VIIRS_NOAA20_NRT: VIIRS_NOAA20_NRT,
    VIIRS_NOAA20_SP: VIIRS_NOAA20_SP,
    VIIRS_NOAA21_NRT: VIIRS_NOAA21_NRT,
}

PRODUCT_METADATA: dict[str, dict[str, str]] = {
    MODIS_NRT: {"sensor": "MODIS", "platform": "Terra/Aqua", "mode": "nrt"},
    MODIS_SP: {"sensor": "MODIS", "platform": "Terra/Aqua", "mode": "sp"},
    VIIRS_SNPP_NRT: {"sensor": "VIIRS", "platform": "Suomi-NPP", "mode": "nrt"},
    VIIRS_SNPP_SP: {"sensor": "VIIRS", "platform": "Suomi-NPP", "mode": "sp"},
    VIIRS_NOAA20_NRT: {"sensor": "VIIRS", "platform": "NOAA-20", "mode": "nrt"},
    VIIRS_NOAA20_SP: {"sensor": "VIIRS", "platform": "NOAA-20", "mode": "sp"},
    VIIRS_NOAA21_NRT: {"sensor": "VIIRS", "platform": "NOAA-21", "mode": "nrt"},
}

_MODE_ALIASES: dict[str, str] = {
    "nrt": "nrt",
    "near_real_time": "nrt",
    "near-real-time": "nrt",
    "realtime": "nrt",
    "sp": "sp",
    "standard": "sp",
    "historical": "sp",
    "archive": "sp",
}

_SENSOR_PRODUCTS_BY_MODE: dict[str, dict[str, tuple[str, ...]]] = {
    "modis": {
        "nrt": (MODIS_NRT,),
        "sp": (MODIS_SP,),
    },
    "viirs": {
        "nrt": (VIIRS_SNPP_NRT, VIIRS_NOAA20_NRT, VIIRS_NOAA21_NRT),
        "sp": (VIIRS_SNPP_SP, VIIRS_NOAA20_SP),
    },
    "snpp": {
        "nrt": (VIIRS_SNPP_NRT,),
        "sp": (VIIRS_SNPP_SP,),
    },
    "noaa20": {
        "nrt": (VIIRS_NOAA20_NRT,),
        "sp": (VIIRS_NOAA20_SP,),
    },
    "noaa21": {
        "nrt": (VIIRS_NOAA21_NRT,),
        "sp": (),
    },
    "all": {
        "nrt": NRT_PRODUCTS,
        "sp": SP_PRODUCTS,
    },
}

_SENSOR_ALIASES: dict[str, str] = {
    "modis": "modis",
    "viirs": "viirs",
    "all": "all",
    "snpp": "snpp",
    "suomi-npp": "snpp",
    "suomi_npp": "snpp",
    "viirs_snpp": "snpp",
    "noaa20": "noaa20",
    "noaa-20": "noaa20",
    "noaa_20": "noaa20",
    "viirs_noaa20": "noaa20",
    "noaa21": "noaa21",
    "noaa-21": "noaa21",
    "noaa_21": "noaa21",
    "viirs_noaa21": "noaa21",
}


def validate_product(source: str) -> str:
    """Validate and return a canonical NASA FIRMS product code."""
    if not isinstance(source, str):
        raise TypeError("FIRMS product source must be a string.")
    if not source.strip():
        raise ValueError("FIRMS product source must be a non-empty string.")
    normalized = source.strip().upper()
    if normalized not in PRODUCTS:
        supported = ", ".join(sorted(PRODUCTS.keys()))
        raise ValueError(
            f"Unsupported FIRMS product {source!r}. Supported products: {supported}"
        )
    return normalized


def get_products_for_sensor(sensor: str = "all", mode: str = "nrt") -> list[str]:
    """Return supported FIRMS product codes for a sensor family and processing mode.

    Args:
        sensor: Sensor or platform name ('modis', 'viirs', 'all', 'snpp', 'noaa20', 'noaa21').
        mode: Processing mode ('nrt' for Near Real-Time, 'sp' for Standard Processing).

    Returns:
        List of valid FIRMS product identifiers.
    """
    if not isinstance(sensor, str):
        raise TypeError("sensor must be a string.")
    if not sensor.strip():
        raise ValueError("sensor must be a non-empty string.")
    if not isinstance(mode, str):
        raise TypeError("mode must be a string.")
    if not mode.strip():
        raise ValueError("mode must be a non-empty string.")

    sensor_key = _SENSOR_ALIASES.get(sensor.strip().lower())
    if sensor_key is None:
        raise ValueError(
            f"Unsupported sensor {sensor!r}. Expected one of: modis, viirs, all, snpp, noaa20, noaa21."
        )

    mode_key = _MODE_ALIASES.get(mode.strip().lower())
    if mode_key is None:
        raise ValueError(
            f"Unsupported mode {mode!r}. Expected 'nrt' or 'sp'."
        )

    products = list(_SENSOR_PRODUCTS_BY_MODE[sensor_key][mode_key])
    if not products:
        raise ValueError(
            f"No FIRMS products available for sensor={sensor!r} in mode={mode!r} "
            "(NOAA-21 does not have a Standard Processing product)."
        )
    return products


select_products = get_products_for_sensor
