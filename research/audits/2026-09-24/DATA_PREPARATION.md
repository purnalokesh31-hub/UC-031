# DLD staging and documentation review

Reviewed 24 September 2026. No real-data model fitting or scoring has occurred.

## Completed

- Preserved nine selected archive members unchanged under `research/data/raw/dld_20260924`: two crop CSVs, four weather CSVs, the DLD manual, its digitized apportionment workbook and package README.
- Recorded SHA-256 checksums for the archive, each preserved member, the preparation script and all normalized CSV outputs.
- Created separate annual crop records for each boundary version, a row-level exclusion log and a monthly weather table under `research/data/processed/dld_staging_20260924`.
- Normalized hectares, tonnes and reported yield in quintals/ha. Kept production/area-derived yield only as a diagnostic; it does not replace reported yield.
- Passed 11 structural tests covering normalization, invalid values, duplicate keys and protected evaluation splits. Verified output checksums against the manifest.

## Row accounting

The scope is source records labelled Andhra Pradesh or Telangana, for Rice, Wheat, Maize, Cotton, Sugarcane and Groundnut.

| Item | Count |
|---|---:|
| Candidate crop records across both boundary versions | 14,520 |
| Positive area, production and reported yield | 9,128 |
| Excluded with explicit reasons | 5,392 |
| Monthly district weather records | 20,424 |
| Weather records failing finite-value, nonnegative water-variable or Tmax >= Tmin checks | 0 |
| Retained crop records with a reported/ratio yield difference above 5% | 251 |

The two crop versions overlap and are not independent observations. They must not be pooled to increase sample size. The counts above describe staging, not final training eligibility. No weather-to-crop join has been accepted yet.

## What the supplied documentation establishes

Page numbers below refer to physical PDF pages in `DLD-Apportioned-Data-Documentation.pdf`, not printed page numbers.

- Pages 8 and 23: crop missing observations use `-1`. Missingness can include unreported or unimportant crop activity. It must not be converted into zero yield.
- Page 10: area is in thousands of hectares, production in thousands of tonnes and yield in kg/ha. A crop year such as 1966 denotes 1966–67.
- Page 21: rice production is expressed as rice rather than unprocessed paddy. Cotton production is lint, converted from 170 kg bales. Sugarcane production is raw sugar/gur, described as 10% of cane production. The newer unapportioned export still needs its product definitions checked against this manual.
- Pages 6–7: the environment files are generated from pixels and are available only for unapportioned districts. They are not evidence of local weather-station measurements.
- Pages 7, 34 and 38: the apportioned data use historical district boundaries. Geographic allocation percentages cannot be reused as weights for averaging weather without further spatial justification.
- Package README pages 3–4 identifies ICRISAT-TCI DLD as the source and documents downloads in 2024/2025. Page 9 describes manual geographic aggregation for the package author's separate cotton study; that study's transformation choices are not automatically valid for ours.

These are descriptions of the supplied archive, whose checksum is recorded in the staging manifest. The older [2015 ICRISAT manual](https://vdsa.icrisat.org/Include/document/all-apportioned-web-document.pdf) independently documents the same general missing-code and historical-boundary conventions but is not a substitute for the supplied updated manual. Archive catalogue: <https://reproducibility.worldbank.org/index.php/catalog/409>.

## Findings requiring investigation

1. **Annual targets:** the six selected crop columns do not distinguish seasons. Do not reuse the season-based feature contract or invent a Kharif/Rabi label. Revise the study to annual district yield unless documented season-level data are acquired.
2. **Boundary changes:** retained Telangana rice has nine district codes in 2015 and 30 in 2016, then 32 in 2018. A district's numeric ID alone does not prove constant spatial support. The crosswalk lists several Telangana formation years as 2014 while the table expansion occurs later; verify dates against official district notifications before using it. Andhra Pradesh-to-Telangana boundary transfers also need review.
3. **Crosswalk representation:** `Apportionment.xlsx` is a single column with six consecutive cells per mapping. The archive's `c1_crosswalk_1966-2017.do` explains this representation. It is not a ready-to-join rectangular district table. No crosswalk weights were applied during staging.
4. **Time alignment:** the crop year spans two calendar years. Weather months remain keyed by their source year; do not join the same numeric years and call the result a complete agricultural-year exposure. Confirm the environment export's calendar convention and agricultural-year endpoints before aggregation.
5. **Outcome consistency:** 193 unapportioned Cotton, 19 Sugarcane, 15 Wheat, 8 Groundnut and 1 Maize records exceed a 5% reported-versus-ratio discrepancy. There are another 15 such records in the apportioned table. These are investigation flags, not automatic exclusions or evidence of incorrect reported yield. Rounding and source estimation methods may explain differences.
6. **Missing covariates:** these weather tables do not provide soil measurements, relative humidity or daily extremes. Do not substitute monthly maxima for the previous daily 95th-percentile feature. Review a weather-only baseline separately from the planned soil extension.
7. **External validation:** neither a second boundary version of the same DLD data nor an overlapping state-level rice export is an independent external yield test set.

## Next study decision

Start the data-alignment pilot with **annual rice yield**. The apportioned version retains 1,040 rice records in the selected states, and the unapportioned version 752. No retained rice record exceeds the 5% ratio-discrepancy flag. This is a data-quality observation, not a predictive score or proof of agricultural accuracy.

Before model fitting:

1. Resolve a common geographic support and a documented year-to-weather alignment, preserving every inclusion/exclusion decision.
2. Declare the annual feature set before test outcomes are scored. Add real soil inputs when a defensible spatial join is available; label mapped estimates accurately.
3. Finalize equal per-algorithm tuning budgets, fold-local target scaling and geographic/temporal split rules. The existing benchmark still needs the annual feature adapter and those fairness changes.
4. Freeze data, splits and code. Run development experiments first; reserve final evaluation for the fixed study.

The staging manifest deliberately has a status that the benchmark rejects. This prevents unfinished spatial and temporal joins from being reported as a real-data evaluation.
