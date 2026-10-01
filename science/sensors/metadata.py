"""Detailed technical metadata for MODIS and VIIRS instruments."""

SENSOR_METADATA = {
    "MODIS": {
        "bands_fire": ["B21", "B22", "B31"],
        "swath_width_km": 2330.0,
        "nadir_pixel_m": 1000.0,
        "edge_pixel_m": 4800.0,
        "quantization_bits": 12
    },
    "VIIRS": {
        "bands_fire": ["I4", "I5", "M13"],
        "swath_width_km": 3060.0,
        "nadir_pixel_m": 375.0,
        "edge_pixel_m": 800.0,
        "quantization_bits": 14
    }
}
