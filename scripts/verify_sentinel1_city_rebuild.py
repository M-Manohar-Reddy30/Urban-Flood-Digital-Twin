"""Rebuild city radar arrays from source ZIPs and verify saved outputs."""

from pathlib import Path
import hashlib
import json
import math
import zipfile

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import Window, from_bounds, bounds
from shapely.geometry import mapping

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/flood_evidence/sentinel1_city_pair"
RAW = ROOT / "data/raw/flood_evidence/sentinel1_rtc"
BOUNDARY = ROOT / "data/processed/ballari_municipal_boundary_2d.geojson"
DATES = ("20260528", "20260609")
LAYERS = {
    "VV": "_VV.tif",
    "VH": "_VH.tif",
    "layover_shadow": "_ls_map.tif",
    "incidence_radians": "_inc_map.tif",
    "dem": "_dem.tif",
}


def checksum(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(manifest_path=None, writer=None):
    manifest_path = manifest_path or BASE / "provenance.json"
    metadata = json.loads(manifest_path.read_text())
    if checksum(BOUNDARY) != metadata["boundary_sha256"]:
        raise ValueError("Boundary checksum mismatch.")

    sources = {}
    members = {}
    for date in DATES:
        record = metadata["sources"][date]
        filename = record["filename"]
        if Path(filename).name != filename:
            raise ValueError("Expected a source filename without directories.")
        source = RAW / filename
        print(f"Checking source checksum: {date}", flush=True)
        if checksum(source) != record["sha256"]:
            raise ValueError(f"Source checksum mismatch: {date}")
        sources[date] = source
        with zipfile.ZipFile(source) as archive:
            names = archive.namelist()
        for layer, suffix in LAYERS.items():
            matches = [name for name in names if name.endswith(suffix)]
            if len(matches) != 1:
                raise ValueError(f"Expected one {suffix}: {date}")
            members[date, layer] = matches[0]

    def uri(date, layer):
        return (
            f"/vsizip/{sources[date].resolve().as_posix()}/"
            f"{members[date, layer]}"
        )

    boundary = gpd.read_file(BOUNDARY)
    if boundary.crs is None:
        raise ValueError("Missing boundary CRS.")
    geometry = boundary.to_crs("EPSG:32643").geometry.union_all()
    if geometry.is_empty or not geometry.is_valid:
        raise ValueError("Invalid boundary.")

    with rasterio.open(uri(DATES[0], "VV")) as src:
        if src.crs.to_epsg() != 32643 or src.res != (30.0, 30.0):
            raise ValueError("Unexpected reference CRS or pixel spacing.")
        raw = from_bounds(*geometry.bounds, transform=src.transform)
        c0, r0 = math.floor(raw.col_off), math.floor(raw.row_off)
        c1 = math.ceil(raw.col_off + raw.width)
        r1 = math.ceil(raw.row_off + raw.height)
        win = Window(c0, r0, c1-c0, r1-r0)
        extent = bounds(win, src.transform)
        transform = src.window_transform(win)
        crs = src.crs
        shape = (r1-r0, c1-c0)

    city = geometry_mask(
        [mapping(geometry)], out_shape=shape,
        transform=transform, invert=True, all_touched=False,
    )

    def compare(filename, expected):
        if writer is not None:
            writer(filename, expected, crs, transform)
            return
        with rasterio.open(BASE / filename) as saved:
            if (saved.crs, saved.transform, saved.shape) != (
                crs, transform, shape
            ):
                raise ValueError(f"Saved grid mismatch: {filename}")
            actual = saved.read(1)
        if not np.array_equal(actual, expected, equal_nan=True):
            raise ValueError(f"Saved pixel values differ: {filename}")

    masks = []
    for date in DATES:
        layers = {}
        print(f"Rebuilding city arrays: {date}", flush=True)
        for layer in LAYERS:
            with rasterio.open(uri(date, layer)) as src:
                raw = from_bounds(*extent, transform=src.transform)
                values = (raw.col_off, raw.row_off, raw.width, raw.height)
                if not np.allclose(
                    values, np.round(values), rtol=0, atol=1e-6
                ):
                    raise ValueError("Non-integer source grid offset.")
                win = Window(*(int(round(value)) for value in values))
                if (
                    win.col_off < 0 or win.row_off < 0
                    or win.col_off + win.width > src.width
                    or win.row_off + win.height > src.height
                ):
                    raise ValueError("City window exceeds source bounds.")
                if (
                    src.crs != crs
                    or not src.window_transform(win).almost_equals(transform)
                ):
                    raise ValueError("Source grid mismatch.")
                data = src.read(1, window=win, masked=True)

            values = data.data.astype("float32")
            valid = ~np.ma.getmaskarray(data) & np.isfinite(values)
            values[~valid | ~city] = np.nan
            layers[layer] = values
            compare(f"{date}_{layer}.tif", values)

        good = (
            city
            & np.isfinite(layers["VV"]) & (layers["VV"] > 0)
            & np.isfinite(layers["VH"]) & (layers["VH"] > 0)
            & (layers["layover_shadow"] == 1)
        )
        if int(good.sum()) != metadata["sources"][date]["usable_city_pixels"]:
            raise ValueError(f"Provenance count mismatch: {date}")
        masks.append(good)

    common = masks[0] & masks[1]
    compare("city_mask.tif", city.astype("uint8"))
    compare("common_usable_mask.tif", common.astype("uint8"))

    if (
        int(city.sum()) != metadata["city_pixels"]
        or int(common.sum()) != metadata["common_usable_pixels"]
    ):
        raise ValueError("Provenance city/common counts differ.")

    print("\nSource ZIP and boundary checksums: PASS")
    print("Ten city layers and two masks rebuilt: PASS")
    if writer is None:
        print("All rebuilt arrays match saved outputs: PASS")
    print(f"City pixels: {city.sum():,}")
    print(f"Common usable pixels: {common.sum():,}")
    print("Reproducibility verified; flood accuracy is not established.")
    if writer is None:
        print("No data files or models modified.")


if __name__ == "__main__":
    main()
