from pathlib import Path
import numpy as np
import rasterio
from scipy.ndimage import minimum_filter, maximum_filter

ROOT = Path(__file__).resolve().parents[1]
DEM = ROOT / "data/processed/hydrology/ballari_hydrology_dem_30m_complete.tif"

with rasterio.open(DEM) as src:
    elevation = src.read(1)
    valid = np.isfinite(elevation) & (elevation != src.nodata)

    # Require a complete valid 3x3 neighbourhood.
    valid_count = minimum_filter(
        valid.astype(np.uint8),
        size=3,
        mode="constant",
        cval=0
    )

    complete = valid_count == 1

    # Compare centre elevation with its eight neighbours.
    local_min = minimum_filter(
        np.where(valid, elevation, np.inf),
        size=3,
        mode="constant",
        cval=np.inf
    )

    local_max = maximum_filter(
        np.where(valid, elevation, -np.inf),
        size=3,
        mode="constant",
        cval=-np.inf
    )

    # A candidate sink is strictly lower than every neighbour.
    candidate_sinks = complete & (elevation < local_min + 1e-6)

    # Flat minima are included separately.
    flat_minima = complete & (elevation == local_min) & (local_max > elevation)

    print("DEM depression diagnostic")
    print("=" * 45)
    print("Valid DEM cells:", int(valid.sum()))
    print("Complete 3x3 neighbourhoods:", int(complete.sum()))
    print("Strict local-minimum candidates:", int(candidate_sinks.sum()))
    print("Local-minimum candidates including flats:", int(flat_minima.sum()))

    print("\nCandidate sink elevation statistics:")
    if candidate_sinks.any():
        values = elevation[candidate_sinks]
        print("Minimum:", round(float(values.min()), 2), "m")
        print("Median:", round(float(np.median(values)), 2), "m")
        print("Maximum:", round(float(values.max()), 2), "m")
    else:
        print("No strict local minima detected.")

    print("\nNOTE:")
    print("These are local-minimum candidates, not confirmed hydrological sinks.")
    print("No depression filling or elevation modification was performed.")
