from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_readiness_summary_returns_success():
    response = client.get("/api/v1/readiness/summary")

    assert response.status_code == 200


def test_readiness_summary_contains_expected_sections():
    response = client.get("/api/v1/readiness/summary")

    assert response.status_code == 200
    data = response.json()

    assert data["project"] == "Ballari Urban Flood Digital Twin"
    assert "datasets" in data
    assert "quality_checks" in data
    assert "rasters" in data
    assert "raster_alignment" in data
    assert "flood_evidence" in data
    assert "modelling_readiness" in data


def test_readiness_summary_reports_flood_evidence_cautiously():
    response = client.get("/api/v1/readiness/summary")

    assert response.status_code == 200
    data = response.json()

    evidence = data["flood_evidence"]

    assert evidence["record_count"] == 9
    assert evidence["incident_coordinate_records"] == 0
    assert evidence["supervised_spatial_labels_ready"] is False
    assert data["modelling_readiness"]["predictive_model_validation"] == (
        "Not established"
    )


def test_readiness_summary_reports_raster_alignment():
    response = client.get("/api/v1/readiness/summary")

    assert response.status_code == 200
    data = response.json()

    alignment = data["raster_alignment"]

    assert alignment["all_rasters_present"] is True
    assert alignment["crs_dimensions_resolution_aligned"] is True


def test_readiness_summary_includes_rainfall_verification_status():
    response = client.get("/api/v1/readiness/summary")

    assert response.status_code == 200
    data = response.json()
    verification = data["rainfall_verification"]

    assert verification["status"] == "present"
    assert verification["rows"] == 16
    assert verification["unique_source_ids"] == 16
    assert verification["readings_above_threshold"] == 16
    assert verification["unverified_count"] == 16
    assert verification["other_review_status_count"] == 0
    assert verification["missing_nasa_comparisons"] == 1
