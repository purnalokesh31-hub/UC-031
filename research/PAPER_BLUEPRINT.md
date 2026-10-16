# Proposed paper blueprint

## Working title

**Spatially and Temporally Held-Out Evaluation of Quantum Fidelity-Kernel and Classical Models for District-Level Crop Yield Estimation in Southern India**

This is a working title only. It should change if the final experiment does not support the question or if the literature search shows insufficient novelty.

## Research question

For annual rice yields on a fixed historical district geography, does an exact four-qubit fidelity-kernel regressor, simulated on a classical computer, generalize better than classical regressors given equal candidate budgets to unseen districts and later agricultural years? Do its prediction intervals retain nominal coverage under those shifts?

## Contributions to establish (not assume)

1. A provenance-traced annual rice panel on 1966-apportioned district units, joined to June–May reference-point weather and explicitly labelled static soil-map estimates. The current 17-district historical pilot is a feasibility study, not sufficient evidence of broad geographic applicability.
2. A label-blind geographic lockbox and a separate temporal lockbox, with a joint geographic-plus-temporal stress test.
3. A budget-matched comparison of classical regression, a classical RBF-kernel control, and an exact simulated quantum fidelity kernel; grouped model selection and calibrated intervals.
4. Evidence about where each family fails, including negative or inconclusive quantum findings.

If the data cannot support these claims, narrow the paper to a reproducibility/benchmark study or stop. Don't invent a new model name to create novelty.

## Paper sections

1. **Introduction:** practical scope; distinction between district estimation and farm forecasting; concise gap statement; contributions.
2. **Related work:** district-level crop-yield prediction; spatial/temporal leakage and validation; quantum kernels in classical-data learning; existing quantum/agriculture studies. Search IEEE Xplore plus Crossref/Scopus/Web of Science before freezing novelty claims.
3. **Data:** source agency, release date, licenses, yield units and formula, boundary vintage and crosswalk, season calendars, NASA POWER point sampling, SoilGrids properties and uncertainty, missingness, complete row flow diagram.
4. **Methods:** feature definitions, exact quantum feature map and classical simulator, baselines, 25-configuration tuning budgets, group CV, frozen role keys, conformal calibration, bootstrap scheme, ablations.
5. **Results:** panel description first; per-crop spatial and temporal metrics; paired comparisons and uncertainty; interval coverage/width; ablations; runtime/memory only with machine details.
6. **Discussion:** domain shift, data quality, aggregate-target limits, no demonstrated quantum advantage unless separately established, applicability boundaries.
7. **Reproducibility:** code version/commit, environment lock, source and output hashes, split lockbox, data statement, limitations, conflict/funding/author contribution statements.

## Planned tables and figures

- Source/feature table with source resolution, units, temporal scope, spatial support, and uncertainty.
- Crop × split panel counts and coverage / exclusion audit.
- Per-crop MAE, RMSE, R², interval coverage and width with district-cluster 95% intervals.
- Paired quantum-minus-classical error differences on exactly the same rows.
- Quantum ablation table and grouped prediction-error plots by year and district.
- Map of train/development vs geographic lockbox districts, sourced boundary only.

## Claims to avoid

- “100% accurate,” “97% accurate,” or converting R²/within-tolerance into generic accuracy.
- Farm-level agronomic advice from district aggregates or static mapped soil at reference points.
- “Forecast” when the model uses full-season weather; call it post-season estimation.
- “Quantum advantage,” hardware speedup, or real-quantum execution for exact classical statevector results.
- “External validation” for a held-out subset from the same data source without explaining the source boundary.
- Any field-validation claim based on the synthetic app dataset.
