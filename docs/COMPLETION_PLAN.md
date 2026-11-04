# Completion plan against the synopsis

Audit date: 4 November 2026. Baseline: f4d1dc4.

This assessment follows the uploaded synopsis, *AI-Based Urban Flood Digital Twin With Predictive Climate Analysis*, objectives (page 4) and methodology (page 7). It distinguishes software implementation from scientific validation. No defensible overall completion percentage is available: the objectives have not been assigned agreed weights and acceptance criteria.

| Synopsis requirement | Current implementation | Remaining acceptance criteria |
| --- | --- | --- |
| Integrate climate, geographic and historical flood data | Municipal GIS, terrain samples, rainfall displays and evidence inventory | Reproducible source bundle; verify event locations/dates and observation coverage |
| Train and evaluate flood probability/severity models | Experimental rainfall regression and baseline evaluation only | Define forecast horizon/spatial unit; assemble verified event and non-event observations; prevent leakage; independently evaluate flood occurrence and severity; assess probability calibration |
| GIS flood-risk and affected infrastructure | Drainage, terrain and facility maps | Independently validated hazard output, roads/buildings, spatial exposure calculations and uncertainty reporting |
| Digital twin and rainfall simulations | Uniform rainfall/runoff volume scenarios and spatial upstream volumes | Time-dependent hydrology, drainage capacity and hydraulic boundary conditions; mass-balance checks; observed-event validation before claiming inundation/depth |
| Explainable AI and decision support | Global rainfall-model impurity importance | Explain the actual flood model; assess explanation stability; validated infrastructure impacts before emergency recommendations |
| Backend, database, AI services and UI | FastAPI, React, SQLite and static evaluation results | Durable hosted storage; deployed end-to-end checks; reproducible model training/inference artifacts and tests |

## Work completed in this branch

- Scenario history accepts `SCENARIO_DB_PATH` for a mounted database location. This is configuration support, not evidence that a persistent disk is provisioned.
- Minimum duration is aligned with the UI at 0.01 hours, rejecting subnormal durations that could produce non-finite intensity.
- Sidebar selection follows the selected URL anchor instead of always highlighting Overview.
- Permanent tests cover scenario volume units, water balance, duration behaviour, invalid requests, spatial thresholds, zero runoff, real spatial samples and terrain lookup.
- README now describes the implemented system rather than claiming flood prediction, PostGIS or SHAP are present.

## Next implementation order and required inputs

1. **Reproducibility and deployment.** Restore original drainage KML; restore the historical rainfall training bundle and preprocessing/model-generation code; supply the full hydrology raster bundle. Confirm the deployed frontend/backend URLs. Configure durable storage, then verify a saved comparison survives a restart/redeploy. Current database is shared across visitors; add user isolation before treating it as private storage.
2. **Flood observation dataset.** Obtain dated, georeferenced Ballari flood observations with source provenance and uncertainty. Obtain defensible observation coverage for non-events. District names and landmark coordinates alone are insufficient. Define a forecast horizon and spatial unit before splitting data.
3. **Flood AI.** Build training and evaluation around those observations, using features available before the forecast period. Compare against baselines with temporal/spatial separation. Report event metrics and calibration, not training accuracy. Explain the trained flood model, not the rainfall model as a substitute.
4. **Hydrology and hydraulics.** Restore full-domain DEM, conditioned DEM, D8 pointer and accumulation with provenance and direction convention. Review conditioning and upstream boundaries. Obtain channel/drain geometry, capacity, roughness, outlets and event forcing for the chosen model. Select and verify a solver before generating water depths. A cell's upstream volume alone does not determine its water depth.
5. **Infrastructure impacts.** Add sourced roads/buildings and verified facility locations. Overlay validated inundation outputs with assets; distinguish exposure from damage and operational status. Do not infer flood exposure from drainage proximity alone.
6. **Final acceptance.** Repeat full tests with source inputs, reproduce model results, validate simulations against observations, test the deployed demonstration, and document residual limitations.

## Confirmed blockers

- The tracked flood evidence inventory has no incident coordinates; it cannot support the promised supervised spatial flood model.
- The original `data/raw/drainage/ballari_drainage_source.kml` is not in a fresh checkout. Nine existing drainage source tests require it. Do not fabricate it from the clipped city output: the tests cover the full original source.
- Full-domain hydrology rasters and the trained rainfall model/training dataset are not shipped in this checkout. Summaries and display data do not replace those sources.
- The rainfall model did not beat the zero-rainfall baseline on MAE in the reported evaluation periods.

These blockers require real inputs or an explicitly revised project scope. Adding coloured maps, arbitrary scores or synthetic flood labels would not complete the promised validated model.
