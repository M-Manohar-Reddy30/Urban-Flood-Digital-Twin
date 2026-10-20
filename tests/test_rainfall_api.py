from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_rainfall_summary_returns_daily_records():
    response = client.get("/api/v1/rainfall/summary")

    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "NASA GPM IMERG"
    assert data["unit"] == "mm/day"
    assert data["record_count"] > 0
    assert len(data["records"]) == data["record_count"]
    assert data["statistics"]["minimum"] >= 0
    assert data["grid_point"]["latitude"] == 15.15


def test_rainfall_date_filter():
    response = client.get(
        "/api/v1/rainfall/summary",
        params={"start_date": "2024-01-01", "end_date": "2024-01-07"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["record_count"] == 7
    assert data["start_date"] == "2024-01-01"
    assert data["end_date"] == "2024-01-07"


def test_rainfall_rejects_reversed_dates():
    response = client.get(
        "/api/v1/rainfall/summary",
        params={"start_date": "2024-12-31", "end_date": "2024-01-01"},
    )

    assert response.status_code == 400


def test_rainfall_empty_date_range():
    response = client.get(
        "/api/v1/rainfall/summary",
        params={"start_date": "2025-01-01", "end_date": "2025-01-31"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["record_count"] == 0
    assert data["records"] == []
    assert data["statistics"] is None
