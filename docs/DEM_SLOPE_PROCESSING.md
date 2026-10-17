# DEM and Slope Processing — Ballari Urban Flood Digital Twin

## Study area
An initial rectangular working area around Ballari, Karnataka.
This is not an official municipal boundary.

## Source elevation data
- Dataset: Copernicus DSM GLO-30
- Original file: data/raw/dem/Copernicus_DSM_10_N15_00_E076_00_DEM.tif
- Source tile: approximately 76°E–77°E and 15°N–16°N
- Source CRS: EPSG:4326
- Elevation unit: metres
- Data type: Digital Surface Model (DSM), which may include buildings and vegetation.

## Processed elevation raster
- File: data/processed/dem/ballari_dem_utm43.tif
- CRS: EPSG:32643 (WGS 84 / UTM zone 43N)
- Dimensions: 715 × 591 pixels
- Pixel size: approximately 30.27 metres
- Method: GDAL warp, bilinear resampling, rectangular crop.

## Slope raster
- File: data/processed/slope/ballari_slope_degrees.tif
- Output unit: degrees
- Method: GDAL slope calculation
- Minimum: 0 degrees
- Maximum: approximately 47.749 degrees
- Mean: approximately 1.761 degrees
- Valid pixel percentage reported by GDAL: 100%.

## Visualization
- Colorized raster: data/processed/slope/ballari_slope_map.tif
- PNG preview: data/processed/slope/ballari_slope_preview.png
- Color ramp: data/processed/slope/slope_colors.txt
- Colors represent slope classes, not flood-risk classes.

## Limitations
- The working rectangle is not an official municipal boundary.
- The DSM is not a bare-earth terrain model.
- Slope alone cannot determine flood risk.
- The results must be validated and combined with rainfall, drainage,
  land cover, and other reliable data before flood-risk conclusions are made.
