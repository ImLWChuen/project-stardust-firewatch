"""DateTime helpers and day-of-year conversions."""
from datetime import datetime

def parse_acq_datetime(acq_date: str, acq_time: str) -> datetime:
    time_str = str(acq_time).zfill(4)
    return datetime.strptime(f"{acq_date} {time_str}", "%Y-%m-%d %H%M")
