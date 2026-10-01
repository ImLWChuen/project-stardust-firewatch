# System Architecture

## Overview
Project Stardust is organized into a modular layered architecture separating scientific computation, ETL data pipelining, RESTful API services, and client presentation.

```
+-------------------------------------------------------+
|                    Frontend (Next.js)                 |
|  - Fire Map (MapLibre / Leaflet)                      |
|  - Burning Calendar Heatmaps                          |
|  - Anomaly & Sensor Comparison Analytics              |
+---------------------------+---------------------------+
                            | HTTP / JSON REST
+---------------------------v---------------------------+
|                    Backend (FastAPI)                  |
|  - Routers: AOI, Calendar, Hotspots, Anomalies        |
|  - Services & Repository layer                        |
|  - NASA FIRMS Client & Cache                          |
+---------------------------+---------------------------+
                            |
+---------------------------v---------------------------+
|               Scientific Harmonization Core           |
|  - Spatial Normalization (0.01-deg Equal-Area Grid)   |
|  - Temporal Deduplication (Overlap Orbit Windows)     |
|  - Non-linear FRP & Detection Bias Calibration        |
|  - Climatology Baseline & Anomaly Z-Score Scoring     |
+-------------------------------------------------------+
```
