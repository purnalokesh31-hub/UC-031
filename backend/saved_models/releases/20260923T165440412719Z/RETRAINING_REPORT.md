# CropGuard retraining results

Previous release: `20260923T163712505316Z`  
Candidate release: `20260923T165440412719Z`

Same fixed 100 test rows per crop; all tuning uses 300 training rows with 4-fold CV. 100 separate calibration rows.

Synthetic data only. The fixed holdout has been inspected in earlier work; independent external validation is still needed. R2 is not classification accuracy.

## Fixed holdout results

| Crop | Model | R² before → after | MAE before → after (q/ha) | New MAPE | Within ±5% of actual |
|---|---|---:|---:|---:|---:|
| Rice | classical | 0.9177 → 0.9127 | 0.868 → 0.902 | 1.68% | 99% |
| Rice | quantum | 0.8821 → 0.9123 | 1.056 → 0.897 | 1.68% | 100% |
| Wheat | classical | 0.9384 → 0.9384 | 0.754 → 0.754 | 1.74% | 98% |
| Wheat | quantum | 0.8865 → 0.9305 | 0.947 → 0.781 | 1.80% | 98% |
| Maize | classical | 0.9149 → 0.9149 | 0.815 → 0.815 | 1.72% | 94% |
| Maize | quantum | 0.9205 → 0.9211 | 0.801 → 0.787 | 1.66% | 96% |
| Cotton | classical | 0.9239 → 0.9239 | 0.390 → 0.390 | 2.13% | 95% |
| Cotton | quantum | 0.7900 → 0.9078 | 0.640 → 0.413 | 2.26% | 94% |
| Sugarcane | classical | 0.9082 → 0.9082 | 13.232 → 13.232 | 1.90% | 99% |
| Sugarcane | quantum | 0.9192 → 0.9189 | 12.433 → 12.193 | 1.75% | 98% |
| Groundnut | classical | 0.9430 → 0.9430 | 0.294 → 0.294 | 1.77% | 97% |
| Groundnut | quantum | 0.8297 → 0.9224 | 0.497 → 0.342 | 2.06% | 96% |

## Interpretation

- The larger quantum search includes smaller encoding angles, regularization, centered kernels, and one/two encoding layers. The batched exact statevector implementation is checked against Qiskit.
- Classical candidates include polynomial and spline features plus linear, kernel, and tree regressors. The new classical estimator is Rice; spline candidates won for Rice.
- Every candidate family matches or lowers the previous training cross-validation error. Holdout improvements vary; declines are listed below and remain visible in this report.
- Training CV changed the serving family for: Sugarcane: classical → quantum. Selection never uses the displayed test scores.
- Holdout R² declined for: Rice classical R²: 0.9177 → 0.9127; Sugarcane quantum R²: 0.9192 → 0.9189.
- The dataset and its noise were not changed. Its generator adds independent Gaussian noise with standard deviation 2% of base yield. Further fitting cannot guarantee predicting that random component.
- MAPE is mean absolute percentage error. The ±5% column uses an explicit error tolerance, not exact correctness. These measurements do not establish farm accuracy.

## Warm inference timing

| Crop | Quantum before (ms) | Quantum after (ms) |
|---|---:|---:|
| Rice | 7.343 | 3.525 |
| Wheat | 5.869 | 3.695 |
| Maize | 6.742 | 2.379 |
| Cotton | 4.620 | 3.244 |
| Sugarcane | 6.535 | 3.146 |
| Groundnut | 7.133 | 3.309 |

Median of 10 single-row predictions on this machine; excludes network and cold loading.

## Integrity checks

Dataset hash unchanged; identical disjoint splits; all 12 serialized pipelines reproduce saved predictions, regression scores and independent calibration radii. Active-family selection and training-CV non-regression checked.
