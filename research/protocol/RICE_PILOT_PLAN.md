# Annual rice pilot: analysis plan

Written before scoring this real-data pilot, 24 September 2026.

## Scope and data decisions

- Outcome: source-reported annual rice yield, kg/ha converted to quintals/ha, from the archive's 1966-apportioned DLD table. Rice is not unprocessed paddy.
- Region: historical districts within undivided Andhra Pradesh, including areas now in Telangana.
- Years: 1981-82 through 2012-13. NASA weather availability determines the start. The end precedes the 2014 state-boundary transfers and the 2016 district reorganization, and was chosen without model scores.
- Spatial covariates: fixed reference coordinates transcribed from ICRISAT Appendix 4, physical PDF pages 47, 48, 70. They are not claimed to be cropland centroids or representative district averages.
- Weather: NASA POWER daily UTC MERRA-2-derived variables. Require every day from June 1 to May 31 next year; no missing-day rainfall summation or imputation. Aggregate mean T2M, total corrected precipitation and mean RH2M. Store daily Tmax 95th percentile for later explicitly labelled sensitivity work.
- Soil: SoilGrids 0–5 cm median nitrogen, pH, organic carbon and clay; preserve 5th and 95th quantiles. Values are modern static mapped estimates, not historical soil measurements.
- Source coverage: 20 documented reference points queried. Three have missing soil estimates and are excluded without relocating them to find convenient values. The resulting primary pilot has 544 district-years in 17 districts.
- Inputs: the four mapped soil properties, annual temperature/rainfall/humidity, and year as a technology/time trend proxy. No production, crop area, target-derived ratio, district ID, or target-lag input enters the models.
- Interpretation: retrospective annual district yield estimation; not an operational forecast or farm recommendation. Geographic and temporal tests from this source are not independent-source external validation.

## Evaluation

The machine-readable protocol is frozen from the panel before scoring. Reserve approximately 20% of districts using the predeclared SHA-256 ID ordering. Reserve the latest three years among remaining districts. Reserve the preceding year for calibration.

Development runs use only the frozen fit role. Outer district splits use seeds 17, 29, 41, 53, 67 and a 20% district holdout. A further 20% of remaining districts is reserved for conformal calibration. Hyperparameters use district-grouped inner CV with up to five folds and RMSE selection. No reserved geographic or future cohort is scored in this development run.

Each tuned family has 25 candidate configurations: Ridge, RBF SVR, random forest, Extra Trees, histogram gradient boosting, RBF kernel ridge, exact simulated quantum fidelity kernel, and three quantum ablations (no entanglement, one layer, no kernel centering). Classical feature and target scalers are fitted within training folds; the quantum estimator likewise scales features and targets during each fit. Mean and linear year-trend baselines are untuned controls.

Report all families and all splits. Save CV settings, best parameters and fitting times. Primary error measures are MAE and RMSE; also report R², median absolute error, MAPE, explicitly labelled ±5% tolerance fraction, and empirical coverage/width of nominal 90% residual intervals. Geographic shift breaks exchangeability, so nominal coverage is not guaranteed. Repeated splits overlap and their SD is descriptive, not an independent-sample significance test. Paired error differences use district-cluster bootstrap intervals, with only a few held-out districts per split; interpret those intervals cautiously and do not use them as definitive evidence of superiority.

## Decisions after development

Do not tune toward a desired percentage or inspect the final cohorts to choose a model. Diagnose feature quality, trend dependence and spatial sensitivity on development data. A weather-only/no-soil sensitivity analysis, point-location sensitivity, richer classical baselines where justified, external yield data and an agronomic review remain required before a strong publication claim. Any amended study design must be documented before final evaluation.

No quantum-computing advantage is claimed. These are exact quantum-kernel calculations on a classical machine.

## Sources

- Supplied archive: https://reproducibility.worldbank.org/index.php/catalog/409
- Agricultural year: https://ecostat.telangana.gov.in/agricultural_Census.html
- District reorganization: https://medchal-malkajgiri.telangana.gov.in/history/
- 2014 boundary amendment reproduced in: https://telangana.gov.in/wp-content/uploads/2023/05/Statistical-Year-Book-2015.pdf
- NASA daily API: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- SoilGrids units and uncertainty: https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html
