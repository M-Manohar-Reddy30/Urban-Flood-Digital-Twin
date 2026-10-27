import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Polygon

from backend.app.services import gis_service


@pytest.fixture
def valid_gis_files(tmp_path, monkeypatch):
    data_dir = tmp_path / "processed"
    data_dir.mkdir()

    csv_path = data_dir / "ballari_gis_features.csv"
    boundary_path = data_dir / "ballari_municipal_boundary_2d.geojson"

    pd.DataFrame(
        {
            "longitude": [76.92, 76.93],
            "latitude": [15.15, 15.16],
            "easting_m": [700000.0, 701000.0],
            "northing_m": [1679000.0, 1680000.0],
            "elevation_m": [450.0, 455.0],
            "slope_degrees": [2.0, 5.0],
            "landcover_class": [30, 40],
        }
    ).to_csv(csv_path, index=False)

    boundary = gpd.GeoDataFrame(
        {"name": ["test boundary"]},
        geometry=[
            Polygon(
                [
                    (76.90, 15.10),
                    (76.95, 15.10),
                    (76.95, 15.20),
                    (76.90, 15.20),
                    (76.90, 15.10),
                ]
            )
        ],
        crs="EPSG:4326",
    )
    boundary.to_file(boundary_path, driver="GeoJSON")

    monkeypatch.setattr(gis_service, "DATA_DIR", data_dir)
    return csv_path


def test_valid_gis_dataset_loads(valid_gis_files):
    result = gis_service.get_gis_summary()

    assert result["city"] == "Ballari"
    assert result["feature_count"] == 2
    assert result["boundary_valid"] is True


@pytest.mark.parametrize(
    ("column", "bad_value", "message"),
    [
        ("longitude", 181, "longitude"),
        ("latitude", 91, "latitude"),
        ("elevation_m", float("nan"), "elevation"),
        ("elevation_m", float("inf"), "elevation"),
        ("slope_degrees", -1, "slope"),
        ("slope_degrees", 91, "slope"),
        ("landcover_class", float("nan"), "landcover"),
    ],
)
def test_invalid_gis_values_are_rejected(
    valid_gis_files, column, bad_value, message
):
    df = pd.read_csv(valid_gis_files)
    df.loc[0, column] = bad_value
    df.to_csv(valid_gis_files, index=False)

    with pytest.raises(ValueError, match=message):
        gis_service.get_gis_summary()


def test_missing_required_gis_column_is_rejected(valid_gis_files):
    df = pd.read_csv(valid_gis_files).drop(columns=["latitude"])
    df.to_csv(valid_gis_files, index=False)

    with pytest.raises(ValueError, match="latitude"):
        gis_service.get_gis_summary()


def test_empty_gis_dataset_is_rejected(valid_gis_files):
    df = pd.read_csv(valid_gis_files).iloc[0:0]
    df.to_csv(valid_gis_files, index=False)

    with pytest.raises(ValueError, match="empty"):
        gis_service.get_gis_summary()
