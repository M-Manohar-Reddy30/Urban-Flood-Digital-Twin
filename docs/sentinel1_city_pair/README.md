# Ballari Sentinel-1 city comparison

## Scope

Exploratory radar comparison between 28 May and 9 June 2026.
These results are not verified flood labels or a validated flood map.
The 9 June acquisition may miss temporary waterlogging reported on 7 June.

## Source data

The exact processed ZIP filenames and SHA-256 checksums are recorded in
source_manifest.json. Keep independent backups of both ZIPs.

Expected ZIP location:
data/raw/flood_evidence/sentinel1_rtc/

Other required local inputs:
- data/processed/ballari_municipal_boundary_2d.geojson
- data/processed/ballari_landcover_2021.tif

The manifest records the boundary checksum. Land cover represents 2021,
not verified land use in June 2026.

## Processing

ASF HyP3 RTC GAMMA products: gamma-0 linear power, 30-metre pixel spacing,
EPSG:32643, no speckle filter applied.

City crops use matching ground coordinates without radar interpolation.
The city mask includes pixels whose centres lie inside the boundary.
Common usable pixels require positive finite VV and VH values and
layover/shadow code 1 on both dates.

Land-cover categories are sampled directly from the original land-cover
raster onto the radar grid using nearest-neighbour resampling.

Radar change is 10*log10(June9 power) - 10*log10(May28 power).

## Commands currently available

Run from the project root with the project environment activated:

    python scripts/verify_sentinel1_city_rebuild.py
    python scripts/analyze_sentinel1_city_pair.py

The verification command rebuilds arrays in memory and compares them with
existing saved city rasters.

To restore missing city rasters from the original ZIPs and boundary:

    python scripts/restore_sentinel1_city_pair.py --output data/processed/flood_evidence/sentinel1_city_pair

The destination must not already exist. The command verifies source ZIP
and boundary checksums against source_manifest.json, rebuilds ten city
layers and two masks, checks written pixel values, and saves provenance.
Temporary outputs are cleaned up if processing fails.

Restoration was tested in a separate directory. All twelve restored
rasters matched the existing grids and pixel values exactly, and
provenance matched. The comparison PNG is not regenerated.

The original ZIPs and boundary remain required external inputs.
The original 2021 land-cover raster is additionally required for the
land-cover analysis command.

Expected output directory:
data/processed/flood_evidence/sentinel1_city_pair/

## Verified results

- City pixel centres: 97,459
- Common usable pixels: 97,385
- Common usable coverage: 99.92%
- Median VV change: +1.573 dB
- Median VH change: +1.450 dB

Coverage is not prediction accuracy. Radar changes do not establish their
cause, flood extent, water depth, or the absence of flooding.

## Software environment

environment.json records versions from the environment used to run the
verification successfully. It is an environment record, not a dependency
lockfile.

## Attribution

RTC product processed by ASF DAAC HyP3 2026 using GAMMA software.
Contains modified Copernicus Sentinel data 2026, processed by ESA.
