# Data Pipeline

ETL pipeline executing automated ingestion, cleaning, transformation, and harmonization for satellite fire data.

## Stages:
1. `ingestion/`: Download raw feeds from NASA FIRMS Area API (`<= 5` days per request chunk).
2. `preprocessing/`: Quality control, invalid row filtering, and canonical field standardization across MODIS and VIIRS.
3. `transformation/`: Configured `0.01°` equal-angle spatial gridding, `20`-minute temporal deduplication, and `FireCellDay` daily aggregation.
4. `harmonization/`: Overlap extraction, model fitting, and calibrated index generation.
5. `jobs/`: End-to-end orchestration routines (`python -m pipeline.jobs.daily_update` / `python -m pipeline.jobs.rebuild_region`).
