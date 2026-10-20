# Flood Prediction Target Feasibility Assessment

## 1. Study Area

**Study area:** Ballari Urban Area, Karnataka, India.

The analysis must distinguish the urban study area from the wider Ballari district. District-level reports must not be treated as verified urban incident locations without supporting evidence.

## 2. Purpose

This document evaluates whether the currently available datasets can support a scientifically defensible flood-prediction target.

The project will not create artificial flood/no-flood labels, assume that an unreported location did not flood, or present unvalidated outputs as real-world flood predictions.

## 3. Current Data Readiness

### 3.1 Rainfall

The 2024 NASA IMERG dataset contains 366 daily records from one grid point.

- The date series covers 2024-01-01 through 2024-12-31.
- The sampled location is approximately 15.15° N, 76.95° E.
- The precipitation variable is documented as a daily mean precipitation rate; it must not automatically be interpreted as accumulated daily rainfall.
- One grid point does not establish rainfall conditions across the entire urban area.

The separate Bellary station dataset contains intermittent observations and requires appropriate quality review. Its records must not be treated as a continuous hourly series.

### 3.2 Terrain and Land Cover

Processed GIS features contain elevation, slope and land-cover attributes. These data support geographic analysis, but their presence alone does not establish that a location flooded or quantify its probability of flooding.

The elevation source is a digital surface model. Its values may reflect buildings and vegetation as well as terrain.

### 3.3 Historical Flood Evidence

The current flood evidence inventory contains nine records.

- No record currently has verified incident coordinates.
- Candidate landmark coordinates must not be substituted for incident coordinates without verification.
- Reported district-level incidents must not automatically be interpreted as incidents inside the urban study area.
- Vulnerable-village population figures are not flood-affected population counts.
- Absence of a flood report is not evidence that flooding did not occur.

The current inventory is not a validated spatial training-label dataset.

### 3.4 Infrastructure and Drainage

The existing data inventory has not established that complete, usable urban roads, buildings, stormwater drains or drainage-capacity datasets are available.

Their availability, coverage, source dates, coordinate reference systems and suitability must be investigated before they are used as model features.

## 4. Candidate Prediction Targets

### Candidate A: Flood Occurrence Prediction

**Proposed output:** An estimate of flood occurrence at a defined location and forecast time or period, using information available before that period.

**Required evidence:**

- Verified flood-event locations and timestamps.
- A clearly defined spatial unit and prediction horizon.
- Reliable event observations and defensible non-event observations.
- Time-aligned rainfall and other features available at prediction time.
- Independent temporal or spatial evaluation data.

**Current decision:** Not ready for supervised training. Verified incident coordinates and reliable negative observations are not currently available.

### Candidate B: Flood Susceptibility Analysis

**Proposed output:** A relative assessment of how geographic conditions may be associated with flood susceptibility.

**Potential inputs:** Elevation, slope, land cover and, if suitable data become available, drainage and urban infrastructure characteristics.

**Limitations:**

- Terrain-derived rankings are not validated flood probabilities.
- Without suitable observed flood evidence, a weighted or rule-based map must be labelled as exploratory and its assumptions disclosed.
- Model weights or thresholds must not be presented as empirically validated when they have not been validated.
- Independent evidence is required before claiming that the map accurately identifies flood-prone locations.

**Current decision:** Potentially feasible as an explicitly limited exploratory analysis, subject to a documented method and evidence review. A validated susceptibility model is not yet established.

### Candidate C: Rainfall Forecasting

**Proposed output:** Future rainfall estimates for a specified location and forecast horizon.

This is a distinct task from flood prediction. The existing rainfall model must be evaluated against suitable held-out observations and compared with a baseline before its performance is described as useful for forecasting.

Rainfall forecast performance alone does not validate flood predictions.

**Current decision:** Suitable for a separate model-evaluation workstream, subject to checking the existing implementation, evaluation method and data limitations.

## 5. Requirements Before Supervised Flood Training

Training must not begin until the following conditions are met:

1. A prediction target, spatial unit and prediction horizon are explicitly defined.
2. Historical flood incidents have verified locations and dates, with source provenance.
3. Flood-event labels are constructed only from evidence that meets documented inclusion criteria.
4. Non-event observations have defensible observation coverage; unreported locations are not automatically labelled as non-flood.
5. Features are aligned to the correct location and time and would be available at prediction time.
6. Duplicate incidents, missing data, spatial leakage and temporal leakage are assessed.
7. A reproducible train/validation/test strategy is defined before model comparison.
8. Evaluation metrics and a baseline are selected in advance.
9. Results and limitations can be reproduced from documented source data and code.

The number of records alone is not a sufficient criterion for training readiness. Label quality, spatial coverage, temporal coverage, class balance and independent evaluation are also necessary.

## 6. Evidence Collection Priorities

Prioritize the following work:

1. Verify the locations and dates of the incidents already listed in the evidence inventory.
2. Seek authoritative or otherwise traceable flood reports, inundation maps and event records covering the urban study area.
3. Investigate whether reliable historical non-event observations and observation-coverage records exist.
4. Identify usable rainfall observations with appropriate spatial and temporal coverage.
5. Investigate authoritative drainage, road, building and critical-facility datasets.
6. Record the source, licence, date, spatial coverage, coordinate system and limitations of every acquired dataset.

A source being available online does not automatically make it suitable for training.

## 7. Go/No-Go Decision

### Current decision: NO-GO for supervised flood-occurrence model training

Reason: the current evidence inventory does not provide verified incident coordinates or a validated spatial set of flood/no-flood labels.

### Conditional GO for exploratory analysis

Proceed with descriptive rainfall analysis, terrain and land-cover analysis, evidence verification and data collection. An exploratory susceptibility assessment may be developed only if its method and limitations are explicit and it is not misrepresented as a validated prediction.

### Reassessment criteria

Reassess supervised training when the project has sufficient verified event observations, defensible non-event observations, appropriate feature coverage and an independent evaluation design for the chosen target.

No fixed minimum sample count is asserted in this document because the required quantity depends on the target, spatial and temporal coverage, class distribution and evaluation design.

## 8. Reporting Rules

- Distinguish observed data, reported evidence, derived features, exploratory indices and model predictions.
- Do not invent labels, coordinates, dates or rainfall observations.
- Do not interpret missing reports as confirmed non-events.
- Do not describe a susceptibility score as a flood probability unless the probability is appropriately calibrated and validated.
- Report the study area's spatial limitations and the provenance of all inputs.
- Revisit this assessment whenever the available evidence materially changes.

## 9. Current Conclusion

The project has usable rainfall, terrain and land-cover inputs for exploratory analysis, but its current flood evidence is insufficient for defensible supervised flood-occurrence training.

The next priority is to improve flood-event evidence and establish a rigorous target definition. Model training should follow that work, not precede it.
