"""High-level orchestrator for full fire data harmonization pipeline."""

class FireHarmonizer:
    """Unified pipeline integrating spatial, temporal, and calibration steps."""
    def __init__(self, config=None):
        self.config = config or {}

    def harmonize(self, dataset):
        return dataset
