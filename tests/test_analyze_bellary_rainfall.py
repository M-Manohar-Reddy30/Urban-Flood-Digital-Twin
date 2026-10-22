
import pandas as pd

from scripts.analyze_bellary_rainfall import analyze_bellary_rainfall


def test_bellary_rainfall_review_and_report(tmp_path):
    source = tmp_path / "sample_rainfall.csv"
    output_dir = tmp_path / "output"

    pd.DataFrame(
        [
            {
                "Station": "Bellary",
                "Agency": "Karnataka",
                "Latitude": 15.1375,
                "Longitude": 76.85055556,
                "District": "Bellary",
                "Data Acquisition Time": "01-06-2024 10:00",
                "Telemetry Hourly Rainfall (mm)": 10.0,
            },
            {
                "Station": "Bellary",
                "Agency": "Karnataka",
                "Latitude": 15.1375,
                "Longitude": 76.85055556,
                "District": "Bellary",
                "Data Acquisition Time": "01-06-2024 11:00",
                "Telemetry Hourly Rainfall (mm)": 100.0,
            },
            {
                "Station": "Bellary",
                "Agency": "Karnataka",
                "Latitude": 15.1375,
                "Longitude": 76.85055556,
                "District": "Bellary",
                "Data Acquisition Time": "01-06-2024 12:00",
                "Telemetry Hourly Rainfall (mm)": 120.0,
            },
            {
                "Station": "OtherStation",
                "Agency": "Karnataka",
                "Latitude": 15.0,
                "Longitude": 77.0,
                "District": "Bellary",
                "Data Acquisition Time": "01-06-2024 13:00",
                "Telemetry Hourly Rainfall (mm)": 500.0,
            },
        ]
    ).to_csv(source, index=False)

    report = analyze_bellary_rainfall(source, output_dir)

    reviewed_csv = output_dir / "bellary_station_quality_review.csv"
    reviewed = pd.read_csv(reviewed_csv)

    assert len(reviewed) == 3
    assert reviewed["Station"].eq("Bellary").all()

    # The threshold is strictly greater than 100 mm.
    assert (
        reviewed["quality_flag"]
        == "REVIEW_HIGH_VALUE_NOT_AUTOMATICALLY_INVALID"
    ).sum() == 1

    # Values are retained; a review flag does not delete the observation.
    assert 120.0 in reviewed["rainfall_mm"].tolist()
    assert 100.0 in reviewed["rainfall_mm"].tolist()

    assert "Station metadata records: 1" in report
    assert "Agency: Karnataka" in report
    assert "Latitude: 15.1375" in report
    assert "Longitude: 76.85055556" in report

    assert "Values above 100 mm: 1" in report
    assert "2024-06-01 12:00:00: 120.0 mm" in report
    assert "not declared invalid" in report
    assert "not a confirmed error criterion" in report

    assert (output_dir / "bellary_station_quality_report.txt").exists()
