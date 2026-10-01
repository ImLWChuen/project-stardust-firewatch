# Project Stardust Backend

FastAPI REST service providing endpoints for:
- AOI (Area of Interest) queries & management
- Agricultural Burning Calendar predictions & history
- Live and historical harmonized fire hotspots
- Regional anomaly alerts and statistical aggregates

## Running Locally

```bash
pip install -e .
uvicorn app.main:app --reload --port 8000
```
