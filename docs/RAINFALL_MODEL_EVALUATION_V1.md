# Rainfall Model Evaluation — Experiment V1

## Decision

Retain the Random Forest as an experimental retrospective benchmark.
Do not present it as a validated operational rainfall forecast or
a flood-occurrence prediction.

The model did not outperform the zero-rainfall baseline on the
preselected primary metric, MAE, in any evaluated period.
Zero rainfall is a benchmark, not a recommended forecasting system.

## Data and protocol

- Target: area-weighted municipal precipitation rate, stored in mm/day.
- Training: 2001–2002, 723 eligible observations.
- Validation: 2003, 365 observations.
- Held-out test at the time of this experiment: 2004, 366 observations.
- Later-period evaluation: 2024, 359 observations.
- Missing years: 2005–2023; no interpolation was performed.
- January 1–7, 2024 were excluded because lag history was unavailable.
- Features: seven exact calendar-day lags, their mean and maximum,
  and sine/cosine encoding of the target month.
- Model: Random Forest, 300 trees, maximum depth 6,
  minimum leaf size 10, random seed 42.
- Model remained fitted on 2001–2002 during all evaluations.
- Primary metric: MAE. Secondary diagnostics: RMSE, bias,
  and MAE on observations at or above the training 95th percentile.
- Upper-tail threshold: approximately 9.8632 mm/day.
  This is a statistical diagnostic, not an official warning threshold.

Predictions use actual preceding observations sequentially.
They are not forecasts of an entire year from its first day.
Operational availability of the preceding-day inputs was not established.

## Results

Errors are in mm/day. Values below are rounded.

| Period | RF MAE | Best baseline MAE | RF RMSE | Best baseline RMSE |
|---|---:|---:|---:|---:|
| 2003 | 1.6444 | 1.1351 (zero) | 3.7933 | 3.8519 (monthly mean) |
| 2004 | 2.2343 | 1.7290 (zero) | 5.3396 | 5.3479 (monthly mean) |
| 2024 | 2.8466 | 2.3276 (zero) | 6.7844 | 6.7521 (monthly mean) |

The RF had the lowest upper-tail MAE among compared methods in 2003
and 2004, based on 11 and 20 days respectively.
In 2024, with 22 upper-tail days, the previous seven-day mean
outperformed RF: 18.5899 versus 20.1720 mm/day.

These descriptive comparisons do not establish statistical significance.
Performance advantages were not consistent across periods.

## Provenance and limitations

Internal consistency checks passed for the five annual datasets.
Sampled remote-source comparisons passed for 40 grid observations
and 10 municipal estimates. These checks establish sampled
reproducibility, not independent satellite measurement accuracy.

This experiment does not validate flood probabilities, flood depths,
inundation maps, or emergency warnings.

The 2004 and 2024 results have now been inspected. Future changes
informed by these results require a new evaluation design and must
not describe these periods as untouched tests.

## Saved artifacts

Experiment directory:
data/processed/rainfall/rainfall_experiment_wd__gq_e

Validation model and results:
rf_validation_onlmhoex/

Frozen-model evaluation:
frozen_model_evaluation_ivux9k63/

Source-check reports:
data/processed/rainfall/source_audit_ifo29618/

## Next implementation milestone

Expose historical rainfall evaluation results in the application
with clear experimental status, observed-versus-predicted comparisons,
baseline metrics, date coverage, and limitations.
