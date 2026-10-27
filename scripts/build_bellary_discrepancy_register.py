from pathlib import Path

import pandas as pd


SOURCE_PATH = Path(
    "data/raw/rainfall/18434c62-2ed5-4083-8060-cac00be166c9.csv"
)
NASA_PATH = Path(
    "data/processed/rainfall/nasa_imerg_ballari_2024.csv"
)
OUTPUT_PATH = Path(
    "data/processed/rainfall/bellary_high_value_discrepancy_register.csv"
)

HIGH_VALUE_THRESHOLD_MM = 100.0

REVIEW_STATUS = "UNVERIFIED_SOURCE_CONFIRMATION_REQUIRED"

REVIEW_REASON = (
    "Station value exceeds 100 mm; verify sensor measurement "
    "and accumulation convention with the data provider."
)


def build_discrepancy_register(
    source: pd.DataFrame,
    nasa: pd.DataFrame,
    threshold_mm: float = HIGH_VALUE_THRESHOLD_MM,
) -> pd.DataFrame:
    """Build a review register without changing or validating source readings."""

    required_columns = {
        "_id",
        "SlNo",
        "Station",
        "Agency",
        "District",
        "Latitude",
        "Longitude",
        "Data Acquisition Time",
        "Telemetry Hourly Rainfall (mm)",
    }

    missing = required_columns - set(source.columns)
    if missing:
        raise ValueError(
            f"Source dataset is missing required columns: {sorted(missing)}"
        )

    station = source.loc[
        source["Station"].astype(str).str.strip().str.casefold().eq("bellary")
        & source["District"].astype(str).str.strip().str.casefold().isin(
            ["bellary", "ballari"]
        )
    ].copy()

    station["timestamp"] = pd.to_datetime(
        station["Data Acquisition Time"],
        dayfirst=True,
        errors="coerce",
    )
    station["rainfall_mm"] = pd.to_numeric(
        station["Telemetry Hourly Rainfall (mm)"], errors="coerce"
    )

    station = station.dropna(subset=["timestamp", "rainfall_mm"])
    station = station.sort_values(["timestamp", "_id"]).copy()

    # This is the time since the previous recorded observation,
    # not proof of the sensor's rainfall accumulation period.
    station["gap_since_previous_hours"] = (
        station["timestamp"].diff().dt.total_seconds() / 3600
    )

    flagged = station.loc[
        station["rainfall_mm"] > threshold_mm
    ].copy()

    nasa_required = {"date", "precipitation_mm_per_day"}
    if not nasa_required.issubset(nasa.columns):
        raise ValueError(
            f"NASA dataset must contain columns: {sorted(nasa_required)}"
        )

    nasa_daily = nasa[["date", "precipitation_mm_per_day"]].copy()
    nasa_daily["date"] = pd.to_datetime(
        nasa_daily["date"], errors="coerce"
    ).dt.date

    flagged["date"] = flagged["timestamp"].dt.date
    flagged = flagged.merge(nasa_daily, on="date", how="left")

    flagged["review_status"] = REVIEW_STATUS
    flagged["review_reason"] = REVIEW_REASON
    flagged["nasa_comparison_note"] = (
        "Satellite daily estimate is contextual evidence, not ground truth."
    )

    columns = [
        "_id",
        "SlNo",
        "Station",
        "Agency",
        "District",
        "Latitude",
        "Longitude",
        "timestamp",
        "rainfall_mm",
        "gap_since_previous_hours",
        "precipitation_mm_per_day",
        "review_status",
        "review_reason",
        "nasa_comparison_note",
    ]

    return flagged[columns].reset_index(drop=True)


def main() -> None:
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(f"Source file not found: {SOURCE_PATH}")

    if not NASA_PATH.exists():
        raise FileNotFoundError(f"NASA comparison file not found: {NASA_PATH}")

    source = pd.read_csv(SOURCE_PATH)
    nasa = pd.read_csv(NASA_PATH)

    register = build_discrepancy_register(source, nasa)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    register.to_csv(OUTPUT_PATH, index=False)

    print(f"Register saved: {OUTPUT_PATH}")
    print(f"Flagged observations: {len(register)}")
    print(f"Unique source IDs: {register['_id'].nunique()}")
    print("Review statuses:")
    print(register["review_status"].value_counts().to_string())


if __name__ == "__main__":
    main()
