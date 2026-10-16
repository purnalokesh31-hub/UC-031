# Research status — updated 6 October 2026

## Completed

- Prepared a real-source annual rice pilot: 544 district-years, 17 historical district units, agricultural years 1981–82 to 2012–13. Source hashes, daily weather completeness, units, exclusions and mapped-soil uncertainty are retained.
- Froze geographic and future-year reservations. Development experiments use only 364 rows from 13 districts.
- Completed 60 primary evaluations: 12 models/controls across five district splits, with 25 candidates per tuned family.
- Completed 45 further evaluations removing soil, year, or both for three predeclared linear/kernel models. All use the same outer assignments and tuning budgets.
- Passed 19 automated checks including independent Qiskit circuit equivalence, kernel properties, split isolation, target units and complete weather years.
- Saved predictions, tuning settings/times, paired comparisons, source snapshots, package versions, reports and a scientific comparison figure.

## What the results say

Five overlapping development splits; mean values below are exploratory, not final-test estimates. RMSE is q/ha (lower is better); R² is not percentage accuracy.

| Model/input condition | RMSE | Mean R² |
|---|---:|---:|
| Year trend only | 4.671 | 0.278 |
| Random Forest, all inputs | 4.833 | 0.226 |
| Main simulated quantum kernel, all inputs | 5.350 | 0.058 |
| Ridge, weather + year (soil removed) | 4.621 | 0.292 |

The full-feature quantum model did not establish an improvement over classical controls. Its 90% intervals covered 92.4% of observations, but averaged 20.06 q/ha in width. Coverage must be interpreted alongside interval width and prediction error.

All three weather-only models had negative mean R². Removing year also produced negative mean R² for all three. Removing soil helped Ridge and classical RBF kernel ridge, but made the simulated quantum model unstable (RMSE 7.252 ± 4.527 q/ha across splits). The fixed eight-slot circuit was retained in these ablations; other encodings are not evaluated.

These results suggest dependence on the year trend and weak transfer of the present environmental inputs across districts. They do not identify a causal explanation. The tiny apparent improvement of weather-plus-year Ridge over year-only is insufficient to establish agricultural usefulness or superiority.

## Artifacts

- [Primary results](results/rice_pilot_development_20260925/PILOT_RESULTS.md)
- [Comparison figure](results/rice_pilot_development_20260925/development_comparison.png)
- [Feature sensitivity](results/rice_feature_sensitivity_20260925/FEATURE_SENSITIVITY.md)
- [Frozen primary plan](protocol/RICE_PILOT_PLAN.md)
- [Feature sensitivity plan](protocol/RICE_FEATURE_SENSITIVITY.md)
- [Initial literature investigation](LITERATURE_INVESTIGATION.md)

## Next investigation, before consuming final tests

1. **Spatial input validity:** obtain documented historical polygons/cropland support and evaluate area-based weather summaries. The current points are source-listed locations, not verified representative district averages. Do not claim polygon support from a name match.
2. **Target/calendar alignment:** retain annual rice labels unless independently sourced seasonal outcomes are available. Assess monthly or agricultural-quarter climate summaries on development rows, rather than inventing crop-season labels.
3. **Missing predictors and stronger controls:** investigate source-documented irrigation/management information and contemporary vegetation features where temporally valid. Retain year-only, simple linear and strong classical controls. Modern static soil is not a historical measurement.
4. **Generalization evidence:** expand documented geography and obtain a genuinely independent yield source, with overlap and boundary audits. The state-level ICAR export and another copy of DLD do not establish independent external validation.
5. **Research contribution:** complete the closest-paper review. A transparent negative-results/generalization study is a possible direction, but novelty is not established by this pilot.

Declare each design amendment before running it. Retain all earlier findings and keep the current reserved cohort unscored while developing the study. New data require explicit overlap checks; do not accidentally expose the original reserved outcomes through another source.

## Publication decision

**Not ready for submission.** There is no defensible 96–100% accuracy claim, demonstrated quantum advantage, independent external validation or established novel contribution. The work now has a reproducible pilot and evidence of its limitations. A paper may become viable after the investigations above, even if quantum performance remains negative, provided the scientific contribution is substantive. No model has been activated in the application and no manuscript has been submitted.

## Update — 26 September 2026

Audited the supplied `Rice_Data_2026-09-24.csv` for file integrity, structure, internal yield/area consistency, source documentation, and suitability for external validation. It contains 1,844 state-year records for 35 labels spanning 1966–2025, but is state-level only and overlaps the Andhra Pradesh/Telangana region and years covered by the district pilot. ICAR-IIRR's published database description lists state-level years 1997–2023 and all-India years 1966–2023, which does not match this export's stated range. The CSV is therefore excluded from model fitting and external-test claims until its exact export version, source documentation, license, and boundary definitions are verified. No model was run and no reserved outcomes were compared. See [the full file audit](audits/2026-09-26/ICAR_STATE_RICE_CSV_AUDIT.md).

Next: obtain a documented independent district- or farm-level yield dataset and resolve the ICAR export's metadata. Keep the frozen reserved cohort unscored until a new-source overlap protocol is recorded.

The data-source investigation found the official General Crop Estimation Survey / crop-cutting experiment system as the closest lead: NSC documents plot-harvest measurements used to estimate district/state yields, and Telangana DES documents plot-yield, input, and irrigation schedules. No public plot-level download was identified from those pages. These records may underlie the APY labels, so they are not automatically independent. A [data request draft](data/CCE_DATA_REQUEST_TEMPLATE.md) is ready for separate requests to the Andhra Pradesh and Telangana Directorates of Economics & Statistics, asking for anonymized records or district-season summaries, sampling metadata, lineage to the APY series, boundary definitions, and publication terms. Do not use any received records as external test data until source overlap is resolved.

## Update — literature scan, 26 September 2026

A targeted primary-source search found prior work on Indian district-level rice prediction (247 districts, 2001–2020), quantum-assisted rice forecasting (2024), and quantum-ensemble crop-yield regression (2026). This rules out broad novelty claims such as “first quantum crop-yield model,” “first quantum rice forecast,” or “first Indian district rice model.” The literature note now records the overlap and what must still be compared. A possible contribution remains a rigorous, well-documented shift evaluation of a simulated quantum kernel against matched classical controls, but novelty is not established. The search was not systematic or complete across IEEE Xplore, Scopus, and Web of Science.

## Update — weather timing investigation, 27 September 2026

Completed 15 additional development evaluations under a [declared design amendment](protocol/RICE_WEATHER_CONTRASTS.md): added June–November minus December–May temperature, rainfall and humidity contrasts to annual weather plus year. These calendar halves are not crop-season labels. All three linear/kernel families retained the original 25 candidates and five district splits; reserved outcomes remain unscored. This amendment was chosen after earlier development results and is exploratory.

| Model | Prior annual-weather/year RMSE | With contrasts RMSE | With contrasts mean R² |
|---|---:|---:|---:|
| Ridge | 4.621 | 4.769 | 0.248 |
| Classical RBF kernel ridge | 4.838 | 5.221 | 0.075 |
| Quantum kernel simulated classically | 7.252 | 6.977 | -1.083 |

All RMSE values are q/ha, averaged across five overlapping splits. The unchanged year-only control remains 4.671 q/ha. The added features worsened both classical controls. They modestly reduced the quantum model's mean error relative to its without-soil baseline, but instability and poor transfer remain; this is not evidence of a useful improvement or superiority. Its mean interval coverage was 86.9%, with mean width 22.916 q/ha.

An independent report script recomputed all 15 split score groups from 1,260 saved prediction rows, verified aggregate scores and original output hashes. A post-hoc diagnostic found the largest quantum error at seed 41 in historical district DLD1966-54 (RMSE 22.220 q/ha). That split selected alpha=1e-8, and 82.1% of that district's test rows were outside at least one training-feature min/max. These are descriptive associations, not a causal explanation.

- [Full results](results/rice_weather_contrasts_20260927/WEATHER_CONTRASTS.md)
- [Comparison figure](results/rice_weather_contrasts_20260927/weather_contrast_comparison.png)
- [Failure investigation](results/rice_weather_contrasts_20260927/FAILURE_DIAGNOSIS.md)
- [Independent score verification](results/rice_weather_contrasts_20260927/report_verification.json)

Next technical investigation: declare a matched, more conservative regularization/model-selection comparison for classical and simulated quantum kernels, without choosing thresholds from these outer errors. In parallel, the documented spatial-support, management-data and independent-source gaps still need resolution. Do not consume the final tests or deploy this experimental model. The application continues to use its existing synthetic-data release; the UI redesign does not establish improved predictive accuracy.

## Update — real rice field-survey source, 6 October 2026

Downloaded and checksum-verified the public CC0 CIMMYT/CSISA rice field survey (45,643 records across six South Asian regions; deposited harvest-yield labels are mostly farmer-reported, with crop cuts in documented subsets). The CSV's generic app features only partially align: applied N, applied P₂O₅/K₂O, and mapped SoilGrids pH are available, while soil moisture, temperature, and humidity are absent; the precipitation field is calendar-year total and does not match the app's unqualified rainfall input.

An exploratory model benchmark retained 31,181 complete rows after exposed crop/season/yield/rate/duration/soil filters and left out one underlying survey collection at a time. Best fixed recipes reached MAE about 10.3 q/ha, RMSE about 13.2 q/ha, and R² about 0.30. A whole-region holdout fell to R² −0.17 for a fixed ensemble, with MAE 13.9 q/ha. This is not enough for field-specific deployment. A partial-input example for the dashboard's N=100, P=50, K=50, pH=6.3 values gave roughly 45–48 q/ha under different P/K unit assumptions, but its 90th-percentile absolute grouped error was about 22 q/ha, and it ignores four UI fields. These are exploratory outputs, not validated real-harvest estimates.

- [Real-rice input benchmark and current-sample interpretation](REAL_RICE_INPUT_BENCHMARK_20261006.md)
- [Benchmark script](benchmark_cimmyt_rice_input_subset.py)
- [Dataset provenance, codebook mapping, license and checksum](data/external/cimmyt_rice_2026/README.md)

The synthetic active release was not changed, and the quantum model was not evaluated on this rice survey. Continue to treat all active app yield scores as synthetic-only until a feature-aligned, independently measured external harvest test is available.
