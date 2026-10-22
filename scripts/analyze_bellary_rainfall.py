
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = ROOT / "data/raw/rainfall"
DEFAULT_OUTPUT_DIR = ROOT / "data/processed/rainfall"

COLUMNS = [
    "Station",
    "Agency",
    "Latitude",
    "Longitude",
    "District",
    "Data Acquisition Time",
    "Telemetry Hourly Rainfall (mm)",
]


def analyze_bellary_rainfall(
    source: Path,
    output_dir: Path,
) -> str:
    """Create a quality-review CSV and report for Bellary station rainfall."""
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(source, usecols=COLUMNS, low_memory=False)

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

    station_metadata = df[
        ["Station", "Agency", "Latitude", "Longitude"]
    ].drop_duplicates()

    flagged_records = df.loc[
        df["rainfall_mm"] > 100,
        ["timestamp", "rainfall_mm"],
    ]

    df["quality_flag"] = "REVIEW_NOT_REQUIRED_BY_THRESHOLD"
    df.loc[df["rainfall_mm"] > 100, "quality_flag"] = (
        "REVIEW_HIGH_VALUE_NOT_AUTOMATICALLY_INVALID"
    )

    csv_path = output_dir / "bellary_station_quality_review.csv"
    df.to_csv(csv_path, index=False)

    report = [
        "BELLARY STATION RAINFALL QUALITY REVIEW",
        "",
        f"Source file: {source.name}",
        f"Station metadata records: {len(station_metadata)}",
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

    if len(station_metadata) == 1:
        metadata = station_metadata.iloc[0]
        report.extend([
            f"Station: {metadata['Station']}",
            f"Agency: {metadata['Agency']}",
            f"Latitude: {metadata['Latitude']}",
            f"Longitude: {metadata['Longitude']}",
        ])
    else:
        report.append(
            "Station metadata: multiple combinations found; inspect source records."
        )

    report.extend([
        "",
        "HIGH-VALUE RECORDS REQUIRING REVIEW",
        "Rule: rainfall_mm > 100 mm.",
        "This threshold is a screening rule, not a confirmed error criterion.",
    ])

    for _, row in flagged_records.iterrows():
        report.append(f"{row['timestamp']}: {row['rainfall_mm']} mm")

    report_text = "\n".join(report) + "\n"
    report_path = output_dir / "bellary_station_quality_report.txt"
    report_path.write_text(report_text, encoding="utf-8")

    return report_text


def main() -> None:
    sources = sorted(DEFAULT_SOURCE_DIR.glob("*.csv"))

    if len(sources) != 1:
        raise RuntimeError(
            f"Expected exactly one rainfall source CSV in "
            f"{DEFAULT_SOURCE_DIR}, found {len(sources)}."
        )

    report_text = analyze_bellary_rainfall(
        source=sources[0],
        output_dir=DEFAULT_OUTPUT_DIR,
    )

    print(report_text)
    print(
        "\nSaved detailed records:",
        DEFAULT_OUTPUT_DIR / "bellary_station_quality_review.csv",
    )
    print(
        "Saved report:",
        DEFAULT_OUTPUT_DIR / "bellary_station_quality_report.txt",
    )


if __name__ == "__main__":
    main()
