"""Configuration parameters and loader for harmonization models."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HARMONIZATION_CONFIG_PATH = REPO_ROOT / "config" / "harmonization.yaml"

DEFAULT_GRID_SIZE_DEG = 0.01
DEDUPLICATION_WINDOW_MINUTES = 20
MODIS_VIIRS_SCALING_FACTOR = 1.42


def load_harmonization_config(
    config_path: Path | str | None = None,
) -> dict[str, Any]:
    """Load harmonization settings from config/harmonization.yaml."""
    path = (
        Path(config_path)
        if config_path is not None
        else DEFAULT_HARMONIZATION_CONFIG_PATH
    )
    if not path.exists():
        return {
            "grid_resolution_deg": DEFAULT_GRID_SIZE_DEG,
            "temporal_dedup_window_minutes": DEDUPLICATION_WINDOW_MINUTES,
        }
    with open(path, encoding="utf-8") as fh:
        payload = yaml.safe_load(fh) or {}
    if not isinstance(payload, dict):
        raise TypeError("Harmonization config YAML root must be a mapping.")
    section = payload.get("harmonization", payload)
    if not isinstance(section, dict):
        raise TypeError("'harmonization' section in config must be a mapping.")
    return section


def get_configured_grid_resolution(config_path: Path | str | None = None) -> float:
    """Return configured spatial grid resolution in degrees (default 0.01)."""
    cfg = load_harmonization_config(config_path)
    return float(cfg.get("grid_resolution_deg", DEFAULT_GRID_SIZE_DEG))


def get_configured_dedup_window_minutes(config_path: Path | str | None = None) -> int:
    """Return configured temporal deduplication window in minutes (default 20)."""
    cfg = load_harmonization_config(config_path)
    return int(cfg.get("temporal_dedup_window_minutes", DEDUPLICATION_WINDOW_MINUTES))
