from datetime import date
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAINFALL_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "rainfall"
    / "nasa_imerg_ballari_2024.csv"
)


def load_rainfall_data() -> pd.DataFrame:
    """Load and validate the prepared NASA IMERG daily rainfall dataset."""
    if not RAINFALL_FILE.exists():
        raise FileNotFoundError(
            f"Rainfall dataset not found: {RAINFALL_FILE}"
        )

    df = pd.read_csv(RAINFALL_FILE)

    required = {
        "date",
        "latitude",
        "longitude",
        "precipitation_mm_per_day",
        "valid_half_hourly_retrievals",
        "status",
    }
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Rainfall dataset is missing columns: {sorted(missing)}"
        )

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["precipitation_mm_per_day"] = pd.to_numeric(
        df["precipitation_mm_per_day"], errors="coerce"
    )

    df = df.dropna(subset=["date", "precipitation_mm_per_day"]).copy()
    df = df.sort_values("date")

    if df.empty:
        raise ValueError("Rainfall dataset contains no valid observations.")

    if (df["precipitation_mm_per_day"] < 0).any():
        raise ValueError("Rainfall dataset contains negative precipitation.")

    return df


def get_rainfall_data(
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """Return rainfall records and descriptive statistics for a date range."""
    df = load_rainfall_data()

    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date must be on or before end_date.")

    if start_date:
        df = df[df["date"].dt.date >= start_date]

    if end_date:
        df = df[df["date"].dt.date <= end_date]

    if df.empty:
        return {
            "source": "NASA GPM IMERG",
            "dataset": RAINFALL_FILE.name,
            "unit": "mm/day",
            "measurement_note": (
                "Values are daily mean precipitation rates in mm/day, "
                "not necessarily daily accumulated rainfall totals."
            ),
            "grid_point": None,
            "record_count": 0,
            "start_date": None,
            "end_date": None,
            "statistics": None,
            "records": [],
        }

    values = df["precipitation_mm_per_day"]

    first = df.iloc[0]
    grid_point = {
        "latitude": float(first["latitude"]),
        "longitude": float(first["longitude"]),
    }

    records = []
    for _, row in df.iterrows():
        records.append(
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "precipitation_mm_per_day": round(
                    float(row["precipitation_mm_per_day"]), 3
                ),
                "valid_half_hourly_retrievals": int(
                    row["valid_half_hourly_retrievals"]
                ),
                "status": str(row["status"]),
            }
        )

    return {
        "source": "NASA GPM IMERG",
        "dataset": RAINFALL_FILE.name,
        "unit": "mm/day",
        "measurement_note": (
            "Values are daily mean precipitation rates in mm/day, "
            "not necessarily daily accumulated rainfall totals."
        ),
        "grid_point": grid_point,
        "record_count": int(len(df)),
        "start_date": df["date"].min().strftime("%Y-%m-%d"),
        "end_date": df["date"].max().strftime("%Y-%m-%d"),
        "statistics": {
            "mean": round(float(values.mean()), 3),
            "maximum": round(float(values.max()), 3),
            "minimum": round(float(values.min()), 3),
            "days_above_zero": int((values > 0).sum()),
            "days_at_zero": int((values == 0).sum()),
        },
        "records": records,
    }

def get_rainfall_quality() -> dict:
    """Summarize data-quality indicators for the complete rainfall CSV."""
    if not RAINFALL_FILE.exists():
        raise FileNotFoundError(
            f"Rainfall dataset not found: {RAINFALL_FILE}"
        )

    df = pd.read_csv(RAINFALL_FILE)

    required = {
        "date",
        "latitude",
        "longitude",
        "precipitation_mm_per_day",
        "valid_half_hourly_retrievals",
        "status",
    }
    missing_columns = sorted(required - set(df.columns))

    if missing_columns:
        raise ValueError(
            f"Rainfall dataset is missing columns: {missing_columns}"
        )

    parsed_dates = pd.to_datetime(df["date"], errors="coerce")
    rainfall = pd.to_numeric(
        df["precipitation_mm_per_day"], errors="coerce"
    )
    retrievals = pd.to_numeric(
        df["valid_half_hourly_retrievals"], errors="coerce"
    )

    valid_dates = parsed_dates.dropna()
    missing_calendar_dates = 0

    if not valid_dates.empty:
        expected_dates = pd.date_range(
            valid_dates.min().normalize(),
            valid_dates.max().normalize(),
            freq="D",
        )
        observed_dates = set(valid_dates.dt.normalize())
        missing_calendar_dates = len(
            set(expected_dates) - observed_dates
        )

    coordinates = df[["latitude", "longitude"]].drop_duplicates()

    return {
        "source": "NASA GPM IMERG",
        "dataset": RAINFALL_FILE.name,
        "scope": "Complete rainfall CSV; not date-filtered",
        "units": "mm/day",
        "grid_point_count": int(len(coordinates)),
        "grid_point_note": (
            "A single grid point does not represent complete "
            "citywide rainfall coverage."
        ),
        "row_count": int(len(df)),
        "invalid_dates": int(parsed_dates.isna().sum()),
        "duplicate_date_rows": int(
            parsed_dates.dropna().duplicated().sum()
        ),
        "missing_calendar_dates": int(missing_calendar_dates),
        "invalid_rainfall_values": int(rainfall.isna().sum()),
        "negative_rainfall_values": int((rainfall < 0).sum()),
        "invalid_retrieval_counts": int(
            retrievals.isna().sum()
            + ((retrievals % 1) != 0).sum()
            + (retrievals < 0).sum()
            + (retrievals > 48).sum()
        ),
        "retrieval_counts_other_than_48": int(
            (retrievals.notna() & (retrievals != 48)).sum()
        ),
        "statuses_other_than_ok": int(
            (
                df["status"].fillna("").astype(str).str.strip().str.lower()
                != "ok"
            ).sum()
        ),
        "interpretation": (
            "Quality checks describe the supplied file. They do not "
            "establish measurement accuracy or flood-prediction skill."
        ),
    }
