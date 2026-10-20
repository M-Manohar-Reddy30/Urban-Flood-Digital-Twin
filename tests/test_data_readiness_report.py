from scripts.build_data_readiness_report import (
    FILES,
    RASTERS,
    build_report,
    csv_summary,
    raster_summary,
)


def test_rainfall_inventory_has_expected_2024_coverage():
    summary = csv_summary(FILES["NASA IMERG rainfall"])

    assert summary["rows"] == 366
    assert summary["missing_cells"] == 0
    assert summary["duplicate_rows"] == 0
    assert "date" in summary["column_names"]
    assert "precipitation_mm_per_day" in summary["column_names"]


def test_flood_evidence_is_not_misrepresented_as_verified_labels():
    report = build_report()

    assert "Inventory records: 9" in report
    assert "Records with incident latitude and longitude: 0" in report
    assert "Candidate landmark coordinates are" in report
    assert "not incident coordinates" in report
    assert "Flood/no-flood target | Not approved for training" in report


def test_modelling_rasters_share_grid_metadata():
    summaries = [raster_summary(path) for path in RASTERS.values()]
    first = summaries[0]

    for summary in summaries[1:]:
        assert summary["crs"] == first["crs"]
        assert summary["width"] == first["width"]
        assert summary["height"] == first["height"]
        assert summary["resolution"] == first["resolution"]
        assert summary["bounds"] == first["bounds"]


def test_report_does_not_claim_model_validation():
    report = build_report()

    assert "does not establish flood-prediction accuracy" in report
    assert "Predictive model validation | Not established" in report
    assert "Missing flood reports must not be interpreted as confirmed no-flood events." in report



def test_dataset_specific_quality_checks():
    from scripts.build_data_readiness_report import (
        rainfall_quality_checks,
        station_quality_checks,
        gis_quality_checks,
    )

    rainfall = rainfall_quality_checks()
    assert rainfall["missing_columns"] == []
    assert rainfall["unique_dates"] == 366
    assert rainfall["missing_calendar_days"] == 0
    assert rainfall["duplicate_dates"] == 0
    assert rainfall["negative_rainfall_values"] == 0
    assert rainfall["retrieval_counts_other_than_48"] == 0
    assert rainfall["statuses_other_than_ok"] == 0

    station = station_quality_checks()
    assert station["missing_columns"] == []
    assert station["invalid_timestamps"] == 0
    assert station["duplicate_timestamps"] == 0
    assert station["negative_rainfall_values"] == 0
    assert station["high_value_review_flags"] == 16

    gis = gis_quality_checks()
    assert gis["missing_columns"] == []
    assert gis["rows"] == 95246
    assert gis["invalid_longitude"] == 0
    assert gis["invalid_latitude"] == 0
    assert gis["invalid_elevation_m"] == 0
    assert gis["invalid_slope_degrees"] == 0
    assert gis["invalid_landcover_class"] == 0


def test_raster_summary_reports_valid_pixel_counts():
    summaries = {
        name: raster_summary(path)
        for name, path in RASTERS.items()
    }

    assert summaries["Corrected DEM"]["valid_pixels"] == 97444
    assert summaries["Corrected slope"]["valid_pixels"] == 95246
    assert summaries["Aligned land cover"]["valid_pixels"] == 97461


def test_report_includes_quality_checks_and_pixel_counts():
    report = build_report()

    assert "## 2. Dataset-specific quality checks" in report
    assert "Missing calendar days: 0" in report
    assert "High value review flags: 16" in report
    assert "Valid pixels: 97,444" in report
    assert "Valid pixels: 95,246" in report
    assert "Valid pixels: 97,461" in report
