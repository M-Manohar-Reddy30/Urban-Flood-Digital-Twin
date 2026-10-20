from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = DATA / "processed" / "data_readiness_report.md"

FILES = {
    "NASA IMERG rainfall": DATA / "processed/rainfall/nasa_imerg_ballari_2024.csv",
    "Bellary station rainfall": DATA / "processed/rainfall/bellary_station_quality_review.csv",
    "Flood evidence inventory": DATA / "processed/flood_evidence_inventory.csv",
    "GIS features": DATA / "processed/ballari_gis_features.csv",
    "Land-cover statistics": DATA / "processed/ballari_landcover_statistics.csv",
    "Terrain statistics": DATA / "processed/ballari_terrain_statistics.csv",
}

RASTERS = {
    "Corrected DEM": DATA / "processed/dem/ballari_dem_utm43_corrected.tif",
    "Corrected slope": DATA / "processed/slope/ballari_slope_degrees_corrected.tif",
    "Aligned land cover": DATA / "processed/ballari_landcover_utm43_aligned.tif",
}


def csv_summary(path: Path) -> dict:
    df = pd.read_csv(path)
    return {
        "rows": len(df),
        "columns": len(df.columns),
        "missing_cells": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "column_names": list(df.columns),
    }


def raster_summary(path: Path) -> dict:
    with rasterio.open(path) as src:
        return {
            "crs": str(src.crs),
            "width": src.width,
            "height": src.height,
            "resolution": [abs(src.res[0]), abs(src.res[1])],
            "nodata": src.nodata,
            "valid_pixels": int(
                (~np.ma.getmaskarray(src.read(1, masked=True))).sum()
            ),
            "bounds": [
                src.bounds.left,
                src.bounds.bottom,
                src.bounds.right,
                src.bounds.top,
            ],
        }



def rainfall_quality_checks() -> dict:
    path = FILES["NASA IMERG rainfall"]
    df = pd.read_csv(path)

    required = {
        "date",
        "precipitation_mm_per_day",
        "valid_half_hourly_retrievals",
        "status",
    }
    missing_columns = sorted(required - set(df.columns))

    if missing_columns:
        return {"missing_columns": missing_columns}

    dates = pd.to_datetime(df["date"], errors="coerce")
    rainfall = pd.to_numeric(df["precipitation_mm_per_day"], errors="coerce")
    retrievals = pd.to_numeric(df["valid_half_hourly_retrievals"], errors="coerce")

    expected_dates = pd.date_range("2024-01-01", "2024-12-31", freq="D")
    observed_dates = pd.DatetimeIndex(dates.dropna().dt.normalize().unique())

    return {
        "missing_columns": [],
        "invalid_dates": int(dates.isna().sum()),
        "unique_dates": int(observed_dates.nunique()),
        "missing_calendar_days": int(len(expected_dates.difference(observed_dates))),
        "duplicate_dates": int(dates.dropna().dt.normalize().duplicated().sum()),
        "invalid_rainfall_values": int(rainfall.isna().sum()),
        "negative_rainfall_values": int((rainfall < 0).sum()),
        "invalid_retrieval_counts": int(retrievals.isna().sum()),
        "retrieval_counts_other_than_48": int((retrievals != 48).sum()),
        "statuses_other_than_ok": int((df["status"].astype(str) != "ok").sum()),
    }


def station_quality_checks() -> dict:
    path = FILES["Bellary station rainfall"]
    df = pd.read_csv(path)

    required = {"timestamp", "rainfall_mm", "quality_flag"}
    missing_columns = sorted(required - set(df.columns))

    if missing_columns:
        return {"missing_columns": missing_columns}

    timestamps = pd.to_datetime(df["timestamp"], errors="coerce")
    rainfall = pd.to_numeric(df["rainfall_mm"], errors="coerce")
    flags = df["quality_flag"].astype(str)

    return {
        "missing_columns": [],
        "invalid_timestamps": int(timestamps.isna().sum()),
        "duplicate_timestamps": int(timestamps.dropna().duplicated().sum()),
        "invalid_rainfall_values": int(rainfall.isna().sum()),
        "negative_rainfall_values": int((rainfall < 0).sum()),
        "high_value_review_flags": int(
            flags.eq("REVIEW_HIGH_VALUE_NOT_AUTOMATICALLY_INVALID").sum()
        ),
    }


def gis_quality_checks() -> dict:
    path = FILES["GIS features"]
    df = pd.read_csv(path)

    required = {
        "longitude",
        "latitude",
        "elevation_m",
        "slope_degrees",
        "landcover_class",
    }
    missing_columns = sorted(required - set(df.columns))

    if missing_columns:
        return {"missing_columns": missing_columns}

    result = {"missing_columns": [], "rows": len(df)}
    for column, lower, upper in [
        ("longitude", -180, 180),
        ("latitude", -90, 90),
    ]:
        values = pd.to_numeric(df[column], errors="coerce")
        result[f"invalid_{column}"] = int(
            (~values.between(lower, upper)).sum()
        )

    for column in ["elevation_m", "slope_degrees", "landcover_class"]:
        values = pd.to_numeric(df[column], errors="coerce")
        result[f"invalid_{column}"] = int(
            (~np.isfinite(values)).sum()
        )

    return result


def build_report() -> str:
    lines = [
        "# Ballari Urban Flood Digital Twin — Data Readiness Audit",
        "",
        "## Purpose and limitations",
        "",
        "This report inventories existing data for research and modelling readiness.",
        "It does not establish flood-prediction accuracy or validate an AI model.",
        "Missing flood reports must not be interpreted as confirmed no-flood events.",
        "",
        "## 1. CSV dataset inventory",
        "",
    ]

    for name, path in FILES.items():
        lines.extend([f"### {name}", ""])
        if not path.is_file():
            lines.extend([f"- Status: MISSING ({path.relative_to(ROOT)})", ""])
            continue

        summary = csv_summary(path)
        lines.extend([
            f"- File: `{path.relative_to(ROOT)}`",
            "- Status: present",
            f"- Rows: {summary['rows']:,}",
            f"- Columns: {summary['columns']}",
            f"- Missing cells: {summary['missing_cells']:,}",
            f"- Duplicate rows: {summary['duplicate_rows']:,}",
            f"- Fields: {', '.join(summary['column_names'])}",
            "",
        ])

    lines.extend([
        "## 2. Dataset-specific quality checks",
        "",
        "### NASA IMERG rainfall",
        "",
    ])

    rainfall_checks = rainfall_quality_checks()
    for key, value in rainfall_checks.items():
        lines.append(f"- {key.replace('_', ' ').capitalize()}: {value}")

    lines.extend([
        "",
        "### Bellary station rainfall",
        "",
    ])

    station_checks = station_quality_checks()
    for key, value in station_checks.items():
        lines.append(f"- {key.replace('_', ' ').capitalize()}: {value}")

    lines.extend([
        "- High-value review flags require assessment; they do not automatically",
        "  mean the observations are invalid.",
        "",
        "### GIS features",
        "",
    ])

    gis_checks = gis_quality_checks()
    for key, value in gis_checks.items():
        lines.append(f"- {key.replace('_', ' ').capitalize()}: {value}")

    lines.extend([
        "",
        "## 3. Raster metadata and alignment",
        "",
    ])

    raster_results = {}
    for name, path in RASTERS.items():
        lines.extend([f"### {name}", ""])
        if not path.is_file():
            lines.extend([f"- Status: MISSING ({path.relative_to(ROOT)})", ""])
            continue

        summary = raster_summary(path)
        raster_results[name] = summary
        lines.extend([
            f"- File: `{path.relative_to(ROOT)}`",
            "- Status: present",
            f"- CRS: {summary['crs']}",
            f"- Dimensions: {summary['width']} × {summary['height']} pixels",
            f"- Pixel size: {summary['resolution'][0]:.3f} × "
            f"{summary['resolution'][1]:.3f} map units",
            f"- NoData value: {summary['nodata']}",
            f"- Valid pixels: {summary['valid_pixels']:,}",
            "",
        ])

    lines.extend([
        "### Grid alignment check",
        "",
    ])

    if len(raster_results) == len(RASTERS):
        grids = list(raster_results.values())
        aligned = all(
            item["crs"] == grids[0]["crs"]
            and item["width"] == grids[0]["width"]
            and item["height"] == grids[0]["height"]
            and item["resolution"] == grids[0]["resolution"]
            and item["bounds"] == grids[0]["bounds"]
            for item in grids[1:]
        )
        lines.append(f"- CRS, dimensions, resolution and bounds match: **{aligned}**")
    else:
        lines.append("- Alignment status: INCOMPLETE; one or more rasters are missing.")

    lines.extend([
        "",
        "## 4. Flood-evidence readiness",
        "",
        "The inventory contains reported evidence, not automatically verified event labels.",
        "Incident coordinates and event details must be independently checked before",
        "records are used as spatial flood labels. Candidate landmark coordinates are",
        "not incident coordinates. Vulnerable-village population figures are not",
        "flood-affected population counts.",
        "",
    ])

    evidence_path = FILES["Flood evidence inventory"]
    if evidence_path.is_file():
        evidence = pd.read_csv(evidence_path)
        lines.append(f"- Inventory records: {len(evidence)}")

        if "latitude" in evidence.columns and "longitude" in evidence.columns:
            valid_coordinates = (
                pd.to_numeric(evidence["latitude"], errors="coerce").notna()
                & pd.to_numeric(evidence["longitude"], errors="coerce").notna()
            )
            lines.append(
                f"- Records with incident latitude and longitude: "
                f"{int(valid_coordinates.sum())}"
            )
        else:
            lines.append("- Incident-coordinate fields: missing")

        if "verification_status" in evidence.columns:
            counts = evidence["verification_status"].fillna("missing").value_counts()
            lines.append("- Verification status counts:")
            for status, count in counts.items():
                lines.append(f"  - `{status}`: {count}")

    lines.extend([
        "",
        "## 5. Modelling readiness decisions",
        "",
        "| Component | Current decision | Reason |",
        "|---|---|---|",
        "| Rainfall | Suitable for descriptive analysis | "
        "Sources have different spatial and temporal coverage |",
        "| Terrain and land cover | Suitable as candidate GIS features | "
        "Alignment does not establish physical accuracy or flood labels |",
        "| Historical flood evidence | Not ready for supervised spatial labels | "
        "Incident coordinates and independent verification are incomplete |",
        "| Infrastructure and drainage | Availability not established by this report | "
        "Dedicated source datasets must be identified and assessed |",
        "| Flood/no-flood target | Not approved for training | "
        "No verified labels or valid negative-event sampling scheme established |",
        "| Predictive model validation | Not established | "
        "No validated model demonstrated by this audit |",
        "",
        "## 6. Important interpretation notes",
        "",
        "- The Bellary station is outside the municipal boundary and should be treated",
        "  as nearby rainfall context, not an in-city station.",
        "- NASA IMERG contains one grid point in the audited 2024 dataset.",
        "- The Copernicus DSM may include buildings and vegetation.",
        "- Different raster resolutions can produce different pixel and feature counts.",
        "- A passing data-quality check does not prove that a dataset is accurate or",
        "  suitable for every modelling purpose.",
        "",
        "## Reproducibility",
        "",
        "Generated by `scripts/build_data_readiness_report.py`.",
        "The report records the files available at generation time.",
        "",
    ])

    return "\n".join(lines)


def main() -> None:
    report = build_report()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nSaved report: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
