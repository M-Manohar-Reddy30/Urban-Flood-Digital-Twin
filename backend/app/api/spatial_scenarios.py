"""Spatial upstream runoff-volume scenarios using existing GIS samples."""

import numpy as np
from fastapi import APIRouter, HTTPException

from backend.app.api.rainfall_scenarios import ScenarioInput
from backend.app.api.terrain_inspection import load_dataset

router = APIRouter(
    prefix="/api/v1/scenarios",
    tags=["Exploratory spatial scenarios"],
)


@router.post("/rainfall/spatial")
def spatial_rainfall_scenario(request: ScenarioInput):
    try:
        frame, _, _, _ = load_dataset()
    except OSError as exc:
        raise HTTPException(
            status_code=503, detail="Spatial scenario data is unavailable."
        ) from exc
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(
            status_code=500, detail="Spatial scenario data is invalid."
        ) from exc

    # Display existing GIS sample locations along larger contributing paths.
    # This threshold controls the preview; it is not a flood-warning threshold.
    threshold_km2 = 1.0
    selected = frame.loc[
        frame["upstream_contributing_area_km2"] >= threshold_km2,
        ["longitude", "latitude", "upstream_contributing_area_km2"],
    ].copy()

    if selected.empty:
        raise HTTPException(
            status_code=503, detail="No spatial scenario samples are available."
        )

    areas = selected["upstream_contributing_area_km2"].to_numpy(dtype=float)
    volumes = (
        areas * 1_000_000
        * request.rainfall_depth_mm / 1000
        * request.runoff_fraction
    )
    if not np.isfinite(volumes).all():
        raise HTTPException(
            status_code=500, detail="Invalid spatial scenario calculation."
        )

    features = []
    for sample_id, row in selected.iterrows():
        area = float(row["upstream_contributing_area_km2"])
        volume = (
            area * 1_000_000
            * request.rainfall_depth_mm / 1000
            * request.runoff_fraction
        )
        features.append({
            "type": "Feature",
            "id": int(sample_id),
            "geometry": {
                "type": "Point",
                "coordinates": [
                    float(row["longitude"]), float(row["latitude"])
                ],
            },
            "properties": {
                "sample_id": int(sample_id),
                "upstream_contributing_area_km2": area,
                "estimated_upstream_runoff_volume_m3": volume,
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "status": "exploratory_uncalibrated_spatial_scenario",
            "method_version": "uniform_upstream_runoff_volume_v1",
            "inputs": request.model_dump(),
            "sample_count": len(features),
            "minimum_contributing_area_km2": threshold_km2,
            "representation": (
                "GIS sample centres; hydrology values describe the "
                "hydrology cell containing each sample centre."
            ),
            "formula": (
                "upstream_contributing_area_km2 * 1000000 "
                "* rainfall_depth_mm / 1000 * runoff_fraction"
            ),
            "maximum_displayed_upstream_runoff_volume_m3": float(volumes.max()),
            "limitations": [
                "Uniform rainfall and runoff fraction across the entire "
                "modelled upstream area, including land outside Ballari.",
                "Upstream areas overlap. Do not sum volumes across points.",
                "Multiple GIS samples may represent the same hydrology cell.",
                "Duration does not change total volume at fixed rainfall "
                "depth and runoff fraction.",
                "No travel time, discharge, drainage capacity, flood depth "
                "or inundation extent is calculated.",
                "DEM conditioning and upstream domain coverage remain provisional.",
                "The display threshold is not a flood-warning category.",
            ],
        },
    }
