"""Exploratory rainfall-volume scenarios with explicit assumptions."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict

from backend.app.api.terrain_inspection import load_dataset

router = APIRouter(
    prefix="/api/v1/scenarios",
    tags=["Exploratory rainfall scenarios"],
)


class ScenarioInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    rainfall_depth_mm: float = Field(ge=0, le=1000)
    duration_hours: float = Field(gt=0, le=168)
    runoff_fraction: float = Field(ge=0, le=1)


def calculate_scenario(request: ScenarioInput, cell_count: int) -> dict:
    # Each existing GIS sample represents one 30 m square.
    # This is sampled-grid area, not exact municipal polygon area.
    area_m2 = cell_count * 30.0 * 30.0
    rainfall_volume = request.rainfall_depth_mm / 1000.0 * area_m2
    runoff_volume = rainfall_volume * request.runoff_fraction

    return {
        "status": "exploratory_uncalibrated_scenario",
        "inputs": request.model_dump(),
        "coverage": {
            "sampled_cell_count": cell_count,
            "gis_cell_size_m": 30,
            "sampled_area_km2": area_m2 / 1_000_000.0,
            "area_definition": (
                "Sum of full 30 m GIS cells represented by feature centres; "
                "not exact clipped municipal area."
            ),
        },
        "results": {
            "average_rainfall_intensity_mm_per_hour": (
                request.rainfall_depth_mm / request.duration_hours
            ),
            "rainfall_volume_m3": rainfall_volume,
            "estimated_runoff_volume_m3": runoff_volume,
            "remaining_water_volume_m3": rainfall_volume - runoff_volume,
        },
        "method": {
            "rainfall_volume": "rainfall_depth_mm / 1000 * sampled_area_m2",
            "runoff_volume": "rainfall_volume_m3 * runoff_fraction",
            "runoff_fraction_source": "User-specified assumption; not calibrated",
        },
        "limitations": [
            "Uniform rainfall depth and runoff fraction across sampled cells.",
            "Remaining water is not separately modelled as infiltration, "
            "storage or evaporation.",
            "Duration changes average intensity; with a fixed runoff fraction "
            "it does not change total runoff volume.",
            "No flow routing, drainage capacity, flood depth or inundation "
            "extent is calculated.",
            "This is not a weather forecast or a flood probability.",
        ],
    }


@router.post("/rainfall")
def rainfall_scenario(request: ScenarioInput):
    try:
        frame, _, _, _ = load_dataset()
    except OSError as exc:
        raise HTTPException(
            status_code=503, detail="Scenario feature data is unavailable."
        ) from exc
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(
            status_code=500, detail="Scenario feature data is invalid."
        ) from exc

    return calculate_scenario(request, len(frame))
