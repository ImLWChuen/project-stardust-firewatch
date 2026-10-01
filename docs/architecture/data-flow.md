# Data Flow Architecture

This document describes the end-to-end data lifecycle:
1. **Raw Ingestion**: Ingesting NASA FIRMS MODIS (C6.1) and VIIRS (VNP14IMGTDL, VJ114IMGTDL, VJ214IMGTDL).
2. **Preprocessing**: Timestamp normalization, confidence filtering, geometry validation.
3. **Harmonization Engine**:
   - Spatial aggregation to equal-area grid cells.
   - Dual-sensor observation overlap matching.
   - Sensor scaling and sensor calibration model application.
4. **Product Generation**: Daily harmonized fire cell aggregates, climatological baselines, anomaly scores.
5. **API & Visualization**: Serving aggregated geospatial tiles and timeseries.
