import pandas as pd
import pytest

from scripts.build_bellary_discrepancy_register import (
    REVIEW_STATUS,
    build_discrepancy_register,
)


def make_source():
    return pd.DataFrame(
        [
            {
                "_id": "101",
                "SlNo": 101,
                "Station": "Bellary",
                "Agency": "Karnataka",
                "District": "Ballari",
                "Latitude": 15.1375,
                "Longitude": 76.85055556,
                "Data Acquisition Time": "2024-06-09 09:00:00",
                "Telemetry Hourly Rainfall (mm)": 12.0,
            },
            {
                "_id": "102",
                "SlNo": 102,
                "Station": "Bellary",
                "Agency": "Karnataka",
                "District": "Ballari",
                "Latitude": 15.1375,
                "Longitude": 76.85055556,
                "Data Acquisition Time": "2024-06-09 10:00:00",
                "Telemetry Hourly Rainfall (mm)": 249.5,
            },
            {
                "_id": "103",
                "SlNo": 103,
                "Station": "Bellary",
                "Agency": "Karnataka",
                "District": "Ballari",
                "Latitude": 15.1375,
                "Longitude": 76.85055556,
                "Data Acquisition Time": "2024-06-09 11:00:00",
                "Telemetry Hourly Rainfall (mm)": 15.0,
            },
            {
                "_id": "104",
                "SlNo": 104,
                "Station": "Other Station",
                "Agency": "Karnataka",
                "District": "Ballari",
                "Latitude": 15.2,
                "Longitude": 76.9,
                "Data Acquisition Time": "2024-06-09 12:00:00",
                "Telemetry Hourly Rainfall (mm)": 300.0,
            },
        ]
    )


def make_nasa():
    return pd.DataFrame(
        [
            {
                "date": "2024-06-09",
                "precipitation_mm_per_day": 0.395,
            }
        ]
    )


def test_flags_high_values_without_marking_them_invalid():
    result = build_discrepancy_register(make_source(), make_nasa())

    assert len(result) == 1
    assert result.iloc[0]["_id"] == "102"
    assert result.iloc[0]["rainfall_mm"] == 249.5
    assert result.iloc[0]["review_status"] == REVIEW_STATUS


def test_preserves_source_reading_and_records_time_gap():
    result = build_discrepancy_register(make_source(), make_nasa())

    row = result.iloc[0]
    assert row["rainfall_mm"] == 249.5
    assert row["gap_since_previous_hours"] == 1.0


def test_missing_nasa_date_does_not_remove_observation():
    source = make_source()
    source.loc[
        source["_id"] == "102", "Data Acquisition Time"
    ] = "2025-02-02 12:00:00"

    result = build_discrepancy_register(source, make_nasa())

    assert len(result) == 1
    assert result.iloc[0]["_id"] == "102"
    assert pd.isna(result.iloc[0]["precipitation_mm_per_day"])
    assert result.iloc[0]["review_status"] == REVIEW_STATUS


def test_missing_required_source_column_raises_error():
    source = make_source().drop(columns=["Station"])

    with pytest.raises(ValueError, match="missing required columns"):
        build_discrepancy_register(source, make_nasa())
