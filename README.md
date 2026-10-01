# Project Stardust

> **Harmonized Satellite Fire Detection, Calibrated Activity Index & Agricultural Burning Calendar Platform**

Project Stardust addresses the multi-sensor discontinuity between NASA MODIS (Terra/Aqua) and VIIRS (Suomi-NPP, NOAA-20, NOAA-21) active fire products. By normalizing spatial resolution differences (1km vs 375m), deduplicating overlapping orbits, calibrating sensor sensitivities, and establishing baseline climatology, Stardust produces a unified, long-term fire activity time series and an intelligent agricultural burning calendar.

---

## Key Modules
- **`science/`**: Core harmonization models, spatial normalization, sensor calibration, and anomaly detection algorithms.
- **`pipeline/`**: Scalable data ingestion, preprocessing, transformation, and daily update jobs.
- **`backend/`**: FastAPI REST API serving area of interest (AOI) metrics, burning calendar predictions, and geospatial hotspot queries.
- **`frontend/`**: Next.js dashboard featuring interactive fire maps, calendar heatmaps, and sensor comparison charts.
- **`docs/`**: Architecture diagrams, scientific methodology, data dictionaries, and hackathon collateral.
- **`notebooks/`**: Research and verification notebooks validating scientific integrity.
- **`tests/`**: Unit, integration, and scientific regression test suites.

---

## Quickstart

```bash
# Clone and setup environment
make setup

# Run tests
make test

# Start backend & frontend dev servers
make dev
```
