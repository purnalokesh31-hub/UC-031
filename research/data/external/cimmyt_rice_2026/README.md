# CIMMYT South Asia rice field survey

## Source and reuse

- Dataset: [Farmer field survey dataset underpinning “Data-driven strategies to improve nitrogen use efficiency of rice farming in South Asia”](https://data.cimmyt.org/dataset.xhtml?persistentId=hdl%3A11529%2F10549105&version=3.1)
- Citation: Coggins et al. (2024), CIMMYT Research Data & Software Repository Network, version 3.1, persistent identifier [hdl:11529/10549105](https://hdl.handle.net/11529/10549105).
- License: CC0 1.0 Public Domain Dedication, as stated in the repository record.
- Files downloaded 2026-10-06:
  - `NUE_survey_dataset_v2.csv` — 45,643 rows, 136 columns, 32,514,678 bytes; MD5 `c7223de8068f16284f3768408f1730a0` (matches repository metadata).
  - `Variable_Details_v2.xlsx` — variable definitions; 15,808 bytes; MD5 `64b6b4c91f04504bc9588a916e7a9f79` (matches repository metadata).

## Important limitations for CropGuard

The data are field survey records from 2016–2021 across six South Asian rice regions. Most yields are farmer-reported. The paper reports crop-cut measurements for about 40% of Bangladesh floodplain yields and about 25% of Punjab/Haryana yields; the harmonized CSV does not identify the measurement method for each row. The target is therefore a mix of self-reported and crop-cut yield records, not a crop-cut-only ground truth.

The available near-matches are applied nitrogen (`N_kg_ha`), applied phosphorus as P2O5 (`P2O5_ha`), applied potassium as K2O (`K2O_ha`), topsoil pH(H2O) from SoilGrids at 0–5 cm, and calendar-year CHIRPS precipitation (`total_precip`). Soil moisture, temperature, and relative humidity are absent. The weather precipitation variable is not equivalent to an unqualified 0–500 mm rainfall form field, and SoilGrids pH is not a plot-level lab measurement. The UI's generic P/K units are ambiguous relative to P2O5/K2O.

Do not replace the deployed model or describe its output as a verified field harvest estimate using this dataset without resolving those feature definitions, adding location/season context, and obtaining external evaluation on independent field records.

## Benchmark

The reproducible exploratory analysis is in `research/benchmark_cimmyt_rice_input_subset.py`. Its outputs are under `research/results/cimmyt_rice_input_only_20261006/`. It follows the paper's published crop, season, yield, N-rate, and duration filters where exposed in the data package; it does not reproduce the coordinate-in-region polygon check because those polygons/code are not included here. All hyperparameters are fixed in advance for this comparison; holdouts leave one survey collection and, separately, one region out. Outputs remain research-only and are not wired into the deployed service.
