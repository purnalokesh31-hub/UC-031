# Model audit — 6 October 2026

## Scope

This audit checks the deployed yield-regression service and leaf-disease classifier against the real labeled data currently present in the project. It does not evaluate or change the UI.

## Deployed yield models

The active release is `20260923T165440412719Z`. Its six crop pipelines each contain a classical regressor and an exact quantum-kernel regressor simulated on a classical computer. The active dataset scope is explicitly `synthetic`; the reported test metrics use 300 training rows, 100 calibration rows, and 100 test rows per crop. Model selection is based on training cross-validation. Those scores describe the generated demo distribution, not observed field accuracy.

| Crop | Classical R² / RMSE (q/ha) | Simulated quantum R² / RMSE (q/ha) | Selected |
|---|---:|---:|---|
| Rice | 0.913 / 1.112 | 0.912 / 1.115 | Classical |
| Wheat | 0.938 / 0.919 | 0.931 / 0.976 | Classical |
| Maize | 0.915 / 1.059 | 0.921 / 1.019 | Classical |
| Cotton | 0.924 / 0.473 | 0.908 / 0.521 | Classical |
| Sugarcane | 0.908 / 15.693 | 0.919 / 14.745 | Simulated quantum |
| Groundnut | 0.943 / 0.364 | 0.922 / 0.424 | Classical |

The running API returned finite predictions for both regressors for Rice, Wheat, Maize, Cotton, Sugarcane, and Groundnut at each crop's feature-range midpoint. All six were within the release's synthetic training bounds. This is an inference smoke check only; no real outcomes were available for those requests.

The application's eight inputs (N, P, K, pH, moisture, temperature, humidity, rainfall) do not match the existing real-yield pilot's features and prediction target, so that pilot cannot validate or replace the deployed models as-is.

## Real rice-yield evidence

The real-data pilot contains 544 historical district-year rice records across 17 districts and agricultural years 1981–82 through 2012–13. Development evaluation was restricted to the frozen 364-row, 13-district pool. Five overlapping grouped district splits were used; the reserved districts and latest years remain unscored. Inputs are annual weather, mapped soil estimates, and a year trend. This is retrospective annual district-level estimation, not a farm-level or in-season forecast.

| Development model | MAE (q/ha) | RMSE ± split SD (q/ha) | R² | 90% interval coverage | Mean interval width (q/ha) |
|---|---:|---:|---:|---:|---:|
| Year-trend control | 3.785 | 4.671 ± 0.716 | 0.278 | 89.3% | 16.914 |
| Random forest | 3.931 | 4.833 ± 0.771 | 0.226 | 96.0% | 19.205 |
| Simulated quantum kernel | 4.417 | 5.350 ± 0.830 | 0.058 | 92.4% | 20.060 |

The year-only control had lower mean error than the fitted models above. In the exploratory weather-contrast follow-up, the added calendar-half features worsened both classical controls; the simulated quantum model remained worse than the year-only control (RMSE 6.977 q/ha, R² −1.083). R² is not an accuracy percentage. Repeated splits overlap, so their standard deviation is descriptive, not a confidence interval.

The independent verification script recomputed saved predictions and metrics for the primary and feature-sensitivity studies and passed the stored hash, row-membership, and split checks. The weather-contrast verification also passed (15 score groups, 1,260 prediction rows); it confirms reproducibility of that development analysis, not external validity.

## Leaf-disease classifier

The shipped ONNX model loads and returns a normalized 38-class output across 14 crop names. No independent, labeled field-image test set is present, so its real-world accuracy is unknown. The separate training script defines 60 output classes, but its expanded training data/model are not present; its random image validation split is not an independent field test.

The inference code previously hard-rejected any output width other than 38 and treated outputs as probabilities, while the training model emits raw logits for its 60-class head. Inference now maps both known widths to the matching labels, converts raw scores to normalized probabilities, and reports the active class count and crop list. The checked-in model weights were not changed and remain 38-class.

## Checks performed

- 17 backend tests passed, including all six crop inference paths, interval/output contracts, synthetic out-of-range behavior, quantum-kernel checks, and new disease-model 38/60-class compatibility checks.
- Live API health returned `ok`; all six crop `predict/both` midpoint requests returned finite classical and quantum yields.
- Disease engine status reports ONNX Runtime ready, 38 classes, and 14 supported crop names.
- Independent real-rice result verifiers passed; final reserved outcomes were not scored.

## Conclusion and next data requirement

The application models currently work as software inference pipelines, but their yield scores are synthetic-only and the leaf classifier has no measured field accuracy here. The real rice pilot is not a validation set for the deployed field-input models, and it does not establish a quantum advantage. Do not report the deployed R² values as real-world accuracy or claim a 96%/100% real-data target.

To train and evaluate the six deployed crop models on real data, obtain documented, license-cleared crop-specific harvest yields joined to measurements of the same fields and seasons for the deployed inputs. The evaluation needs whole-farm/district/season holdouts and a fresh external test set, with that test kept untouched until the protocol and model selection are frozen.

## Reproduction artifacts

- [`RESEARCH_STATUS.md`](RESEARCH_STATUS.md)
- [`PILOT_RESULTS.md`](results/rice_pilot_development_20260925/PILOT_RESULTS.md)
- [`FEATURE_SENSITIVITY.md`](results/rice_feature_sensitivity_20260925/FEATURE_SENSITIVITY.md)
- [`WEATHER_CONTRASTS.md`](results/rice_weather_contrasts_20260927/WEATHER_CONTRASTS.md)
- [`report_verification.json`](results/rice_weather_contrasts_20260927/report_verification.json)
