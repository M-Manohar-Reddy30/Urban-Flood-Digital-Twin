"""Persist exploratory scenario comparisons in SQLite."""

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import sqlite3
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.api.rainfall_scenarios import ScenarioInput, rainfall_scenario

router = APIRouter(prefix="/api/v1/scenarios", tags=["Scenario history"])
DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "data/scenario_history.db"
DB_PATH = DEFAULT_DB_PATH


def database_path():
    """Allow a host-mounted persistent volume without changing local defaults."""
    configured = os.environ.get("SCENARIO_DB_PATH", "").strip()
    return Path(configured).expanduser() if configured else DB_PATH


class ComparisonInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    scenario_a: ScenarioInput
    scenario_b: ScenarioInput

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be blank.")
        return value


def connect():
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("""
            CREATE TABLE IF NOT EXISTS scenario_comparisons (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                payload TEXT NOT NULL
            )
        """)
        connection.commit()
        return connection
    except Exception:
        connection.close()
        raise


@router.post("/saved", status_code=201)
def save_comparison(request: ComparisonInput):
    # Calculate on the server; do not trust client-submitted results.
    scenario_a = rainfall_scenario(request.scenario_a)
    scenario_b = rainfall_scenario(request.scenario_b)
    record = {
        "id": str(uuid4()),
        "name": request.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "method_version": "uniform_runoff_fraction_v1",
        "status": "exploratory_uncalibrated_scenario",
        "scenario_a": scenario_a,
        "scenario_b": scenario_b,
    }
    try:
        with closing(connect()) as connection:
            with connection:
                connection.execute(
                    "INSERT INTO scenario_comparisons "
                    "(id, name, created_at, payload) VALUES (?, ?, ?, ?)",
                    (
                        record["id"], record["name"], record["created_at"],
                        json.dumps(record, allow_nan=False),
                    ),
                )
    except (OSError, sqlite3.Error) as exc:
        raise HTTPException(
            status_code=503, detail="Scenario storage is unavailable."
        ) from exc
    return record


@router.get("/saved")
def list_comparisons():
    try:
        with closing(connect()) as connection:
            rows = connection.execute(
                "SELECT id, name, created_at FROM scenario_comparisons "
                "ORDER BY created_at DESC, id DESC LIMIT 100"
            ).fetchall()
    except (OSError, sqlite3.Error) as exc:
        raise HTTPException(
            status_code=503, detail="Scenario storage is unavailable."
        ) from exc
    return {"records": [dict(row) for row in rows], "limit": 100}


@router.get("/saved/{comparison_id}")
def get_comparison(comparison_id: str):
    try:
        with closing(connect()) as connection:
            row = connection.execute(
                "SELECT payload FROM scenario_comparisons WHERE id = ?",
                (comparison_id,),
            ).fetchone()
    except (OSError, sqlite3.Error) as exc:
        raise HTTPException(
            status_code=503, detail="Scenario storage is unavailable."
        ) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Saved comparison not found.")
    return json.loads(row["payload"])
