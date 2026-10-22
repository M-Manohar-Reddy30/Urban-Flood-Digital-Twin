
from pathlib import Path

import pandas as pd

from scripts.build_data_readiness_report import (
    FILES,
    RASTERS,
    csv_summary,
    raster_summary,
    rainfall_quality_checks,
    station_quality_checks,
    gis_quality_checks,
)


ROOT = Path(__file__).resolve().parents[3]


def get_readiness_summary() -> dict:
    """Build a current data-readiness summary from available project files."""
    datasets = {}

    for name, path in FILES.items():
        if not path.is_file():
            datasets[name] = {
                "status": "missing",
                "path": str(path.relative_to(ROOT)),
            }
            continue

        summary = csv_summary(path)
        datasets[name] = {
            "status": "present",
            "path": str(path.relative_to(ROOT)),
            "rows": summary["rows"],
            "columns": summary["columns"],
            "missing_cells": summary["missing_cells"],
            "duplicate_rows": summary["duplicate_rows"],
        }

    raster_data = {}

    for name, path in RASTERS.items():
        if not path.is_file():
            raster_data[name] = {
                "status": "missing",
                "path": str(path.relative_to(ROOT)),
            }
            continue

        summary = raster_summary(path)
        raster_data[name] = {
            "status": "present",
            "path": str(path.relative_to(ROOT)),
            "crs": summary["crs"],
            "width": summary["width"],
            "height": summary["height"],
            "resolution": summary["resolution"],
            "bounds": summary["bounds"],
            "valid_pixels": summary["valid_pixels"],
        }

    present_rasters = [
        item for item in raster_data.values()
        if item["status"] == "present"
    ]

    all_rasters_present = len(present_rasters) == len(RASTERS)
    aligned = False

    if all_rasters_present:
        first = present_rasters[0]
        aligned = all(
            item["crs"] == first["crs"]
            and item["width"] == first["width"]
            and item["height"] == first["height"]
            and item["resolution"] == first["resolution"]
            and item["bounds"] == first["bounds"]
            for item in present_rasters[1:]
        )

    evidence_path = FILES["Flood evidence inventory"]
    evidence_summary = {
        "status": "missing",
        "incident_coordinate_records": 0,
        "supervised_spatial_labels_ready": False,
    }

    if evidence_path.is_file():
        evidence = pd.read_csv(evidence_path)
        coordinate_count = 0

        if {"latitude", "longitude"}.issubset(evidence.columns):
            lat = pd.to_numeric(evidence["latitude"], errors="coerce")
            lon = pd.to_numeric(evidence["longitude"], errors="coerce")
            coordinate_count = int((lat.notna() & lon.notna()).sum())

        evidence_summary = {
            "status": "present",
            "record_count": int(len(evidence)),
            "incident_coordinate_records": coordinate_count,
            "supervised_spatial_labels_ready": False,
            "note": (
                "Reported evidence is not automatically verified. "
                "Candidate landmark coordinates are not incident coordinates."
            ),
        }

    return {
        "project": "Ballari Urban Flood Digital Twin",
        "report_scope": "Current files available at request time",
        "datasets": datasets,
        "quality_checks": {
            "nasa_imerg_rainfall": rainfall_quality_checks(),
            "bellary_station_rainfall": station_quality_checks(),
            "gis_features": gis_quality_checks(),
        },
        "rasters": raster_data,
        "raster_alignment": {
            "all_rasters_present": all_rasters_present,
            "crs_dimensions_resolution_aligned": aligned,
        },
        "flood_evidence": evidence_summary,
        "modelling_readiness": {
            "rainfall": "Suitable for descriptive analysis",
            "terrain_and_land_cover": "Suitable as candidate GIS features",
            "historical_flood_evidence": (
                "Not ready for supervised spatial labels"
            ),
            "flood_no_flood_training_target": "Not approved for training",
            "predictive_model_validation": "Not established",
        },
        "interpretation": (
            "Data-quality checks do not establish measurement accuracy "
            "or flood-prediction skill. Missing flood reports are not "
            "confirmed no-flood events."
        ),
    }
