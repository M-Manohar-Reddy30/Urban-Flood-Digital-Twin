from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
source = next((ROOT / "data/raw/rainfall").glob("*.csv"))
output_dir = ROOT / "data/processed/rainfall"
output_dir.mkdir(parents=True, exist_ok=True)

columns = [
    "Station",
    "District",
    "Data Acquisition Time",
    "Telemetry Hourly Rainfall (mm)",
]

df = pd.read_csv(source, usecols=columns, low_memory=False)

df = df[
    (df["Station"].astype(str).str.strip() == "Bellary")
    & (
        df["District"].astype(str).str.strip().str.lower()
        .isin(["bellary", "ballari"])
    )
].copy()

df["timestamp"] = pd.to_datetime(
    df["Data Acquisition Time"],
    format="%d-%m-%Y %H:%M",
    errors="coerce",
)

df["rainfall_mm"] = pd.to_numeric(
    df["Telemetry Hourly Rainfall (mm)"],
    errors="coerce",
)

df = df.dropna(subset=["timestamp", "rainfall_mm"])
df = df.sort_values("timestamp")

duplicate_count = int(df["timestamp"].duplicated().sum())
negative_count = int((df["rainfall_mm"] < 0).sum())
high_count = int((df["rainfall_mm"] > 100).sum())

df["quality_flag"] = "REVIEW_NOT_REQUIRED_BY_THRESHOLD"
df.loc[df["rainfall_mm"] > 100, "quality_flag"] = (
    "REVIEW_HIGH_VALUE_NOT_AUTOMATICALLY_INVALID"
)

df.to_csv(output_dir / "bellary_station_quality_review.csv", index=False)

report = [
    "BELLARY STATION RAINFALL QUALITY REVIEW",
    "",
    f"Source file: {source.name}",
    f"Valid timestamp/value records: {len(df)}",
    f"First observation: {df['timestamp'].min()}",
    f"Last observation: {df['timestamp'].max()}",
    f"Duplicate timestamps: {duplicate_count}",
    f"Negative rainfall values: {negative_count}",
    f"Values above 100 mm: {high_count}",
    f"Minimum recorded value (mm): {df['rainfall_mm'].min()}",
    f"Median recorded value (mm): {df['rainfall_mm'].median()}",
    f"Maximum recorded value (mm): {df['rainfall_mm'].max()}",
    "",
    "CAUTION:",
    "Values above 100 mm are flagged for review, not declared invalid.",
    "Missing timestamps are not treated as zero rainfall.",
    "Measurement conventions and extreme values require source verification.",
    "This intermittent station series is not a continuous hourly time series.",
]

report_path = output_dir / "bellary_station_quality_report.txt"
report_path.write_text("\n".join(report) + "\n", encoding="utf-8")

print("\n".join(report))
print("\nSaved detailed records:", output_dir / "bellary_station_quality_review.csv")
print("Saved report:", report_path)
