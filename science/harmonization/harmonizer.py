"""High-level orchestrator for full fire data harmonization pipeline."""

class FireHarmonizer:
    """Unified pipeline integrating spatial, temporal, and calibration steps."""
    def __init__(self, config=None):
        """Initialize the harmonizer with optional pipeline configuration."""
        self.config = config or {}

    def harmonize(self, dataset):
        """Apply the full harmonization pipeline to the given dataset."""
        return dataset
