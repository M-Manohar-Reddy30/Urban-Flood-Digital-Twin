import geopandas as gpd
import pandas as pd
import pytest

from scripts.build_drainage_dataset import (
    BOUNDARY_FILE,
    OUTPUT_CSV,
    OUTPUT_GEOJSON,
    OUTPUT_REPORT,
    SOURCE_KML,
    main,
    read_source_network,
)


@pytest.fixture(scope="module")
def drainage_outputs():
    main()

    return {
        "audit": pd.read_csv(OUTPUT_CSV),
        "network": gpd.read_file(OUTPUT_GEOJSON),
        "boundary": gpd.read_file(BOUNDARY_FILE),
        "report": OUTPUT_REPORT.read_text(encoding="utf-8"),
    }


def test_required_source_files_exist():
    assert SOURCE_KML.exists()
    assert BOUNDARY_FILE.exists()


def test_source_records_and_ids_are_preserved():
    source = read_source_network()

    assert len(source) == 6891
    assert source["source_id"].nunique() == 6891
    assert source["source_id"].notna().all()


def test_source_categories_match_audited_counts():
    source = read_source_network()

    assert source["category"].value_counts().to_dict() == {
        "Drain": 4797,
        "Stream": 2044,
        "River": 50,
    }


def test_csv_contains_one_row_per_source_record(drainage_outputs):
    audit = drainage_outputs["audit"]

    assert len(audit) == 6891
    assert audit["source_id"].nunique() == 6891
    assert audit["intersects_city"].sum() == 84
    assert audit["within_city"].sum() == 51


def test_clipped_output_has_valid_line_geometries(drainage_outputs):
    network = drainage_outputs["network"]

    assert len(network) == 84
    assert network["source_id"].nunique() == 84
    assert network.geometry.notna().all()
    assert (~network.geometry.is_empty).all()
    assert network.geometry.is_valid.all()
    assert network.geometry.geom_type.isin(
        ["LineString", "MultiLineString"]
    ).all()


def test_clipped_geometries_are_inside_city_boundary(drainage_outputs):
    from shapely.ops import unary_union

    network = drainage_outputs["network"].to_crs("EPSG:32643")
    boundary = drainage_outputs["boundary"].to_crs("EPSG:32643")

    network.geometry = network.geometry.force_2d()
    boundary.geometry = boundary.geometry.force_2d()
    city = unary_union(boundary.geometry)

    # GeoJSON reprojection can introduce floating-point differences at
    # boundary edges. Allow 1 mm for numerical comparison only; do not
    # buffer or modify the actual boundary used for clipping.
    numerical_tolerance_m = 0.001
    tolerated_city = city.buffer(numerical_tolerance_m)

    assert city.is_valid
    assert network.geometry.apply(
        tolerated_city.covers
    ).all()

def test_clipped_lengths_are_positive(drainage_outputs):
    network = drainage_outputs["network"]

    assert "clipped_length_km" in network.columns
    assert (network["clipped_length_km"] > 0).all()
    assert network["clipped_length_km"].sum() == pytest.approx(
        81.296, abs=0.01
    )


def test_report_documents_data_limitations(drainage_outputs):
    report = drainage_outputs["report"]

    assert "KSRSAC" in report
    assert "not assumed to mean exclusively" in report
    assert "not a flood-risk score" in report


def test_all_expected_outputs_are_created(drainage_outputs):
    assert OUTPUT_CSV.exists()
    assert OUTPUT_GEOJSON.exists()
    assert OUTPUT_REPORT.exists()
