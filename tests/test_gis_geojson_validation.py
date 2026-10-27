import json

import pytest
from fastapi.testclient import TestClient

from backend.app.api import gis as gis_api
from backend.app.main import app

client = TestClient(app)


@pytest.mark.parametrize(
    ("route", "file_attribute", "payload"),
    [
        (
            "/api/v1/gis/boundary",
            "BOUNDARY_FILE",
            {"type": "FeatureCollection", "features": [None]},
        ),
        (
            "/api/v1/gis/boundary",
            "BOUNDARY_FILE",
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {},
                        "geometry": None,
                    }
                ],
            },
        ),
        (
            "/api/v1/gis/drainage",
            "DRAINAGE_FILE",
            {"type": "FeatureCollection", "features": [None]},
        ),
        (
            "/api/v1/gis/drainage",
            "DRAINAGE_FILE",
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {},
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [],
                        },
                    }
                ],
            },
        ),
    ],
)
def test_geojson_routes_reject_malformed_features(
    tmp_path, monkeypatch, route, file_attribute, payload
):
    path = tmp_path / "invalid.geojson"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(gis_api, file_attribute, path)

    response = client.get(route)

    assert response.status_code == 500


def test_geojson_routes_reject_invalid_json(tmp_path, monkeypatch):
    path = tmp_path / "invalid.geojson"
    path.write_text("{invalid json", encoding="utf-8")

    monkeypatch.setattr(gis_api, "BOUNDARY_FILE", path)
    response = client.get("/api/v1/gis/boundary")

    assert response.status_code == 500
    assert response.json()["detail"] == "Municipal boundary GeoJSON is invalid."
