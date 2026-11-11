"""Audit saved Ballari radar inputs and summarize changes by land cover."""

from pathlib import Path
import json

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/flood_evidence/sentinel1_city_pair"
LANDCOVER = ROOT / "data/processed/ballari_landcover_2021.tif"

CLASSES = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare/sparse vegetation",
    70: "Snow/ice",
    80: "Permanent water",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss/lichen",
}


def main():
    metadata = json.loads((BASE / "provenance.json").read_text())
    with rasterio.open(BASE / "common_usable_mask.tif") as src:
        reference = (src.crs, src.transform, src.shape)
        common_values = src.read(1)

    def read(name):
        with rasterio.open(BASE / name) as src:
            if (src.crs, src.transform, src.shape) != reference:
                raise ValueError(f"Grid mismatch: {name}")
            return src.read(1)

    city_values = read("city_mask.tif")
    for name, values in (
        ("city", city_values), ("common", common_values)
    ):
        if not np.isin(values, [0, 1]).all():
            raise ValueError(f"Unexpected values in {name} mask.")

    city = city_values == 1
    common = common_values == 1
    if not city.any() or not common.any() or np.any(common & ~city):
        raise ValueError("Invalid city/common mask relationship.")

    if (
        int(city.sum()) != metadata["city_pixels"]
        or int(common.sum()) != metadata["common_usable_pixels"]
    ):
        raise ValueError("Pixel counts disagree with provenance.")

    changes = {}
    for polarization in ("VV", "VH"):
        before = read(f"20260528_{polarization}.tif")
        after = read(f"20260609_{polarization}.tif")

        for values in (before, after):
            if not np.all(
                np.isfinite(values[common]) & (values[common] > 0)
            ):
                raise ValueError("Invalid radar values in common mask.")

        change = np.full(reference[2], np.nan, dtype="float64")
        change[common] = (
            10 * np.log10(after[common].astype("float64"))
            - 10 * np.log10(before[common].astype("float64"))
        )
        changes[polarization] = change
        print(
            f"{polarization}: median change "
            f"{np.median(change[common]):+.3f} dB; "
            f"increased {100 * np.mean(change[common] > 0):.2f}%"
        )

    landcover = np.zeros(reference[2], dtype="uint8")
    with rasterio.open(LANDCOVER) as src:
        if src.crs is None or src.count != 1:
            raise ValueError("Invalid land-cover metadata.")
        reproject(
            source=rasterio.band(src, 1),
            destination=landcover,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=src.nodata,
            dst_transform=reference[1],
            dst_crs=reference[0],
            dst_nodata=0,
            resampling=Resampling.nearest,
        )

    observed_codes = set(np.unique(landcover[common]).tolist())
    unknown = observed_codes - set(CLASSES) - {0}
    if unknown:
        raise ValueError(f"Unknown land-cover codes: {unknown}")

    print(f"\nCity pixels: {city.sum():,}")
    print(f"Common usable pixels: {common.sum():,}")
    print(f"Common coverage: {100 * common.sum() / city.sum():.2f}%")
    print(f"Common pixels without land cover: {(common & (landcover == 0)).sum()}")

    print("\n2021 land cover | Pixels | Median VV change | Median VH change")
    for code, label in CLASSES.items():
        selected = common & (landcover == code)
        if selected.any():
            vv = np.median(changes["VV"][selected])
            vh = np.median(changes["VH"][selected])
            print(f"{label} | {selected.sum():,} | {vv:+.3f} | {vh:+.3f}")

    print("\nChanges are June 9 minus May 28, in dB.")
    print("2021 land cover is historical context, not verified 2026 land use.")
    print("This audit does not verify the raw ZIP hashes or recreate terrain masks.")
    print("Results are exploratory radar changes, not flood labels.")
    print("No data files or models modified.")


if __name__ == "__main__":
    main()
