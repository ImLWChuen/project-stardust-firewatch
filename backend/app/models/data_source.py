from dataclasses import dataclass

@dataclass
class DataSourceModel:
    """Domain model representing an upstream data source and its sync state."""

    source_name: str
    product_code: str
    last_synced: str
