import io
import pandas as pd

def parse_firms_csv(csv_text: str) -> pd.DataFrame:
    """Parse FIRMS CSV response text into a standard DataFrame."""
    return pd.read_csv(io.StringIO(csv_text))
