# Research input data contract

## Supplied DLD archive staging

The supplied DLD tables have annual crop targets and monthly weather. They do not directly satisfy the district-season contract below. Preserve and stage them with:

```powershell
.\.venv\Scripts\python.exe research\prepare_dld_staging.py --archive C:\Users\PURNA\Downloads\RR_IND_2025_488.zip --raw-output research\data\raw\dld_20260924 --output research\data\processed\dld_staging_20260924
```

The command refuses existing output directories. It creates `annual_crop_records.csv`, `crop_exclusions.csv`, `monthly_weather_records.csv` and a checksummed manifest. The two boundary variants stay separate. Their reported targets are not replaced by production/area ratios. Review `research/audits/2026-09-24/DATA_PREPARATION.md` before joining or fitting. The manifest status `staging_only_boundary_and_time_alignment_unresolved` intentionally fails the benchmark's provenance gate.

## Earlier DES district-season contract

Keep downloaded raw data under `research/data/raw/`, including unchanged source files, metadata, retrieval timestamps, and checksums. Do not commit sensitive data or files whose license forbids redistribution. The current application data (`backend/data/crop_data.csv`) is synthetic and is not an input here.

Add `source_metadata.json` with an object per input source (`apy`, `district_centroids`, `crop_calendar`), each containing `source_url`, `retrieved_utc`, `license_or_terms`, `raw_filename`, and `raw_sha256`. For the district calendar also include the exact authority/reference for each crop-season-state date window. Preserve original downloads alongside normalized files; don't overwrite or modify the source file.

Normalize the source tables to these CSV schemas before running `prepare_panel.py`:

## `apy.csv`

One observation per source district/crop/season/year.

Required columns: `state,district,year,season,crop,area_ha,production_tonnes`. Optional `reported_yield_q_ha` is accepted only when directly sourced, in quintals/ha, and present for every retained row.

Keep DES source names and units. If the source is in a different unit, record the conversion in a data-preparation log and only then normalize. Normalize `year` to the crop-season start year and record the mapping for each source year label. Prefer a directly reported DES yield rate if the selected release offers it. If not, `yield_q_ha` is calculated as `production_tonnes * 10 / area_ha` and tagged as a derived ratio; it is never supplied by the synthetic app. DES warns reported yield may not exactly match this ratio. Do not mix reported and derived targets without a sensitivity analysis. If area is zero, missing, or invalid, row is excluded with a recorded reason.

## `district_centroids.csv`

Required columns: `state,district,district_id,latitude,longitude,boundary_vintage`.

One canonical district per row. IDs must be stable over the study period. `district` and `state` should match the harmonized APY table. Do not use changing names as IDs. Centroid coordinates and the boundary source must be cited. County/district aggregates are not farm observations.

## `crop_calendar.csv`

Required columns: `district_id,crop,season,start_month,start_day,end_month,end_day,calendar_source`.

Calendar windows must be supported by an authoritative district/crop-specific regional crop calendar or agronomist-reviewed source. Windows crossing New Year are supported by the preparation script. Do not tune dates against test outcomes. DES has noted its generic crop calendar was from 1998–99 and is under revision, so cite a current state/university source where possible.

## Weather and soil tables

`weather_daily.csv`: `district_id,date,t2m_c,t2m_max_c,precip_mm,rh2m_pct,source_version,retrieved_utc`.

`soil_district.csv`: `district_id,soil_nitrogen,soil_ph,soil_soc,soil_clay,depth_cm,statistic,source_version,retrieved_utc`.

Weather is sampled at a district centroid from NASA POWER daily Agroclimatology data. Soil is a static SoilGrids estimate, nominally 0–5 cm; record native units and scale conversions. For SoilGrids values, use the median (`Q0.50`) and divide by the property's documented scale factor. Retain Q0.05/Q0.95 or interval-width fields in an auxiliary provenance table if returned. Do not silently treat the SoilGrids estimate as a measured farm sample.

The processed panel produced by `prepare_panel.py` must contain:

`district_id,state,district,year,season,crop,area_ha,production_tonnes,yield_q_ha,soil_nitrogen,soil_ph,soil_soc,soil_clay,season_mean_temp_c,season_p95_max_temp_c,season_precip_mm,season_mean_rh_pct`.
