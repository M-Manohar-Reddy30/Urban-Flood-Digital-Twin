import pandas as pd
import pytest

from backend.app.services import spatial_rainfall_service as service


@pytest.fixture
def spatial_files(tmp_path, monkeypatch):
    weights_path = tmp_path / "weights.csv"
    grid_path = tmp_path / "grid.csv"
    municipal_path = tmp_path / "municipal.csv"

    weights = pd.DataFrame({
        "grid_id": ["A", "B", "C", "D"],
        "latitude": [15.15, 15.15, 15.05, 15.05],
        "longitude": [76.95, 76.85, 76.95, 76.85],
        "intersection_area_km2": [50.0, 25.0, 10.0, 5.0],
        "centre_inside_boundary": [True, False, False, False],
        "area_weight": [0.50, 0.25, 0.15, 0.10],
        "boundary_area_km2": [90.0] * 4,
        "grid_resolution_degrees": [0.1] * 4,
    })

    grid_rows = []

    rainfall_values = [10.0, 20.0, 30.0, 40.0]

    for grid_id, lat, lon, area, weight, rainfall in zip(
        weights["grid_id"],
        weights["latitude"],
        weights["longitude"],
        weights["intersection_area_km2"],
        weights["area_weight"],
        rainfall_values,
    ):
        grid_rows.append({
            "date": "2024-01-01",
            "grid_id": grid_id,
            "latitude": lat,
            "longitude": lon,
            "precipitation_mm_per_day": rainfall,
            "valid_half_hourly_retrievals": 48,
            "intersection_area_km2": area,
            "area_weight": weight,
            "status": "ok",
            "source_file": "test.nc4",
        })

    grid = pd.DataFrame(grid_rows)

    municipal = pd.DataFrame([{
        "date": "2024-01-01",
        "precipitation_mm_per_day": 16.666667,
        "valid_grid_cells": 4,
        "total_grid_cells": 4,
        "valid_area_km2": 90.0,
        "municipal_area_km2": 90.0,
        "spatial_coverage_percent": 100.0,
        "status": "complete_coverage",
        "source": "NASA GPM IMERG Final Daily V07",
    }])

    weights.to_csv(weights_path, index=False)
    grid.to_csv(grid_path, index=False)
    municipal.to_csv(municipal_path, index=False)

    monkeypatch.setattr(service, "WEIGHTS_FILE", weights_path)
    monkeypatch.setattr(service, "GRID_FILE", grid_path)
    monkeypatch.setattr(service, "MUNICIPAL_FILE", municipal_path)

    return {
        "weights": weights_path,
        "grid": grid_path,
        "municipal": municipal_path,
    }


def test_valid_spatial_dataset_loads(spatial_files):
    grid = service.load_spatial_rainfall_data()

    assert len(grid) == 4
    assert grid["grid_id"].nunique() == 4


def test_valid_weights_load(spatial_files):
    weights = service.load_spatial_weights()

    assert len(weights) == 4
    assert weights["area_weight"].sum() == pytest.approx(1.0)


def test_duplicate_grid_observation_rejected(spatial_files):
    grid = pd.read_csv(spatial_files["grid"])
    grid = pd.concat([grid, grid.iloc[[0]]], ignore_index=True)
    grid.to_csv(spatial_files["grid"], index=False)

    with pytest.raises(ValueError, match="duplicate"):
        service.load_spatial_rainfall_data()


def test_missing_grid_cell_rejected(spatial_files):
    grid = pd.read_csv(spatial_files["grid"])
    grid = grid[grid["grid_id"] != "D"]
    grid.to_csv(spatial_files["grid"], index=False)

    with pytest.raises(ValueError, match="Grid dataset IDs do not match spatial weights"):
        service.load_spatial_rainfall_data()


def test_invalid_spatial_weights_rejected(spatial_files):
    weights = pd.read_csv(spatial_files["weights"])
    weights.loc[0, "area_weight"] = 0.90
    weights.to_csv(spatial_files["weights"], index=False)

    with pytest.raises(ValueError, match="sum to 1"):
        service.load_spatial_weights()


def test_negative_rainfall_rejected(spatial_files):
    grid = pd.read_csv(spatial_files["grid"])
    grid.loc[0, "precipitation_mm_per_day"] = -5
    grid.to_csv(spatial_files["grid"], index=False)

    with pytest.raises(ValueError, match="negative rainfall"):
        service.load_spatial_rainfall_data()


def test_incorrect_municipal_estimate_rejected(spatial_files):
    municipal = pd.read_csv(spatial_files["municipal"])
    municipal.loc[0, "precipitation_mm_per_day"] = 99
    municipal.to_csv(spatial_files["municipal"], index=False)

    with pytest.raises(ValueError, match="calculation mismatch"):
        service.load_municipal_rainfall_data()


def test_incomplete_municipal_coverage_rejected(spatial_files):
    municipal = pd.read_csv(spatial_files["municipal"])
    municipal.loc[0, "spatial_coverage_percent"] = 75
    municipal.to_csv(spatial_files["municipal"], index=False)

    with pytest.raises(ValueError, match="incomplete spatial coverage"):
        service.load_municipal_rainfall_data()


def test_date_filter_returns_correct_records(spatial_files):
    result = service.get_municipal_rainfall()

    assert result["record_count"] == 1
    assert result["records"][0]["date"] == "2024-01-01"
    assert result["records"][0]["precipitation_mm_per_day"] == pytest.approx(16.666667)
    assert len(result["records"][0]["grid_cells"]) == 4
