from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_gis_summary():
    response = client.get("/api/v1/gis/summary")
    assert response.status_code == 200

    data = response.json()
    assert data["city"] == "Ballari"
    assert data["feature_count"] == 95246
    assert data["coordinate_reference_system"] == "EPSG:4326"
    assert "not validated flood predictions" in data["note"]


def test_flood_evidence_summary():
    response = client.get("/api/v1/evidence/summary")
    assert response.status_code == 200

    data = response.json()
    assert data["total_records"] == 9


def test_gis_boundary():
    response = client.get("/api/v1/gis/boundary")
    assert response.status_code == 200

    boundary = response.json()
    assert boundary["type"] in {"Feature", "FeatureCollection"}
