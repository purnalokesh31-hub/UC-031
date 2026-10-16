"""Build a documented annual rice pilot with point-proxy weather and mapped soil.

1981-82 through 2012-13 avoids the 2014 state-boundary transfers. Outcomes use
the archive's 1966-apportioned districts. This is post-year yield estimation.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
FEATURES = ["soil_nitrogen", "soil_ph", "soil_soc", "soil_clay",
            "annual_mean_temp_c", "annual_precip_mm", "annual_mean_rh_pct", "year_trend"]
PROPERTIES = {"nitrogen": ("soil_nitrogen", 100), "phh2o": ("soil_ph", 10),
              "soc": ("soil_soc", 10), "clay": ("soil_clay", 10)}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_responses(cache, provider, points_hash):
    manifest_path = cache / f"{provider}_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest["errors"] or manifest["points_sha256"] != points_hash:
        raise ValueError(f"Incomplete or mismatched {provider} acquisition manifest")
    responses = {}
    for item in manifest["responses"]:
        path = Path(item["path"])
        if digest(path) != item["sha256"]:
            raise ValueError(f"Corrupted source response {path}")
        if item["district_id"] in responses:
            raise ValueError("Duplicate response district")
        responses[item["district_id"]] = json.loads(path.read_text())
    return responses, manifest


def parse_soil(payload):
    layers = {layer["name"]: layer for layer in payload["properties"]["layers"]}
    result = {}
    for source, (target, scale) in PROPERTIES.items():
        layer = layers[source]
        if layer["unit_measure"]["d_factor"] != scale:
            raise ValueError(f"Unexpected SoilGrids conversion factor for {source}")
        depth = next(d for d in layer["depths"] if d["range"]["top_depth"] == 0 and d["range"]["bottom_depth"] == 5)
        for statistic, suffix in [("Q0.05", "_q05"), ("Q0.5", ""), ("Q0.95", "_q95")]:
            value = depth["values"].get(statistic)
            result[target + suffix] = np.nan if value is None else float(value) / scale
    return result


def annual_weather(payload, year):
    if payload["header"]["time_standard"] != "UTC":
        raise ValueError("Weather source must use the declared UTC convention")
    columns = ["T2M", "T2M_MAX", "PRECTOTCORR", "RH2M"]
    expected_units = {"T2M": "C", "T2M_MAX": "C", "PRECTOTCORR": "mm/day", "RH2M": "%"}
    for parameter, unit in expected_units.items():
        if payload["parameters"][parameter]["units"] != unit:
            raise ValueError(f"Unexpected {parameter} unit")
    data = pd.DataFrame(payload["properties"]["parameter"])[columns]
    data.index = pd.to_datetime(data.index, format="%Y%m%d")
    if data.index.duplicated().any():
        raise ValueError("Duplicate weather dates")
    dates = pd.date_range(f"{year}-06-01", f"{year+1}-05-31", freq="D")
    data = data.reindex(dates).replace(payload["header"]["fill_value"], np.nan)
    if not np.isfinite(data.to_numpy(float)).all():
        raise ValueError("Incomplete daily weather year; no implicit imputation")
    if (data.PRECTOTCORR < 0).any() or not data.RH2M.between(0, 100).all():
        raise ValueError("Invalid rainfall or humidity")
    return {"annual_mean_temp_c": float(data.T2M.mean()),
            "annual_precip_mm": float(data.PRECTOTCORR.sum()),
            "annual_mean_rh_pct": float(data.RH2M.mean()),
            "annual_p95_max_temp_c": float(data.T2M_MAX.quantile(.95)),
            "weather_days": len(data), "weather_start": dates[0].date().isoformat(),
            "weather_end": dates[-1].date().isoformat()}


def prepare(output):
    if output.exists():
        raise FileExistsError("Preserve existing pilot data; choose a fresh directory")
    point_path = ROOT / "district_reference_points.json"
    points = {p["district_id"]: p for p in json.loads(point_path.read_text())["points"]}
    cache = ROOT / "data/raw/pilot_covariates"
    nasa, nasa_manifest = load_responses(cache, "nasa", digest(point_path))
    soil, soil_manifest = load_responses(cache, "soilgrids", digest(point_path))
    if set(points) != set(nasa) or set(points) != set(soil):
        raise ValueError("Provider district sets differ from the documented point inventory")
    staging = ROOT / "data/processed/dld_staging_20260924"
    source_manifest = json.loads((staging / "manifest.json").read_text())
    crop_path = staging / "annual_crop_records.csv"
    if source_manifest["output_sha256"][crop_path.name] != digest(crop_path):
        raise ValueError("Staged crop checksum mismatch")
    crops = pd.read_csv(crop_path, dtype={"source_district_id": str})
    source = crops[(crops.variant == "Apportioned") & (crops.crop == "Rice") &
                   crops.source_year.between(1981, 2012)].copy()
    if set(source.source_district_id) != set(points):
        raise ValueError("Rice geography differs from documented points")
    records, exclusions, soil_records = [], [], []
    for district, group in source.groupby("source_district_id"):
        soil_values = parse_soil(soil[district])
        soil_records.append({"source_district_id": district, **soil_values})
        for row in group.itertuples():
            reason = None
            if not np.isfinite([soil_values[c] for c in FEATURES[:4]]).all():
                reason = "missing_soil_map_estimate_at_documented_point"
            try:
                weather = annual_weather(nasa[district], int(row.source_year))
            except ValueError as exc:
                reason = str(exc) if reason is None else reason + ";" + str(exc)
            if reason:
                exclusions.append({"source_district_id": district, "year": row.source_year, "reason": reason})
                continue
            records.append({"district_id": f"DLD1966-{district}", "source_district_id": district,
                            "district": row.source_district, "state": row.source_state,
                            "year": int(row.source_year), "season": "annual", "crop": "Rice",
                            "yield_q_ha": row.reported_yield_q_ha, "year_trend": int(row.source_year),
                            **{c: soil_values[c] for c in FEATURES[:4]}, **weather,
                            "reference_latitude": points[district]["latitude"],
                            "reference_longitude": points[district]["longitude"]})
    data = pd.DataFrame(records).sort_values(["district_id", "year"])
    if data.district_id.nunique() < 15 or data.duplicated(["district_id", "year"]).any():
        raise ValueError("Insufficient distinct districts or duplicate panel keys")
    output.mkdir(parents=True)
    panel = output / "panel.csv"
    data.to_csv(panel, index=False)
    pd.DataFrame(exclusions, columns=["source_district_id", "year", "reason"]).to_csv(output / "exclusions.csv", index=False)
    pd.DataFrame(soil_records).to_csv(output / "soil_uncertainty.csv", index=False)
    manifest = {
        "status": "prepared_real_source_inputs_not_yet_independently_validated",
        "study": "annual_rice_point_proxy_pilot_1981_2012", "created_utc": datetime.now(timezone.utc).isoformat(),
        "panel_sha256": digest(panel), "features": FEATURES, "rows": len(data),
        "districts": int(data.district_id.nunique()), "exclusions": exclusions,
        "scope": "1966-apportioned districts within the historical undivided Andhra Pradesh region",
        "yield_derivation": "Source-reported rice yield kg/ha divided by 100; rice, not unprocessed paddy",
        "period_definition": "June 1 in source year to May 31 next year; annual is a period marker, not a reported crop season",
        "cutoff_reason": "Last target 2012-13 precedes 2014 state-boundary transfers and 2016 district reorganization",
        "calendar_source": "https://ecostat.telangana.gov.in/agricultural_Census.html",
        "boundary_sources": ["https://medchal-malkajgiri.telangana.gov.in/history/",
                             "https://telangana.gov.in/wp-content/uploads/2023/05/Statistical-Year-Book-2015.pdf"],
        "raw_sha256": {"archive": source_manifest["archive_sha256"], "staged_crops": digest(crop_path),
                       "reference_points": digest(point_path), "preparation_code": digest(Path(__file__)),
                       "dld_manual": source_manifest["sources"]["DLD-Apportioned-Data-Documentation.pdf"]["sha256"]},
        "source_cache_sha256": {item["path"]: item["sha256"] for m in [nasa_manifest, soil_manifest] for item in m["responses"]},
        "source_manifests": {"nasa": nasa_manifest, "soilgrids": soil_manifest},
        "limitations": ["Retrospective post-agricultural-year estimation, not a forecast",
                        "Historical district yield is an aggregate, not a farm target",
                        "Coarse NASA reanalysis at source-listed reference points, not district area averages",
                        "SoilGrids topsoil median is a static modern map estimate, not historical measured soil",
                        "Documented reference points are not verified cropland centroids",
                        "Soil or point-location bias must be examined through feature and spatial sensitivity analyses",
                        "Year trend controls technology/time effects but does not measure management or cultivar",
                        "Reserved subsets from this dataset are not independent external validation"],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"panel": str(panel), "rows": len(data), "districts": int(data.district_id.nunique()),
                      "excluded": len(exclusions), "features": FEATURES}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed/rice_pilot_1981_2012")
    args = parser.parse_args()
    prepare(args.output)
