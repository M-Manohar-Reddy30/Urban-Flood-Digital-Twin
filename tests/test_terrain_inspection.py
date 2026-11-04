"""Exercise the shipped GIS data and reject locations outside its coverage."""
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.api.terrain_inspection import load_dataset


def test_cell_centre_returns_its_values():
    frame, _, _, _ = load_dataset()
    row = frame.iloc[len(frame) // 2]
    with TestClient(app) as client:
        response = client.get('/api/v1/gis/terrain-inspection', params={
            'latitude': row.latitude, 'longitude': row.longitude,
        })
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'provisional_environmental_features'
    assert data['cell_centre_distance_m'] < 0.01
    assert data['values']['elevation_m'] == row.elevation_m


def test_outside_and_invalid_coordinates():
    with TestClient(app) as client:
        assert client.get('/api/v1/gis/terrain-inspection', params={'latitude': 0, 'longitude': 0}).status_code == 404
        assert client.get('/api/v1/gis/terrain-inspection', params={'latitude': 91, 'longitude': 76.9}).status_code == 422
