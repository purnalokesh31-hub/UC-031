# Crop yield model research track

## Study status

Start with [RESEARCH_STATUS.md](RESEARCH_STATUS.md) for completed experiments, actual scores, and the remaining publication investigations.

This directory starts a separate, reproducible research track. It does not replace the application's active model. The active release was trained and evaluated on a formula-generated dataset, so its scores are development diagnostics only.

**Current pilot scope:** annual rice yield estimation for historical districts of undivided Andhra Pradesh, including areas now in Telangana. Unit of analysis is a historical district × agricultural year. This is retrospective district-level estimation, not a farm recommendation or an in-season forecast. The earlier district-season DES workflow remains available below as an unexecuted alternative.

**Current status: real-data development evaluation; not yet publication-ready.** The supplied World Bank archive contains ICRISAT-TCI district crop tables. The prepared pilot has 544 rice district-years across 17 historical district units, 1981–82 through 2012–13. Newly downloaded NASA POWER weather is aligned to June–May agricultural years at source-listed reference points. SoilGrids supplies static mapped topsoil estimates. Three of 20 districts are excluded because soil estimates are unavailable at the documented points. The ICAR state-level export is not used as independent validation. See `protocol/RICE_PILOT_PLAN.md` for the authoritative pilot design.

The exploratory scorer now uses only the frozen `fit` rows. It excludes reserved districts, calibration years and future years. Reserved scoring is a separate explicit stage, checks frozen evaluation-code hashes, and creates an exclusive started receipt beside the protocol. Existing protocols and output directories cannot be overwritten. These guards prevent accidental reuse, but do not make previously inspected data pristine.

**Data staging completed:** `prepare_dld_staging.py` preserves archive members and records units and exclusions. Its staging outputs are deliberately not accepted by the scorer. `prepare_rice_pilot.py` creates the separate validated annual panel from apportioned rice outcomes and newly retrieved covariates. Read `audits/2026-09-24/DATA_PREPARATION.md` for the source investigation. Reference points are not verified district centroids or area averages; static modern soil is not historical field measurement.

The executed protocol gives each tuned classical family, the simulated quantum kernel, and each quantum ablation **25 candidates** with identical grouped inner folds. Feature and target scalers fit within each training fold. Mean and year-only controls are untuned. Equal candidate counts do not imply equal computing time; fitting times are recorded.

## Current rice pilot workflow

The eight inputs are mapped soil nitrogen, pH, organic carbon and clay; annual temperature, rainfall and humidity; and a year trend. The outcome is the source-reported rice yield converted from kg/ha to q/ha. No crop area or production enters the features. See `data/processed/rice_pilot_1981_2012/manifest.json` for source hashes and exclusions.

`protocol/rice_pilot_lockbox.json` reserves four districts and the final three years. The development experiments use only 364 fit-role rows in 13 districts, with five outer district splits and separate calibration districts. Reserved scoring has not been run. The source data and covariate caches are ignored by Git; preserve them separately and review redistribution terms before release.

```powershell
# Preparation and freezing were already completed. Do not overwrite the frozen protocol.
$env:OMP_NUM_THREADS='2'
$env:OPENBLAS_NUM_THREADS='2'
$env:MKL_NUM_THREADS='2'
.\.venv\Scripts\python.exe research\benchmark.py --panel research\data\processed\rice_pilot_1981_2012\panel.csv --lockbox research\protocol\rice_pilot_lockbox.json --output research\results\NEW_UNIQUE_RUN
.\.venv\Scripts\python.exe research\report_pilot.py --results research\results\NEW_UNIQUE_RUN
```

The initial five-split run is `results/rice_pilot_development_20260925`. Its source snapshots and environment inventory identify the executed implementation. Read its `PILOT_RESULTS.md` once the run completes. Model scores describe district generalization and must not be presented as percentage accuracy.

## Additional development experiment: calendar-half weather contrasts

The 27 September follow-up adds fixed within-year weather contrasts, keeping the same development rows and tuning budgets. Read [its declared plan](protocol/RICE_WEATHER_CONTRASTS.md), [results](results/rice_weather_contrasts_20260927/WEATHER_CONTRASTS.md) and [failure diagnosis](results/rice_weather_contrasts_20260927/FAILURE_DIAGNOSIS.md). Both classical controls became worse; the simulated quantum model remained unstable. This result does not support deployment.

To reproduce in a fresh output directory, with archived inputs intact:

```powershell
$env:OMP_NUM_THREADS='2'
$env:OPENBLAS_NUM_THREADS='2'
$env:MKL_NUM_THREADS='2'
.\.venv\Scripts\python.exe research\weather_contrasts.py --output research\results\NEW_WEATHER_RUN
.\.venv\Scripts\python.exe research\report_weather_contrasts.py --results research\results\NEW_WEATHER_RUN
.\.venv\Scripts\python.exe research\diagnose_weather_contrasts.py --results research\results\NEW_WEATHER_RUN
```

The scorer refuses an existing directory, verifies the frozen sources, and never scores reserved outcomes. The report independently recomputes metrics and produces PNG/PDF comparison figures; the diagnostic uses saved development-only predictions and features.

## Earlier DES district-season source plan (not the executed pilot)

1. **Outcome:** Government of India, Directorate of Economics and Statistics (DES), district-wise, season-wise area (ha) and production (tonnes), annual from 1997. Prefer a source-reported yield rate if the official release provides one, after documenting its units and method. Otherwise the pipeline computes `10 × production_tonnes / area_ha` in quintals/ha and labels it a **derived production-to-area ratio**, not an official DES yield estimate. DES notes that reported yield rates may not exactly equal the production/area ratio because of rounding and estimation procedures. The OGD catalog says district, crop, season, year, area, and production are provided, and the resource carries the Government Open Data License—India. Check the resource's current terms, metadata, and raw column names at download time.
2. **Weather:** NASA POWER daily Agroclimatology point data, sampled once per unique district centroid (not once per crop). Retrieve T2M, T2M_MAX, PRECTOTCORR, and RH2M with explicit UTC dates and record the API request, response metadata, and retrieval date. Summarize over a documented crop-season window. POWER is gridded/reanalysis-derived weather at coarse spatial resolution, not a district rain gauge; centroid sampling is a limitation and must be described as such.
3. **Soil:** ISRIC SoilGrids point estimates for topsoil (0–5 cm): pH in water, total nitrogen, soil organic carbon, and clay. These are static modelled map estimates, not contemporary farm soil tests. Retain median and uncertainty fields when available; never describe these as field-measured.
4. **Geography/calendar:** `raw/district_centroids.csv` must contain stable `district_id`, canonical district/state names, centroid coordinates, and an explicit boundary vintage. `raw/crop_calendar.csv` must define the start and end date for every crop × season × district and cite the district/crop-specific calendar. The DES itself reports its calendar is old (1998–99) and under revision, so do not silently treat that generic calendar as current. Normalize source year labels to a documented season-start year. Historical names must be reconciled to one fixed boundary system before joining. When a historical district was split, only aggregate components back to the fixed geography when a documented boundary crosswalk makes that aggregation valid; otherwise exclude affected district-years and report the exclusion.

The selected eight model inputs are: `soil_nitrogen`, `soil_ph`, `soil_soc`, `soil_clay`, `season_mean_temp_c`, `season_p95_max_temp_c`, `season_precip_mm`, and `season_mean_rh_pct`. This is an explicit new research feature set. It intentionally does not reuse the app's synthetic N/P/K values as real measurements.

## Frozen research protocol

- Primary outcome: source-reported yield in quintals/ha where available; otherwise derived production-to-area ratio in quintals/ha. Keep the two provenance types explicit and do not mix them in one analysis without a sensitivity check. Keep only valid positive-area and positive-production rows; document all filtering and unit checks.
- Primary reserved evaluation: deterministically select 20% of canonical districts by a predeclared SHA-256 rule, without reading outcomes; never use those districts for tuning, fitting, or calibration. Separately reserve the latest **three complete crop-years** among development districts. Report (a) held-out districts in earlier years, (b) future years in known districts, and (c) the intersection of held-out districts and future years. `freeze_protocol.py` writes exact row-key assignments and hashes before benchmark scores are computed; review and preserve that file before running the scorer. These are rigorous geographic/temporal holdouts from the same source; they are **not an independent-source validation dataset**. A publication claiming independent external validation should add independently collected district or crop-cutting data if it can be obtained.
- Spatial robustness: development years only; grouped splits by canonical district ID. All rows from a held-out district stay out of that split's training data. Use five predeclared seeds and report every split, not just the best one.
- Model selection: same fold assignments, metric (RMSE), candidate count (25 settings per model family), and number of inner folds for all model families. Fit imputers/scalers/feature transforms inside each training fold. The primary baseline is the training-fold mean. Tuned classical families are Ridge, RBF-SVR, Random Forest, Extra Trees, and histogram gradient boosting. Quantum family is exact 4-qubit fidelity-kernel KernelRidge with frozen encoding variants and the same candidate budget. The quantum model is simulated classically; no quantum hardware or quantum advantage is claimed.
- Uncertainty: separate calibration districts/years from fitting; use split-conformal absolute residual intervals at nominal 90%. Report test coverage and mean interval width in q/ha. Also show cluster-bootstrap 95% intervals resampling districts, not individual rows.
- Metrics: per-crop MAE, RMSE, R², median absolute error, MAPE only where yield is safely positive, ±5% tolerance fraction (explicitly not classification accuracy), 90% interval coverage, interval width, and score dispersion across splits. Report macro-by-crop averages separately from pooled metrics.
- Ablations: quantum layer count, kernel centering, removing entanglement, and a matched classical RBF kernel control. Feature-set ablations (soil-only and weather-only) are a follow-on after the core panel and protocol are validated. Distribution shifts: held-out districts and latest seasons.
- Stop/go rule: do not make an accuracy claim until the frozen test is run successfully, dataset provenance is complete, and the district and temporal analyses agree with the stated task. A quantum win must be statistically stable across crop and split, survive the ablations, and beat the matched classical controls. Otherwise report no observed benefit.

## Earlier DES file workflow (not the executed pilot)

Place the DES APY table, canonical district centroids, and sourced crop-calendar windows under `research/data/raw/` as specified in `research/data/README.md`. Fetch weather and SoilGrids estimates by running the downloader below; it obeys ISRIC's five-request-per-minute fair-use limit and caches raw responses. Then run:

```powershell
.\.venv\Scripts\python.exe research\prepare_panel.py
.\.venv\Scripts\python.exe research\freeze_protocol.py --panel research\data\processed\panel.csv --output research\protocol\lockbox.json
# Inspect and preserve the protocol. Default scoring uses development rows only.
.\.venv\Scripts\python.exe research\benchmark.py --panel research\data\processed\panel.csv --lockbox research\protocol\lockbox.json --output research\results\candidate
```

Fetch inputs after adding and verifying the district centroids (use the DES release's actual first/last complete year):

```powershell
.\.venv\Scripts\python.exe research\fetch_covariates.py --start-year 1997 --end-year 2023
```

The benchmark requires a real-source preparation manifest and district/year keys, and writes software versions, hashes, per-split metrics, predictions, and limitations beside results. A metadata flag cannot independently prove provenance: source review is mandatory. After the study design and code are finalized, `--stage reserved` explicitly scores the reserved cohorts once, with a fresh output directory. A failed reserved run leaves a receipt for manual investigation; do not delete it to repeatedly inspect scores. Code changes after protocol freeze require documented protocol amendment before any reserved outcomes are inspected.

Reproduce the source inventory without changing the original archive:

```powershell
.\.venv\Scripts\python.exe research\audit_archive.py --archive C:\Users\PURNA\Downloads\RR_IND_2025_488.zip --output research\audits\new-audit
.\.venv\Scripts\python.exe -m unittest discover -s research\tests -v
```

## IEEE readiness checklist

- [ ] Research question and contribution distinct from prior crop-yield/QML studies; complete IEEE Xplore and cross-index literature search.
- [ ] Raw-source provenance, version/retrieval dates, licenses, transformations, units, geography crosswalk, missingness, and exclusions documented.
- [ ] Frozen temporal external test and grouped spatial analysis completed with no prior inspection of the lockbox.
- [ ] Baselines and quantum comparison use identical splits and model-selection budgets; uncertainty and ablations reported.
- [ ] Results are reproducible from a clean environment; data/code availability and limitations are ready.
- [ ] Venue scope and current author instructions checked; author list, permissions, conflicts, funding, AI-content disclosure (if generated material is included in the paper or supplement), and single-submission requirement handled by the authors.
- [ ] Independent agronomy review confirms outcome units, seasons, and interpretation before claiming agricultural usefulness.

IEEE acceptance cannot be guaranteed. IEEE reviewers assess scope, novelty, validity, data reporting, clarity, compliance, and advancement; the current synthetic application results do not meet the evidence threshold for those claims.

## Sources checked (2026-09-24)

- DES/OGD India crop-area and production resource (annual district/crop/season/year records; Government Open Data License—India): <https://data.gov.in/resource/district-wise-season-wise-crop-production-statistics-1997>
- NASA POWER Daily API documentation (parameter/time standards/point service): <https://power.larc.nasa.gov/docs/services/api/temporal/daily/>
- ISRIC SoilGrids documentation and property scales/depths/uncertainty: <https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html>
- ISRIC SoilGrids REST entry and fair-use limit: <https://rest.isric.org/>
- IEEE review criteria: <https://journals.ieeeauthorcenter.ieee.org/submit-your-article-for-peer-review/about-the-peer-review-process/>
- IEEE author responsibilities and originality: <https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/author-responsibilities/>
- IEEE submission and peer-review policy: <https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/guidelines-and-policies/submission-and-peer-review-policies/>
- DES notes on estimates/rounding and its official crop-calendar limitations: <https://desagri.gov.in/wp-content/uploads/2021/04/Pocket-Book-2019.pdf>, <https://desagri.gov.in/divisions-cell/special-data-dissemination-standards-sdds/>
- Example Government of Andhra Pradesh district/crop sowing and harvest schedule: <https://apagrisnet.gov.in/GO/2019/29-5-2019.PDF>
- Telangana DES agricultural-year/season definitions: <https://ecostat.telangana.gov.in/agricultural_Census.html>
- Related work already exists: <https://www.mdpi.com/2073-431X/13/8/191>, <https://journals.iub.edu.pk/index.php/JCIS/article/view/3052>, <https://www.frontiersin.org/journals/sustainable-food-systems/articles/10.3389/fsufs.2026.1827152/full>
