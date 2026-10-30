"""Spatial rainfall services for the Ballari Urban Flood Digital Twin.

Uses four NASA GPM IMERG grid cells and their municipal-boundary
intersection areas to validate and report municipal rainfall estimates.
"""

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

GRID_FILE = (
    PROJECT_ROOT
    / "data/processed/rainfall/"
    "nasa_imerg_ballari_grid_2024.csv"
)

MUNICIPAL_FILE = (
    PROJECT_ROOT
    / "data/processed/rainfall/"
    "nasa_imerg_ballari_municipal_2024.csv"
)

WEIGHTS_FILE = (
    PROJECT_ROOT
    / "data/processed/rainfall/"
    "ballari_imerg_grid_weights.csv"
)

GRID_COLUMNS = {
    "date",
    "grid_id",
    "latitude",
    "longitude",
    "precipitation_mm_per_day",
    "valid_half_hourly_retrievals",
    "intersection_area_km2",
    "area_weight",
    "status",
    "source_file",
}

MUNICIPAL_COLUMNS = {
    "date",
    "precipitation_mm_per_day",
    "valid_grid_cells",
    "total_grid_cells",
    "valid_area_km2",
    "municipal_area_km2",
    "spatial_coverage_percent",
    "status",
    "source",
}

WEIGHT_COLUMNS = {
    "grid_id",
    "latitude",
    "longitude",
    "intersection_area_km2",
    "area_weight",
}


def _load_csv(path: Path, required_columns: set) -> pd.DataFrame:
    """Load a CSV and verify its required columns and non-empty content."""

    if not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {path}")

    df = pd.read_csv(path)

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"{path.name} is missing columns: {sorted(missing)}"
        )

    if df.empty:
        raise ValueError(f"{path.name} contains no records.")

    return df.copy()


def _parse_dates(df: pd.DataFrame, filename: str) -> pd.DataFrame:
    """Parse strict YYYY-MM-DD dates."""

    parsed = pd.to_datetime(
        df["date"],
        format="%Y-%m-%d",
        errors="coerce",
    )

    if parsed.isna().any():
        raise ValueError(f"{filename} contains invalid dates.")

    df["date"] = parsed

    if df["date"].duplicated().any():
        raise ValueError(f"{filename} contains duplicate dates.")

    return df


def _numeric_columns(
    df: pd.DataFrame,
    columns: list,
    filename: str,
) -> pd.DataFrame:
    """Convert numeric fields and reject missing or non-finite values."""

    for column in columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

        values = df[column].to_numpy(dtype=float)

        if not np.isfinite(values).all():
            raise ValueError(
                f"{filename} contains invalid {column} values."
            )

    return df


def load_spatial_weights() -> pd.DataFrame:
    """Load and validate the four municipal grid-cell weights."""

    df = _load_csv(WEIGHTS_FILE, WEIGHT_COLUMNS)

    if df["grid_id"].isna().any():
        raise ValueError("Spatial weights contain missing grid IDs.")

    df["grid_id"] = df["grid_id"].astype(str).str.strip()

    if (df["grid_id"] == "").any() or df["grid_id"].duplicated().any():
        raise ValueError("Spatial weights contain empty or duplicate IDs.")

    numeric = [
        "latitude",
        "longitude",
        "intersection_area_km2",
        "area_weight",
    ]

    df = _numeric_columns(df, numeric, WEIGHTS_FILE.name)

    if not df["latitude"].between(-90, 90).all():
        raise ValueError("Spatial weights contain invalid latitudes.")

    if not df["longitude"].between(-180, 180).all():
        raise ValueError("Spatial weights contain invalid longitudes.")

    if (df["intersection_area_km2"] <= 0).any():
        raise ValueError("Spatial intersection areas must be positive.")

    if (df["area_weight"] <= 0).any():
        raise ValueError("Spatial area weights must be positive.")

    if not np.isclose(df["area_weight"].sum(), 1.0, atol=1e-6):
        raise ValueError("Spatial area weights must sum to 1.")

    if len(df) != 4:
        raise ValueError(
            "Expected exactly four IMERG grid cells for Ballari."
        )

    df = df.sort_values("grid_id").reset_index(drop=True)

    return df


def load_spatial_rainfall_data() -> pd.DataFrame:
    """Load and validate all daily observations for the four grid cells."""

    df = _load_csv(GRID_FILE, GRID_COLUMNS)

    df["grid_id"] = df["grid_id"].astype("string").str.strip()

    if df["grid_id"].isna().any() or (df["grid_id"] == "").any():
        raise ValueError("Grid dataset contains missing grid IDs.")

    parsed = pd.to_datetime(
        df["date"],
        format="%Y-%m-%d",
        errors="coerce",
    )

    if parsed.isna().any():
        raise ValueError("Grid dataset contains invalid dates.")

    df["date"] = parsed

    if df.duplicated(["date", "grid_id"]).any():
        raise ValueError("Grid dataset contains duplicate date/grid pairs.")

    numeric = [
        "latitude",
        "longitude",
        "precipitation_mm_per_day",
        "valid_half_hourly_retrievals",
        "intersection_area_km2",
        "area_weight",
    ]

    df = _numeric_columns(df, numeric, GRID_FILE.name)

    if not df["latitude"].between(-90, 90).all():
        raise ValueError("Grid dataset contains invalid latitudes.")

    if not df["longitude"].between(-180, 180).all():
        raise ValueError("Grid dataset contains invalid longitudes.")

    if (df["precipitation_mm_per_day"] < 0).any():
        raise ValueError("Grid dataset contains negative rainfall.")

    retrievals = df["valid_half_hourly_retrievals"]

    if (
        (retrievals % 1 != 0).any()
        or (retrievals < 1).any()
        or (retrievals > 48).any()
    ):
        raise ValueError("Grid dataset contains invalid retrieval counts.")

    statuses = df["status"].astype("string").str.strip().str.lower()

    if statuses.isna().any() or (statuses != "ok").any():
        raise ValueError(
            "Grid dataset contains observations that are not successful."
        )

    df["status"] = statuses

    weights = load_spatial_weights()

    expected_ids = set(weights["grid_id"])
    actual_ids = set(df["grid_id"])

    if actual_ids != expected_ids:
        raise ValueError("Grid dataset IDs do not match spatial weights.")

    for _, cell in weights.iterrows():
        subset = df[df["grid_id"] == cell["grid_id"]]

        if not np.isclose(
            subset["latitude"], cell["latitude"], atol=1e-6
        ).all():
            raise ValueError(
                f"Latitude mismatch for {cell['grid_id']}."
            )

        if not np.isclose(
            subset["longitude"], cell["longitude"], atol=1e-6
        ).all():
            raise ValueError(
                f"Longitude mismatch for {cell['grid_id']}."
            )

        if not np.isclose(
            subset["intersection_area_km2"],
            cell["intersection_area_km2"],
            atol=1e-6,
        ).all():
            raise ValueError(
                f"Intersection-area mismatch for {cell['grid_id']}."
            )

        if not np.isclose(
            subset["area_weight"],
            cell["area_weight"],
            atol=1e-6,
        ).all():
            raise ValueError(
                f"Area-weight mismatch for {cell['grid_id']}."
            )

    daily_counts = df.groupby("date")["grid_id"].agg(
        ["count", "nunique"]
    )

    if (
        (daily_counts["count"] != len(expected_ids)).any()
        or (daily_counts["nunique"] != len(expected_ids)).any()
    ):
        raise ValueError(
            "Every date must contain exactly one observation per grid cell."
        )

    df = df.sort_values(["date", "grid_id"]).reset_index(drop=True)

    return df


def load_municipal_rainfall_data() -> pd.DataFrame:
    """Validate municipal estimates against the four-cell source data."""

    municipal = _load_csv(MUNICIPAL_FILE, MUNICIPAL_COLUMNS)

    parsed = pd.to_datetime(
        municipal["date"],
        format="%Y-%m-%d",
        errors="coerce",
    )

    if parsed.isna().any():
        raise ValueError("Municipal dataset contains invalid dates.")

    municipal["date"] = parsed

    if municipal["date"].duplicated().any():
        raise ValueError("Municipal dataset contains duplicate dates.")

    numeric = [
        "precipitation_mm_per_day",
        "valid_grid_cells",
        "total_grid_cells",
        "valid_area_km2",
        "municipal_area_km2",
        "spatial_coverage_percent",
    ]

    municipal = _numeric_columns(
        municipal, numeric, MUNICIPAL_FILE.name
    )

    if (municipal["precipitation_mm_per_day"] < 0).any():
        raise ValueError("Municipal dataset contains negative rainfall.")

    if (
        (municipal["valid_grid_cells"] != 4).any()
        or (municipal["total_grid_cells"] != 4).any()
    ):
        raise ValueError("Municipal dataset has incomplete grid-cell counts.")

    if not np.isclose(
        municipal["spatial_coverage_percent"], 100.0, atol=1e-6
    ).all():
        raise ValueError("Municipal dataset has incomplete spatial coverage.")

    statuses = (
        municipal["status"].astype("string").str.strip().str.lower()
    )

    if statuses.isna().any() or (statuses != "complete_coverage").any():
        raise ValueError("Municipal dataset has invalid coverage statuses.")

    municipal["status"] = statuses

    grid = load_spatial_rainfall_data()

    grid_dates = set(grid["date"])
    municipal_dates = set(municipal["date"])

    if grid_dates != municipal_dates:
        raise ValueError(
            "Grid and municipal datasets have different date coverage."
        )

    weights = load_spatial_weights()
    total_area = float(weights["intersection_area_km2"].sum())

    grouped = grid.groupby("date")

    for _, row in municipal.iterrows():
        day_grid = grouped.get_group(row["date"])

        expected_rainfall = (
            day_grid["precipitation_mm_per_day"]
            * day_grid["intersection_area_km2"]
        ).sum() / total_area

        if not np.isclose(
            expected_rainfall,
            row["precipitation_mm_per_day"],
            rtol=0,
            atol=1e-6,
        ):
            raise ValueError(
                f"Municipal rainfall calculation mismatch on "
                f"{row['date'].date()}."
            )

    return municipal.sort_values("date").reset_index(drop=True)


def get_municipal_rainfall(
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """Return area-weighted municipal rainfall and contributing grid cells."""

    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date must be on or before end_date.")

    municipal = load_municipal_rainfall_data()
    grid = load_spatial_rainfall_data()
    weights = load_spatial_weights()

    if start_date:
        municipal = municipal[
            municipal["date"].dt.date >= start_date
        ]

    if end_date:
        municipal = municipal[
            municipal["date"].dt.date <= end_date
        ]

    if municipal.empty:
        return {
            "source": "NASA GPM IMERG Final Daily V07",
            "dataset": MUNICIPAL_FILE.name,
            "unit": "mm/day",
            "measurement_note": (
                "Area-weighted daily mean precipitation rate over "
                "the municipal boundary, not necessarily accumulated "
                "daily rainfall."
            ),
            "spatial_resolution_degrees": 0.1,
            "grid_cell_count": len(weights),
            "record_count": 0,
            "start_date": None,
            "end_date": None,
            "statistics": None,
            "records": [],
        }

    selected_dates = set(municipal["date"])
    selected_grid = grid[grid["date"].isin(selected_dates)]

    records = []

    for _, row in municipal.iterrows():
        day_grid = selected_grid[
            selected_grid["date"] == row["date"]
        ]

        cells = []

        for _, cell in day_grid.iterrows():
            cells.append({
                "grid_id": str(cell["grid_id"]),
                "latitude": float(cell["latitude"]),
                "longitude": float(cell["longitude"]),
                "precipitation_mm_per_day": round(
                    float(cell["precipitation_mm_per_day"]), 6
                ),
                "valid_half_hourly_retrievals": int(
                    cell["valid_half_hourly_retrievals"]
                ),
                "intersection_area_km2": round(
                    float(cell["intersection_area_km2"]), 6
                ),
                "area_weight": round(float(cell["area_weight"]), 6),
                "status": str(cell["status"]),
            })

        records.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "precipitation_mm_per_day": round(
                float(row["precipitation_mm_per_day"]), 6
            ),
            "valid_grid_cells": int(row["valid_grid_cells"]),
            "total_grid_cells": int(row["total_grid_cells"]),
            "valid_area_km2": round(float(row["valid_area_km2"]), 6),
            "municipal_area_km2": round(
                float(row["municipal_area_km2"]), 6
            ),
            "spatial_coverage_percent": round(
                float(row["spatial_coverage_percent"]), 4
            ),
            "status": str(row["status"]),
            "grid_cells": cells,
        })

    values = municipal["precipitation_mm_per_day"]

    return {
        "source": "NASA GPM IMERG Final Daily V07",
        "dataset": MUNICIPAL_FILE.name,
        "unit": "mm/day",
        "measurement_note": (
            "Area-weighted daily mean precipitation rate over "
            "the Ballari municipal boundary. It is not necessarily "
            "daily accumulated rainfall. IMERG has a 0.1-degree "
            "grid resolution and does not provide street-level rainfall."
        ),
        "spatial_resolution_degrees": 0.1,
        "grid_cell_count": len(weights),
        "record_count": int(len(municipal)),
        "start_date": municipal["date"].min().strftime("%Y-%m-%d"),
        "end_date": municipal["date"].max().strftime("%Y-%m-%d"),
        "statistics": {
            "mean": round(float(values.mean()), 6),
            "maximum": round(float(values.max()), 6),
            "minimum": round(float(values.min()), 6),
            "days_above_zero": int((values > 0).sum()),
            "days_at_zero": int((values == 0).sum()),
        },
        "records": records,
    }


def get_spatial_rainfall_quality() -> dict:
    """Return structural and spatial coverage indicators."""

    grid = load_spatial_rainfall_data()
    municipal = load_municipal_rainfall_data()
    weights = load_spatial_weights()

    daily_counts = grid.groupby("date")["grid_id"].nunique()

    return {
        "source": "NASA GPM IMERG Final Daily V07",
        "grid_dataset": GRID_FILE.name,
        "municipal_dataset": MUNICIPAL_FILE.name,
        "weights_dataset": WEIGHTS_FILE.name,
        "scope": "Complete 2024 spatial rainfall datasets",
        "unit": "mm/day",
        "date_count": int(municipal["date"].nunique()),
        "grid_observation_count": int(len(grid)),
        "municipal_record_count": int(len(municipal)),
        "grid_cell_count": int(grid["grid_id"].nunique()),
        "expected_grid_observations": int(
            municipal["date"].nunique() * len(weights)
        ),
        "dates_with_four_grid_cells": int(
            (daily_counts == len(weights)).sum()
        ),
        "duplicate_date_grid_pairs": int(
            grid.duplicated(["date", "grid_id"]).sum()
        ),
        "failed_grid_observations": int(
            (grid["status"] != "ok").sum()
        ),
        "retrieval_counts_other_than_48": int(
            (grid["valid_half_hourly_retrievals"] != 48).sum()
        ),
        "area_weight_sum": round(float(weights["area_weight"].sum()), 8),
        "municipal_area_km2": round(
            float(weights["intersection_area_km2"].sum()), 6
        ),
        "minimum_spatial_coverage_percent": round(
            float(municipal["spatial_coverage_percent"].min()), 4
        ),
        "maximum_spatial_coverage_percent": round(
            float(municipal["spatial_coverage_percent"].max()), 4
        ),
        "municipal_calculation_validation": "passed",
        "interpretation": (
            "These checks establish structural consistency and "
            "area-weighted calculation consistency. They do not establish "
            "satellite measurement accuracy, independent verification of "
            "every day, or flood-prediction skill. The four intersecting "
            "IMERG cells have 0.1-degree spatial resolution."
        ),
    }
