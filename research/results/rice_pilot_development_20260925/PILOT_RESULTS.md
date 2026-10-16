# Annual rice pilot: development results

Exploratory development results only. Final geographic and future-year cohorts were not scored.

## What was evaluated

544 district-year records, 17 historical district units, agricultural years 1981–82 to 2012–13. Only the frozen development pool of 364 rows in 13 districts was used for these experiments. Each of five splits held out three development districts and used separate calibration districts.

Inputs: four SoilGrids mapped topsoil estimates, NASA annual temperature/rainfall/humidity at documented reference points, and a year trend. Outcomes are reported district rice yields. This is retrospective annual estimation, not a farm-level forecast.

## Comparison

All tuned families received 25 candidates and the same grouped inner folds for each split. The mean and year-only baselines are untuned. Values below are means across five overlapping splits. The ± term is split standard deviation, not a confidence interval.

| Model | MAE (q/ha) | RMSE ± SD (q/ha) | R² | 90% interval coverage | Interval width (q/ha) |
|---|---:|---:|---:|---:|---:|
| Year trend only | 3.785 | 4.671 ± 0.716 | 0.278 | 89.3% | 16.914 |
| Random forest | 3.931 | 4.833 ± 0.771 | 0.226 | 96.0% | 19.205 |
| Extra Trees | 3.957 | 4.870 ± 0.802 | 0.214 | 96.0% | 20.254 |
| RBF SVR | 4.182 | 5.048 ± 1.242 | 0.137 | 93.1% | 20.217 |
| Quantum: one layer | 4.196 | 5.098 ± 1.439 | 0.108 | 92.6% | 20.043 |
| Classical RBF kernel ridge | 4.231 | 5.108 ± 1.129 | 0.124 | 94.3% | 20.821 |
| Histogram gradient boosting | 4.349 | 5.238 ± 0.755 | 0.096 | 89.8% | 18.751 |
| Ridge | 4.369 | 5.311 ± 1.418 | 0.038 | 92.6% | 20.002 |
| Simulated quantum kernel | 4.417 | 5.350 ± 0.830 | 0.058 | 92.4% | 20.060 |
| Quantum: no entanglement | 4.521 | 5.403 ± 1.248 | 0.018 | 92.6% | 20.188 |
| Quantum: uncentered kernel | 4.772 | 5.760 ± 1.629 | -0.141 | 91.7% | 20.907 |
| Training mean | 4.825 | 5.956 ± 0.540 | -0.159 | 89.0% | 20.533 |

## Interpretation

The classical family with the lowest mean development RMSE was Random forest. The main simulated quantum kernel's mean RMSE difference relative to that family was +0.517 q/ha (positive means larger error). This is an exploratory ranking, not a final-test superiority claim.

The year-only baseline scored RMSE 4.671 q/ha and mean R² 0.278. The lowest mean RMSE across all models and controls was Year trend only. This comparison is essential: additional weather, mapped soil and model complexity have not yet established useful improvement over a simple time trend on these district holdouts.

R² is not percentage accuracy. Nominal 90% intervals can miss their target under geographic shift. Each outer test has only three districts, so cluster-bootstrap bounds are unstable; overlapping repeats and multiple comparisons further limit significance claims.

The model evaluates a four-qubit fidelity kernel exactly on a classical computer. These results do not demonstrate a quantum-computing advantage.

## Verification

- All 12 model/control variants completed all five district splits.
- Every prediction row belongs to the frozen fit pool; no final reserved district or year appears.
- Equal candidate budgets, finite metrics and panel checksum checked.
- Predictions, per-split scores, tuning parameters/times and paired district-bootstrap differences are retained beside this report.

## Before publication

1. Feature-removal sensitivity is now completed in `../rice_feature_sensitivity_20260925/FEATURE_SENSITIVITY.md`. Use its findings to guide the next development-only data investigation.
2. Investigate reference-point representativeness and exclusions of three districts with unavailable soil estimates.
3. Obtain independently sourced external yield observations and agronomic review where feasible.
4. Complete the novelty review, finalize the analysis, and then run the reserved evaluation once.

Static modern mapped soil is not a historical soil measurement. The sample is geographically small and historical. Strong publication claims and app deployment remain premature.

Metadata clarification: the generic run-manifest limitation text mentions centroid sampling and absence of a technology trend. For this pilot, the actual inputs use source-listed reference points (not verified centroids) and explicitly include year_trend. The panel manifest and this report contain the study-specific definitions.
