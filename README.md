# Ballari Urban Flood Digital Twin — research prototype

A React/TypeScript and FastAPI platform integrating Ballari GIS, historical rainfall, experimental rainfall-model evaluation, exploratory runoff scenarios and mapped facilities.

**This release does not predict validated flood probability, flood depth, inundation or infrastructure damage.** See [completion plan](docs/COMPLETION_PLAN.md) for the synopsis requirements and remaining work.

## Implemented

- Municipal boundary, mapped drainage and provisional derived drainage overlays.
- Terrain inspection over 95,246 GIS sample locations.
- Historical rainfall visualization and Random Forest evaluation against baselines.
- Global rainfall-model feature importance (not flood-model explanations).
- Rainfall/runoff volume comparisons, SQLite history and spatial upstream-volume scenarios.
- Education/healthcare facility maps with terrain lookup.

The rainfall model did not outperform the zero-rainfall baseline on MAE in any reported evaluation period. Scenario volumes are formula-based calculations with user assumptions, not machine-learning flood predictions.

## Local setup

Use the project's Python environment and install `requirements.txt`. From the repository root:

```bash
python -m pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload
```

In a separate terminal:

```bash
npm --prefix frontend ci
npm --prefix frontend run dev
```

Frontend `VITE_API_BASE_URL` defaults to `http://127.0.0.1:8000`. Set it to the backend URL when building a deployment. Backend `FRONTEND_ORIGINS` is a comma-separated CORS allowlist of frontend origins.

## Scenario storage

History defaults to `data/scenario_history.db`. Set backend environment variable `SCENARIO_DB_PATH` to a database file on a provisioned persistent volume to retain history across host replacements. Merely setting this variable does not provision storage. Back up the database and verify persistence after a redeploy. All visitors currently share the same history; private per-user storage is not implemented.

## Verification

```bash
npm --prefix frontend run build
npm --prefix frontend run lint
python -m pytest tests -q
```

Full source-data verification requires `data/raw/drainage/ballari_drainage_source.kml`, which is not included in Git. A fresh checkout cannot pass its nine source checks without the original input. For the runnable subset only:

```bash
python -m pytest tests --ignore=tests/test_drainage_dataset.py -q
```

This subset is not a substitute for running the full suite with source data. Software tests do not establish predictive skill or hydrological accuracy.

## Actual stack

React, TypeScript, Leaflet, FastAPI, Python, GeoPandas, Rasterio, scikit-learn experiments and SQLite. PostGIS and SHAP are not implemented in this release. OpenStreetMap facility data include attribution and source limitations in the dashboard.
