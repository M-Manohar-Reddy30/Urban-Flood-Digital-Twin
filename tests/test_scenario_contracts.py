"""Permanent regression checks for volume units and spatial API behaviour."""
import math

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api import spatial_scenarios as spatial
from backend.app.api.rainfall_scenarios import ScenarioInput, calculate_scenario

INPUTS = dict(rainfall_depth_mm=100, duration_hours=2, runoff_fraction=0.5)


def test_known_volume_and_water_balance():
    result = calculate_scenario(ScenarioInput(**INPUTS), 1)['results']
    assert result['rainfall_volume_m3'] == pytest.approx(90)
    assert result['estimated_runoff_volume_m3'] == pytest.approx(45)
    assert result['remaining_water_volume_m3'] == pytest.approx(45)
    assert result['average_rainfall_intensity_mm_per_hour'] == 50
    slower = calculate_scenario(ScenarioInput(**{**INPUTS, 'duration_hours': 4}), 1)['results']
    assert slower['estimated_runoff_volume_m3'] == result['estimated_runoff_volume_m3']
    assert slower['average_rainfall_intensity_mm_per_hour'] == 25


@pytest.mark.parametrize('field,value', [
    ('rainfall_depth_mm', -1), ('rainfall_depth_mm', 1001),
    ('duration_hours', 0), ('duration_hours', 1e-320), ('duration_hours', 169),
    ('runoff_fraction', -0.1), ('runoff_fraction', 1.1),
])
@pytest.mark.parametrize('endpoint', ['/rainfall', '/rainfall/spatial'])
def test_invalid_inputs_rejected_before_calculation(field, value, endpoint):
    with TestClient(app) as client:
        response = client.post('/api/v1/scenarios' + endpoint, json={**INPUTS, field: value})
    assert response.status_code == 422


@pytest.fixture
def samples(monkeypatch):
    frame = pd.DataFrame({
        'longitude': [76.9, 76.91, 76.92],
        'latitude': [15.1, 15.11, 15.12],
        'upstream_contributing_area_km2': [0.5, 1., 2.],
    })
    monkeypatch.setattr(spatial, 'load_dataset', lambda: (frame, None, None, None))
    return frame


def test_spatial_threshold_units_and_zero_runoff(samples):
    with TestClient(app) as client:
        response = client.post('/api/v1/scenarios/rainfall/spatial', json=INPUTS)
        assert response.status_code == 200
        result = response.json()
        assert result['metadata']['sample_count'] == 2
        assert [f['id'] for f in result['features']] == [1, 2]
        assert [f['properties']['estimated_upstream_runoff_volume_m3'] for f in result['features']] == [50000, 100000]
        for field in ['rainfall_depth_mm', 'runoff_fraction']:
            zero = client.post('/api/v1/scenarios/rainfall/spatial', json={**INPUTS, field: 0})
            assert zero.status_code == 200
            assert all(f['properties']['estimated_upstream_runoff_volume_m3'] == 0 for f in zero.json()['features'])


def test_real_dataset_spatial_consistency():
    with TestClient(app) as client:
        response = client.post('/api/v1/scenarios/rainfall/spatial', json=INPUTS)
    assert response.status_code == 200
    result = response.json()
    assert result['metadata']['sample_count'] == len(result['features']) == 1982
    for feature in result['features']:
        p = feature['properties']
        assert math.isclose(p['estimated_upstream_runoff_volume_m3'], p['upstream_contributing_area_km2'] * 50000)
