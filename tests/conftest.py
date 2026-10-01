import sys
from pathlib import Path

# Add project root and backend folder to sys.path so 'app', 'science', 'pipeline', and 'backend' are discoverable
ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

for p in (ROOT, BACKEND):
    p_str = str(p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)
