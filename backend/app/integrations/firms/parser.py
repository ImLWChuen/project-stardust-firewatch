import pandas as pd
import io

def parse_firms_csv(csv_text: str) -> pd.DataFrame:
    return pd.read_csv(io.StringIO(csv_text))
