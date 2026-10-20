# Data Requirements

## Study Area
Ballari Urban Area, Karnataka, India

## Required Data

### 1. Rainfall Data
- Historical rainfall
- Date and time
- Rainfall amount
- Ideally hourly or daily measurements

### 2. Elevation Data
- Digital Elevation Model (DEM)
- Elevation values for the study area
- Preferably high-resolution data

### 3. Slope Data
- Derived from the DEM
- Represents terrain steepness

### 4. Land Use / Land Cover
- Built-up areas
- Vegetation
- Water bodies
- Agricultural areas
- Open/unused land

### 5. Historical Flood Data
- Previous flood/inundation locations
- Flood occurrence records
- Flood extent where available

### 6. Urban Infrastructure
- Roads
- Buildings
- Major junctions
- Hospitals
- Schools
- Other critical facilities

### 7. Drainage Data
- Drainage channels
- Stormwater drains
- Other available drainage information

## AI Prediction Features

Potential model features:

- Rainfall
- Elevation
- Slope
- Land Use/Land Cover
- Historical flood information
- Drainage-related features

## Target Variable

The final AI target will be selected only after examining
the available real flood datasets.

Possible target:

- Flood
- No Flood

The target will NOT be artificially created.

## Data Processing

Raw data will be stored in:

data/raw/

Processed data will be stored in:

data/processed/

External reference data will be stored in:

data/external/


## Drainage Data Availability Audit

### Existing evidence reviewed

- The Ballari District Disaster Management Plan 2025-26 and 2026-27 contains a district-level drainage map on printed page 282.
- The extracted drainage-map image is only 402 x 283 pixels. It is retained as a reference image and is not treated as a georeferenced drainage network.
- `data/raw/boundaries/ballari/doc.kml` contains 40 features: 31 polygons, 7 multipolygons, one line and one point.
- The line feature is named `Ballari CC-ULB Boundary`; it represents the municipal boundary, not a verified drainage feature.
- `data/raw/boundaries/ballari/ballari_wardmap.geojson` contains the same ward-map feature set.
- The processed municipal boundary is available at `data/processed/ballari_municipal_boundary.geojson`.

### Current conclusion

A dedicated, verified drainage-network dataset for Ballari urban area has not yet been identified in the inspected project files.

### Data required

Investigate authoritative or otherwise well-documented sources for:

- Natural streams, rivers and drainage paths.
- Urban stormwater drains and major culverts, where available.
- Drainage-network geometry, source date, coordinate reference system and positional accuracy.
- Whether the data covers the municipal study boundary.

Do not digitize drainage features from the low-resolution reference map or assign drainage attributes without supporting evidence. If a suitable dataset cannot be obtained, document the limitation and proceed only with analyses supported by the available data.
