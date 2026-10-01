# Data Pipeline

ETL pipeline executing automated ingestion, cleaning, transformation, and harmonization for satellite fire data.

## Stages:
1. `ingestion/`: Download raw feeds from FIRMS.
2. `preprocessing/`: Quality control, invalid coordinate drops, field standardization.
3. `transformation/`: Equal-area gridding, temporal deduplication, cell aggregation.
4. `harmonization/`: Overlap extraction, model fitting, and calibrated index generation.
5. `jobs/`: Scheduled orchestration routines.
