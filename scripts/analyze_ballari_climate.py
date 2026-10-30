
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    ROOT
    / "data/processed/rainfall/nasa_imerg_ballari_municipal_2024.csv"
)

OUTPUT_DIR = ROOT / "data/processed/climate"

REQUIRED_COLUMNS = {
    "date",
    "precipitation_mm_per_day",
    "valid_grid_cells",
    "total_grid_cells",
    "spatial_coverage_percent",
    "status",
}

# Screening thresholds, not official meteorological warning categories.
HEAVY_RAINFALL_MM = 64.5
VERY_HEAVY_RAINFALL_MM = 115.5

# Meteorological seasons used for this initial analysis.
SEASONS = {
    "Winter": [12, 1, 2],
    "Pre-Monsoon": [3, 4, 5],
    "Southwest Monsoon": [6, 7, 8, 9],
    "Post-Monsoon": [10, 11],
}


def load_data():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input dataset not found: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["precipitation_mm_per_day"] = pd.to_numeric(
        df["precipitation_mm_per_day"], errors="coerce"
    )

    if df["date"].isna().any():
        raise ValueError("Dataset contains invalid dates.")

    rainfall = df["precipitation_mm_per_day"]

    if rainfall.isna().any() or not np.isfinite(rainfall).all():
        raise ValueError("Rainfall contains missing or non-finite values.")

    if (rainfall < 0).any():
        raise ValueError("Negative rainfall values detected.")

    if df["date"].duplicated().any():
        raise ValueError("Duplicate dates detected.")

    if not df["status"].eq("complete_coverage").all():
        raise ValueError("Incomplete spatial coverage detected.")

    if not df["spatial_coverage_percent"].eq(100.0).all():
        raise ValueError("Spatial coverage is not 100%.")

    if not df["valid_grid_cells"].eq(4).all():
        raise ValueError("Expected four valid grid cells per day.")

    df = df.sort_values("date").reset_index(drop=True)

    expected_dates = pd.date_range(
        start="2024-01-01",
        end="2024-12-31",
        freq="D",
    )

    if not df["date"].equals(pd.Series(expected_dates)):
        raise ValueError("Expected complete daily coverage for 2024.")

    return df


def calculate_daily_statistics(df):
    rainfall = df["precipitation_mm_per_day"]

    return pd.DataFrame(
        [{
            "record_count": len(df),
            "annual_rainfall_mm": rainfall.sum(),
            "mean_daily_rainfall_mm": rainfall.mean(),
            "median_daily_rainfall_mm": rainfall.median(),
            "maximum_daily_rainfall_mm": rainfall.max(),
            "minimum_daily_rainfall_mm": rainfall.min(),
            "standard_deviation_mm": rainfall.std(),
            "rainy_days_above_1mm": int((rainfall > 1).sum()),
            "rainy_days_above_10mm": int((rainfall > 10).sum()),
            "zero_rainfall_days": int((rainfall == 0).sum()),
        }]
    )


def calculate_monthly_analysis(df):
    working = df.set_index("date")

    rainfall = working["precipitation_mm_per_day"]

    monthly = pd.DataFrame({
        "total_rainfall_mm": rainfall.resample("ME").sum(),
        "mean_daily_rainfall_mm": rainfall.resample("ME").mean(),
        "maximum_daily_rainfall_mm": rainfall.resample("ME").max(),
        "observation_days": rainfall.resample("ME").count(),
        "rainy_days": rainfall.gt(1).resample("ME").sum(),
    })

    monthly["month"] = monthly.index.month
    monthly["month_name"] = monthly.index.strftime("%B")

    return monthly.reset_index(drop=True)


def calculate_seasonal_analysis(df):
    working = df.copy()
    working["month"] = working["date"].dt.month

    results = []

    for season, months in SEASONS.items():
        subset = working[working["month"].isin(months)]

        results.append({
            "season": season,
            "months": ",".join(map(str, months)),
            "total_rainfall_mm": subset[
                "precipitation_mm_per_day"
            ].sum(),
            "mean_daily_rainfall_mm": subset[
                "precipitation_mm_per_day"
            ].mean(),
            "maximum_daily_rainfall_mm": subset[
                "precipitation_mm_per_day"
            ].max(),
            "observation_days": len(subset),
        })

    return pd.DataFrame(results)


def detect_extreme_rainfall(df):
    extremes = df.loc[
        df["precipitation_mm_per_day"] >= HEAVY_RAINFALL_MM
    ].copy()

    def classify(value):
        if value >= VERY_HEAVY_RAINFALL_MM:
            return "Above very-heavy screening threshold"
        return "Heavy screening threshold"

    extremes["event_category"] = extremes[
        "precipitation_mm_per_day"
    ].apply(classify)

    extremes["threshold_note"] = (
        "Research screening threshold; not an official warning."
    )

    return extremes


def create_rainfall_anomaly_screening(df):
    """
    Descriptive screening relative to the 2024 daily distribution.

    This is NOT a climatological anomaly because a multi-year
    baseline is not available.
    """
    result = df[["date", "precipitation_mm_per_day"]].copy()

    mean = result["precipitation_mm_per_day"].mean()
    std = result["precipitation_mm_per_day"].std()

    if std == 0:
        result["standardized_deviation"] = 0.0
    else:
        result["standardized_deviation"] = (
            result["precipitation_mm_per_day"] - mean
        ) / std

    result["screening_flag"] = np.where(
        result["standardized_deviation"] >= 2,
        "Unusually high relative to 2024",
        "Within 2024 screening range",
    )

    result["baseline_note"] = (
        "Standardized against the same year's daily observations; "
        "not a climatological anomaly."
    )

    return result


def create_visualizations(monthly, seasonal, df):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(12, 5))
    plt.bar(monthly["month_name"], monthly["total_rainfall_mm"])
    plt.title("Ballari Monthly Rainfall - 2024")
    plt.xlabel("Month")
    plt.ylabel("Rainfall (mm)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "monthly_rainfall.png", dpi=200)
    plt.close()

    plt.figure(figsize=(10, 5))
    plt.bar(seasonal["season"], seasonal["total_rainfall_mm"])
    plt.title("Ballari Seasonal Rainfall - 2024")
    plt.xlabel("Season")
    plt.ylabel("Rainfall (mm)")
    plt.xticks(rotation=20)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "seasonal_rainfall.png", dpi=200)
    plt.close()

    plt.figure(figsize=(12, 5))
    plt.plot(
        df["date"],
        df["precipitation_mm_per_day"],
        linewidth=1,
    )
    plt.title("Ballari Daily Rainfall - 2024")
    plt.xlabel("Date")
    plt.ylabel("Rainfall (mm/day)")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "daily_rainfall.png", dpi=200)
    plt.close()


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading Ballari municipal rainfall dataset...")
    df = load_data()

    print("Calculating daily statistics...")
    daily = calculate_daily_statistics(df)

    print("Calculating monthly analysis...")
    monthly = calculate_monthly_analysis(df)

    print("Calculating seasonal analysis...")
    seasonal = calculate_seasonal_analysis(df)

    print("Detecting extreme rainfall...")
    extremes = detect_extreme_rainfall(df)

    print("Screening rainfall anomalies...")
    anomalies = create_rainfall_anomaly_screening(df)

    daily.to_csv(OUTPUT_DIR / "daily_statistics.csv", index=False)
    monthly.to_csv(OUTPUT_DIR / "monthly_analysis.csv", index=False)
    seasonal.to_csv(OUTPUT_DIR / "seasonal_analysis.csv", index=False)
    extremes.to_csv(OUTPUT_DIR / "extreme_rainfall_events.csv", index=False)
    anomalies.to_csv(OUTPUT_DIR / "rainfall_anomaly_screening.csv", index=False)

    create_visualizations(monthly, seasonal, df)

    print("\n" + "=" * 55)
    print("BALLARI CLIMATE ANALYTICS ENGINE")
    print("=" * 55)

    print("\nDAILY STATISTICS")
    print(daily.round(3).to_string(index=False))

    print("\nMONTHLY ANALYSIS")
    print(monthly.round(3).to_string(index=False))

    print("\nSEASONAL ANALYSIS")
    print(seasonal.round(3).to_string(index=False))

    print("\nEXTREME RAINFALL EVENTS")
    print(f"Events detected: {len(extremes)}")

    print("\nOUTPUT DIRECTORY")
    print(OUTPUT_DIR)

    print("\nAnalysis completed successfully.")


if __name__ == "__main__":
    main()
