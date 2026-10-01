"""Sensor Registry class managing active satellite instruments."""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class SensorSpec:
    name: str
    instrument: str
    platform: str
    spatial_resolution_m: float
    equator_crossing_time: str
    active: bool = True

class SensorRegistry:
    def __init__(self):
        self._sensors: Dict[str, SensorSpec] = {
            "MODIS_TERRA": SensorSpec("MODIS_TERRA", "MODIS", "Terra", 1000.0, "10:30 AM/PM"),
            "MODIS_AQUA": SensorSpec("MODIS_AQUA", "MODIS", "Aqua", 1000.0, "01:30 PM/AM"),
            "VIIRS_SNPP": SensorSpec("VIIRS_SNPP", "VIIRS", "Suomi-NPP", 375.0, "01:30 PM/AM"),
            "VIIRS_NOAA20": SensorSpec("VIIRS_NOAA20", "VIIRS", "NOAA-20", 375.0, "01:30 PM/AM"),
            "VIIRS_NOAA21": SensorSpec("VIIRS_NOAA21", "VIIRS", "NOAA-21", 375.0, "01:30 PM/AM"),
        }

    def get(self, key: str) -> Optional[SensorSpec]:
        return self._sensors.get(key.upper())

    def list_active(self) -> list[SensorSpec]:
        return [s for s in self._sensors.values() if s.active]
