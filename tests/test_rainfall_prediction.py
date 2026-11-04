import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api import rainfall_prediction as prediction


@pytest.fixture(autouse=True)
def clear_model_cache():
    prediction.load_model.cache_clear()
    yield
    prediction.load_model.cache_clear()


def test_feature_order_and_month_encoding():
    request = prediction.PredictionInput(
        target_date="2003-01-01",
        previous_7_days_mm_per_day=[1, 2, 3, 4, 5, 6, 7],
    )
    frame = prediction.build_features(request)
    assert list(frame.columns) == prediction.FEATURES
    row = frame.iloc[0]
    assert row["lag_1"] == 7
    assert row["lag_7"] == 1
    assert row["previous_7day_mean"] == 4
    assert row["previous_7day_max"] == 7
    assert row["month_sin"] == pytest.approx(0)
    assert row["month_cos"] == pytest.approx(1)


def test_shipped_model_prediction():
    with TestClient(app) as client:
        response = client.post("/api/v1/rainfall/predict", json={
            "target_date": "2003-01-01",
            "previous_7_days_mm_per_day": [0] * 7,
        })
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["prediction_mm_per_day"] == pytest.approx(
        0.027252687747387115
    )
    assert result["status"] == "experimental_user_supplied_rainfall_estimate"


@pytest.mark.parametrize("history", [
    [], [0] * 6, [0] * 8,
    [-1, 0, 0, 0, 0, 0, 0],
    [1001, 0, 0, 0, 0, 0, 0],
])
def test_invalid_history_rejected(history):
    with TestClient(app) as client:
        response = client.post("/api/v1/rainfall/predict", json={
            "target_date": "2003-01-01",
            "previous_7_days_mm_per_day": history,
        })
    assert response.status_code == 422


def test_missing_model_returns_503(tmp_path, monkeypatch):
    monkeypatch.setattr(prediction, "ARTIFACTS", tmp_path)
    with TestClient(app) as client:
        response = client.post("/api/v1/rainfall/predict", json={
            "target_date": "2003-01-01",
            "previous_7_days_mm_per_day": [0] * 7,
        })
    assert response.status_code == 503


def test_nonfinite_model_output_rejected(monkeypatch):
    class BrokenModel:
        def predict(self, frame):
            return np.array([np.nan])

    def stub_loader():
        return BrokenModel()
    stub_loader.cache_clear = lambda: None
    monkeypatch.setattr(prediction, "load_model", stub_loader)

    with TestClient(app) as client:
        response = client.post("/api/v1/rainfall/predict", json={
            "target_date": "2003-01-01",
            "previous_7_days_mm_per_day": [0] * 7,
        })
    assert response.status_code == 500
