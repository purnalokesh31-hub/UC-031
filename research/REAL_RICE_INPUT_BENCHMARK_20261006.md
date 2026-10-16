# Real rice-input benchmark — 6 October 2026

## What I ran

I acquired the public CIMMYT/CSISA South Asia rice survey (45,643 field records, 136 columns) and its variable codebook. The repository marks it CC0 1.0. File MD5s match the repository metadata; provenance and feature definitions are in [`data/external/cimmyt_rice_2026/README.md`](data/external/cimmyt_rice_2026/README.md).

I filtered to monsoon, transplanted rice and applied the published plausible yield, nitrogen-rate, and crop-duration bounds where the harmonized file exposes those fields. I retained 31,181 rows with usable target and the four input fields used below. This is a transparent re-analysis of the currently deposited version, not an exact reproduction of the paper’s 28,865-row analysis: I could not reproduce its coordinate-in-region polygon check from this package. The harmonized file also does not identify which individual yield records used crop cuts.

The outcome `yield_kg_ha` is a mix of farmer-reported and crop-cut harvest yields. The source article reports that most observations are farmer-reported, with crop cuts for about 40% of Bangladesh floodplain yields and about 25% of Punjab/Haryana yields. These are real field-survey harvest records, but they are not all independently measured crop cuts.

## Evaluation

The main holdout leaves one underlying survey collection out at a time (11 survey groups). No row identifier, region, or year is used as a predictor. The second evaluation leaves out each entire region (six regions). Models use fixed, untuned configurations and the same held-out groups; scores are exploratory and no model was promoted to the application.

| Inputs available in the rice survey | Holdout | Model | MAE | RMSE | R² |
|---|---|---|---:|---:|---:|
| Applied N, P₂O₅, K₂O + SoilGrids pH | survey collection | Random forest | 10.34 q/ha | 13.23 q/ha | 0.297 |
| Applied N, P₂O₅, K₂O + SoilGrids pH | survey collection | Histogram gradient boosting | 10.39 q/ha | 13.22 q/ha | 0.298 |
| Same four inputs | survey collection | Training-set median baseline | 13.27 q/ha | 16.71 q/ha | −0.122 |
| Same four inputs | whole region | Fixed mean ensemble | 13.86 q/ha | 17.07 q/ha | −0.171 |

The 90th percentile absolute error for the fixed ensemble on survey-collection holdouts was 22.08 q/ha. This is a descriptive error scale, not a calibrated prediction interval. Whole-region holdout performance is poor: R² is negative overall, and Punjab/Haryana error is especially large. The model does not generalize reliably enough to support farm-specific harvest advice.

Adding the closest available precipitation field did not improve the fixed ensemble: MAE rose from 10.99 to 11.28 q/ha on survey holdouts. This field is annual calendar-year CHIRPS precipitation; it is not semantically equivalent to CropGuard’s 0–500 mm rainfall input.

## Your current sample values

Using the current rice sample from the app (N=100, P=50, K=50 kg/ha; pH=6.3), a research-only four-input model gives the following conditional outputs:

| Interpretation of the generic P/K entries | Fixed model-mean estimate |
|---|---:|
| P and K mean fertilizer-label P₂O₅ and K₂O rates | 45.1 q/ha (4.51 t/ha) |
| P and K mean elemental P and K, converted to P₂O₅/K₂O | 48.2 q/ha (4.82 t/ha) |

These numbers use only N rate, P₂O₅ rate, K₂O rate, and pH. Model-family predictions span 42.4–48.7 q/ha under the first unit interpretation and 39.5–53.7 q/ha under the second. The grouped holdout MAE for the displayed fixed mean is 10.99 q/ha and its 90th-percentile absolute error is 22.08 q/ha, so the point number is much more precise-looking than the available evidence warrants.

The app’s soil moisture, temperature, humidity, and rainfall entries were omitted because this dataset has no matching measurements. It contains SoilGrids pH for topsoil at 0–5 cm, not field-lab soil pH. The app’s generic P/K units do not specify oxide versus elemental rates; if they represent soil-test nutrient concentrations rather than fertilizer application rates, they are not compatible with this dataset at all. Location, season, and management timing are also absent from the current estimate, despite strong regional differences in held-out errors.

## Decision

**Do not present 45.1 or 48.2 q/ha as a verified real-harvest estimate or deploy this partial model in place of the app model.** They are exploratory conditional predictions from a partially matched dataset. The honest answer for the exact eight current form values remains: there is not enough feature-aligned, field-level evidence to produce a validated real-harvest estimate.

The live app’s existing rice score remains based on synthetic training data; its validation scores cannot be called real-world accuracy. This benchmark did not validate the exact quantum-kernel model or demonstrate a quantum-computing advantage. A useful deployable model needs clearly defined fertilizer-vs-soil-test units, field location/season, weather with a matching period, and a crop-cut or otherwise independently verified external harvest set.

## Reproduction outputs

- Script: [`benchmark_cimmyt_rice_input_subset.py`](benchmark_cimmyt_rice_input_subset.py)
- Raw and per-survey held-out metrics, predictions, and the input-scenario JSON: [`results/cimmyt_rice_input_only_20261006`](results/cimmyt_rice_input_only_20261006)

## Sources

- Dataset and license: [CIMMYT Dataverse record, version 3.1](https://data.cimmyt.org/dataset.xhtml?persistentId=hdl%3A11529%2F10549105&version=3.1)
- Study methods and measurement caveats: [Coggins et al., *Nature Sustainability* (2025)](https://www.nature.com/articles/s41893-024-01496-3)
