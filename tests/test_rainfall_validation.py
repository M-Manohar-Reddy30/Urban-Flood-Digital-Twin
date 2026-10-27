import pandas as pd
import pytest

from backend.app.services import rainfall_service


@pytest.fixture
def valid_rainfall_csv(tmp_path, monkeypatch):
    path = tmp_path / "rainfall.csv"
    df = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02"],
            "latitude": [15.15, 15.15],
            "longitude": [76.92, 76.92],
            "precipitation_mm_per_day": [0.0, 12.5],
            "valid_half_hourly_retrievals": [48, 48],
            "status": ["ok", "ok"],
        }
    )
    df.to_csv(path, index=False)
    monkeypatch.setattr(rainfall_service, "RAINFALL_FILE", path)
    return path


def test_valid_dataset_loads_without_losing_records(valid_rainfall_csv):
    data = rainfall_service.load_rainfall_data()

    assert len(data) == 2
    assert data["precipitation_mm_per_day"].tolist() == [0.0, 12.5]


@pytest.mark.parametrize(
    ("column", "bad_value", "message"),
    [
        ("date", "not-a-date", "date"),
        ("precipitation_mm_per_day", "not-a-number", "precipitation"),
        ("precipitation_mm_per_day", "-1", "negative"),
        ("precipitation_mm_per_day", "inf", "finite"),
        ("latitude", "91", "latitude"),
        ("longitude", "181", "longitude"),
        ("valid_half_hourly_retrievals", "49", "retrieval"),
        ("valid_half_hourly_retrievals", "1.5", "retrieval"),
        ("status", "failed", "status"),
    ],
)
def test_invalid_observation_is_rejected(
    valid_rainfall_csv, column, bad_value, message
):
    df = pd.read_csv(valid_rainfall_csv, dtype=str)
    df.loc[0, column] = bad_value
    df.to_csv(valid_rainfall_csv, index=False)

    with pytest.raises(ValueError, match=message):
        rainfall_service.load_rainfall_data()


def test_missing_required_column_is_rejected(valid_rainfall_csv):
    df = pd.read_csv(valid_rainfall_csv)
    df = df.drop(columns=["latitude"])
    df.to_csv(valid_rainfall_csv, index=False)

    with pytest.raises(ValueError, match="latitude"):
        rainfall_service.load_rainfall_data()


def test_duplicate_dates_are_rejected(valid_rainfall_csv):
    df = pd.read_csv(valid_rainfall_csv)
    df.loc[1, "date"] = df.loc[0, "date"]
    df.to_csv(valid_rainfall_csv, index=False)

    with pytest.raises(ValueError, match="duplicate"):
        rainfall_service.load_rainfall_data()
