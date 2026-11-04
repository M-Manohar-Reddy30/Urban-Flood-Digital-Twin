from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api import scenario_history as history
from backend.app.api.rainfall_scenarios import calculate_scenario


def test_saved_comparison_survives_new_client(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "scenarios.db")
    monkeypatch.setattr(
        history, "rainfall_scenario",
        lambda request: calculate_scenario(request, 1),
    )
    body = {
        "name": "Review demonstration",
        "scenario_a": {
            "rainfall_depth_mm": 50, "duration_hours": 2,
            "runoff_fraction": 0.5,
        },
        "scenario_b": {
            "rainfall_depth_mm": 100, "duration_hours": 2,
            "runoff_fraction": 0.5,
        },
    }

    with TestClient(app) as client:
        response = client.post("/api/v1/scenarios/saved", json=body)
        assert response.status_code == 201, response.text
        saved = response.json()
        assert saved["scenario_a"]["results"]["estimated_runoff_volume_m3"] == 22.5
        assert saved["scenario_b"]["results"]["estimated_runoff_volume_m3"] == 45

    # New client and database connections must retrieve the persisted record.
    with TestClient(app) as client:
        response = client.get("/api/v1/scenarios/saved/" + saved["id"])
        assert response.status_code == 200
        assert response.json() == saved

        listing = client.get("/api/v1/scenarios/saved")
        assert listing.status_code == 200
        assert listing.json()["records"][0]["id"] == saved["id"]

        assert client.get("/api/v1/scenarios/saved/missing").status_code == 404
        invalid = client.post(
            "/api/v1/scenarios/saved", json={**body, "name": "   "}
        )
        assert invalid.status_code == 422
        assert len(client.get("/api/v1/scenarios/saved").json()["records"]) == 1


def test_storage_failure_returns_503(tmp_path, monkeypatch):
    blocked = tmp_path / "not_a_directory"
    blocked.write_text("blocked", encoding="utf-8")
    monkeypatch.setattr(history, "DB_PATH", blocked / "scenarios.db")
    with TestClient(app) as client:
        assert client.get("/api/v1/scenarios/saved").status_code == 503


def test_configured_storage_is_used(tmp_path, monkeypatch):
    configured = tmp_path / 'mounted' / 'history.db'
    fallback = tmp_path / 'fallback.db'
    monkeypatch.setenv('SCENARIO_DB_PATH', str(configured))
    monkeypatch.setattr(history, 'DB_PATH', fallback)
    with TestClient(app) as client:
        assert client.get('/api/v1/scenarios/saved').status_code == 200
    assert configured.is_file()
    assert not fallback.exists()
