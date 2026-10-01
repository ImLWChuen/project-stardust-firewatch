from dataclasses import dataclass

@dataclass
class DataSourceModel:
    source_name: str
    product_code: str
    last_synced: str
