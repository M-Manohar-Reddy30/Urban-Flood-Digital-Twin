from pathlib import Path
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import geometry_mask
from scipy import ndimage
from shapely.geometry import mapping

ROOT = Path(__file__).resolve().parents[1]

DEM_FILE = ROOT / "data/processed/hydrology/ballari_hydrology_dem_30m_complete.tif"
BOUNDARY_FILE = ROOT / "data/processed/ballari_municipal_boundary_2d.geojson"

BUFFER_METRES = 10000

boundary = gpd.read_file(BOUNDARY_FILE)

if boundary.empty or boundary.crs is None:
    raise ValueError("Municipal boundary is missing or has no CRS.")

with rasterio.open(DEM_FILE) as src:
    if src.crs is None or src.crs.to_epsg() != 32643:
        raise ValueError(f"Unexpected DEM CRS: {src.crs}")

    boundary_utm = boundary.to_crs(src.crs)
    municipal = boundary_utm.geometry.union_all()
    buffered = municipal.buffer(BUFFER_METRES)

    municipal_mask = geometry_mask(
        [mapping(municipal)],
        out_shape=(src.height, src.width),
        transform=src.transform,
        invert=True,
        all_touched=False,
    )

    buffer_mask = geometry_mask(
        [mapping(buffered)],
        out_shape=(src.height, src.width),
        transform=src.transform,
        invert=True,
        all_touched=False,
    )

    elevation = src.read(1)
    valid = np.isfinite(elevation) & (elevation != src.nodata)

    def report(name, area_mask):
        expected = int(area_mask.sum())
        available = int((area_mask & valid).sum())
        missing = expected - available
        coverage = available / expected * 100 if expected else 0

        print(f"\n{name}")
        print("-" * 45)
        print("Expected pixels:", expected)
        print("Valid pixels:", available)
        print("Missing pixels:", missing)
        print("Coverage:", round(coverage, 4), "%")

        return area_mask & ~valid

    print("DEM:", DEM_FILE)
    print("Dimensions:", src.width, "x", src.height)
    print("Resolution:", src.res)
    print("CRS:", src.crs)

    municipal_missing = report("MUNICIPAL BOUNDARY", municipal_mask)
    buffer_missing = report("10 KM BUFFER", buffer_mask)

    print("\nBUFFER GEOMETRY")
    print("-" * 45)
    print("Buffer area:", round(buffered.area / 1_000_000, 3), "km²")
    print("Municipal area:", round(municipal.area / 1_000_000, 3), "km²")

    print("\nMISSING-PIXEL COMPONENTS INSIDE BUFFER")
    print("-" * 45)

    labels, count = ndimage.label(buffer_missing)
    components = []

    for component_id in range(1, count + 1):
        rows, cols = np.where(labels == component_id)
        pixels = len(rows)

        if pixels < 5:
            continue

        components.append({
            "pixels": pixels,
            "area_km2": pixels * abs(src.res[0] * src.res[1]) / 1_000_000,
            "min_row": int(rows.min()),
            "max_row": int(rows.max()),
            "min_col": int(cols.min()),
            "max_col": int(cols.max()),
        })

    components.sort(key=lambda item: item["pixels"], reverse=True)

    print("Total components:", count)
    print("Components with at least 5 pixels:", len(components))

    for item in components[:15]:
        print(item)

    if components:
        import pandas as pd
        output = ROOT / "data/processed/hydrology/complete_dem_nodata_components.csv"
        pd.DataFrame(components).to_csv(output, index=False)
        print("\nComponent report saved:", output)

    print("\nFINAL CHECK")
    print("-" * 45)
    print(
        "Municipal coverage:",
        "PASS" if not municipal_missing.any() else "INVESTIGATION REQUIRED"
    )
    print(
        "Buffer coverage:",
        "PASS" if not buffer_missing.any() else "GAPS REMAIN"
    )
