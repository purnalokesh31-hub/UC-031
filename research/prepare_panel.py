"""Join normalized public inputs into a district-season yield panel.

This script does not download or invent observations. See research/data/README.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
WEATHER_FEATURES = ["season_mean_temp_c", "season_p95_max_temp_c",
                    "season_precip_mm", "season_mean_rh_pct"]
SOIL_FEATURES = ["soil_nitrogen", "soil_ph", "soil_soc", "soil_clay"]
FEATURES = SOIL_FEATURES + WEATHER_FEATURES


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def source_cache_hashes(raw: Path) -> dict:
    cache = raw / "source_cache"
    if not cache.exists():
        return {}
    return {str(path.relative_to(raw)): sha256(path)
            for path in sorted(cache.rglob("*")) if path.is_file()}


def season_dates(year: int, start_month: int, start_day: int,
                 end_month: int, end_day: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = pd.Timestamp(year=int(year), month=int(start_month), day=int(start_day))
    end_year = int(year) + (1 if (int(end_month), int(end_day)) <
                            (int(start_month), int(start_day)) else 0)
    end = pd.Timestamp(year=end_year, month=int(end_month), day=int(end_day))
    if end < start:
        raise ValueError("Invalid calendar window")
    return start, end


def prepare(raw: Path = RAW, output: Path = OUT) -> Path:
    paths = {name: raw / filename for name, filename in {
        "apy": "apy.csv", "centroids": "district_centroids.csv",
        "calendar": "crop_calendar.csv", "weather": "weather_daily.csv",
        "soil": "soil_district.csv"}.items()}
    metadata_path = raw / "source_metadata.json"
    absent = [str(p) for p in paths.values() if not p.exists()]
    if not metadata_path.exists():
        absent.append(str(metadata_path))
    if absent:
        raise FileNotFoundError("Required normalized source files missing: " + ", ".join(absent))

    centroids = pd.read_csv(paths["centroids"])
    apy = pd.read_csv(paths["apy"])
    calendar = pd.read_csv(paths["calendar"])
    weather = pd.read_csv(paths["weather"], parse_dates=["date"])
    soil = pd.read_csv(paths["soil"])
    source_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    for section in ["apy", "district_centroids", "crop_calendar"]:
        item = source_metadata.get(section, {})
        required_meta = {"source_url", "retrieved_utc", "license_or_terms", "raw_filename", "raw_sha256"}
        if required_meta - set(item):
            raise ValueError(f"source_metadata.json {section} is missing: {sorted(required_meta - set(item))}")
        raw_file = raw / item["raw_filename"]
        if not raw_file.exists() or sha256(raw_file) != item["raw_sha256"]:
            raise ValueError(f"Raw source file/hash mismatch for {section}: {raw_file}")
    expected = {
        "apy": {"state", "district", "year", "season", "crop", "area_ha", "production_tonnes"},
        "centroids": {"state", "district", "district_id", "latitude", "longitude", "boundary_vintage"},
        "calendar": {"district_id", "crop", "season", "start_month", "start_day", "end_month", "end_day", "calendar_source"},
        "weather": {"district_id", "date", "t2m_c", "t2m_max_c", "precip_mm", "rh2m_pct"},
        "soil": {"district_id", *SOIL_FEATURES},
    }
    for name, required in expected.items():
        missing = required - set(locals()[name].columns)
        if missing:
            raise ValueError(f"{name} missing required columns: {sorted(missing)}")

    key = ["state", "district"]
    if centroids.duplicated(key).any() or centroids["district_id"].duplicated().any():
        raise ValueError("District map must have unique state/name and district_id")
    if soil["district_id"].duplicated().any():
        raise ValueError("soil_district.csv must have one documented soil estimate per district")
    if calendar.duplicated(["district_id", "crop", "season"]).any():
        raise ValueError("District crop calendar keys must be unique")
    if apy.duplicated(["state", "district", "year", "season", "crop"]).any():
        raise ValueError("Duplicate APY keys: resolve source revisions before joining")

    # Keep only the declared research geography; unmatched districts within
    # these states still fail below so spelling/boundary issues stay visible.
    target_states = set(centroids["state"].astype(str))
    apy = apy[apy["state"].astype(str).isin(target_states)].copy()
    if apy.empty:
        raise ValueError("No APY rows match the states in district_centroids.csv")
    apy["year"] = pd.to_numeric(apy["year"], errors="raise").astype(int)
    apy["area_ha"] = pd.to_numeric(apy["area_ha"], errors="coerce")
    apy["production_tonnes"] = pd.to_numeric(apy["production_tonnes"], errors="coerce")
    apy = apy[(apy["area_ha"] > 0) & (apy["production_tonnes"] > 0)].copy()
    if "reported_yield_q_ha" in apy:
        apy["reported_yield_q_ha"] = pd.to_numeric(apy["reported_yield_q_ha"], errors="coerce")
        if apy["reported_yield_q_ha"].notna().any() and apy["reported_yield_q_ha"].isna().any():
            raise ValueError("Reported yield is partially missing; do not silently mix reported and derived targets")
    else:
        apy["reported_yield_q_ha"] = np.nan
    if apy["reported_yield_q_ha"].notna().all():
        apy["yield_q_ha"] = apy["reported_yield_q_ha"]
        yield_derivation = "source-reported yield normalized to quintals/ha"
    else:
        apy["yield_q_ha"] = 10 * apy["production_tonnes"] / apy["area_ha"]
        yield_derivation = "derived production-to-area ratio: 10 * production_tonnes / area_ha"

    apy = apy.merge(centroids, on=key, how="left", validate="many_to_one", indicator="_geo")
    if (apy["_geo"] != "both").any():
        names = apy.loc[apy["_geo"] != "both", key].drop_duplicates().to_dict("records")
        raise ValueError(f"District names not harmonized to centroid table: {names[:20]}")
    apy = apy.drop(columns="_geo")
    apy = apy.merge(calendar, on=["district_id", "crop", "season"], how="left",
                     validate="many_to_one", indicator="_cal")
    if (apy["_cal"] != "both").any():
        bad = apy.loc[apy["_cal"] != "both", ["state", "crop", "season"]].drop_duplicates()
        raise ValueError("Missing sourced crop calendar rows: " + str(bad.to_dict("records")[:20]))

    summaries = []
    for row in apy[["district_id", "year", "state", "crop", "season",
                    "start_month", "start_day", "end_month", "end_day"]].drop_duplicates().itertuples(index=False):
        start, end = season_dates(row.year, row.start_month, row.start_day,
                                  row.end_month, row.end_day)
        w = weather[(weather["district_id"] == row.district_id) &
                    weather["date"].between(start, end)]
        # Require 90% daily coverage; summarize only finite source observations.
        expected_days = (end - start).days + 1
        valid = w.dropna(subset=["t2m_c", "t2m_max_c", "precip_mm", "rh2m_pct"])
        if len(valid) < 0.9 * expected_days:
            continue
        summaries.append({
            "district_id": row.district_id, "year": row.year,
            "state": row.state, "crop": row.crop, "season": row.season,
            "season_mean_temp_c": float(valid["t2m_c"].mean()),
            "season_p95_max_temp_c": float(valid["t2m_max_c"].quantile(0.95)),
            "season_precip_mm": float(valid["precip_mm"].sum()),
            "season_mean_rh_pct": float(valid["rh2m_pct"].mean()),
            "weather_coverage": float(len(valid) / expected_days),
        })
    wx = pd.DataFrame(summaries)
    if wx.empty:
        raise ValueError("No district-season has the required weather coverage")
    panel = apy.merge(wx, on=["district_id", "year", "state", "crop", "season"],
                      how="inner", validate="one_to_one")
    panel = panel.merge(soil[["district_id", *SOIL_FEATURES]], on="district_id",
                        how="inner", validate="many_to_one")
    panel = panel.replace([np.inf, -np.inf], np.nan)
    before = len(panel)
    panel = panel.dropna(subset=FEATURES + ["yield_q_ha"])
    panel = panel[(panel["yield_q_ha"] > 0) & (panel["area_ha"] > 0)]
    if panel.empty:
        raise ValueError("No valid rows remain after sourced joins")
    panel = panel.sort_values(["crop", "year", "district_id", "season"]).reset_index(drop=True)
    output.mkdir(parents=True, exist_ok=True)
    target = output / "panel.csv"
    panel.to_csv(target, index=False)
    manifest = {
        "status": "prepared_real_source_inputs_not_yet_independently_validated",
        "rows_before_feature_missingness_filter": int(before), "rows_written": int(len(panel)),
        "years": [int(panel.year.min()), int(panel.year.max())],
        "states": sorted(panel.state.unique().tolist()), "crops": sorted(panel.crop.unique().tolist()),
        "districts": int(panel.district_id.nunique()), "features": FEATURES,
        "yield_derivation": yield_derivation,
        "yield_unit": "quintals per hectare",
        "raw_sha256": {name: sha256(path) for name, path in paths.items()},
        "source_metadata_sha256": sha256(metadata_path),
        "source_metadata": source_metadata,
        "source_cache_sha256": source_cache_hashes(raw),
        "panel_sha256": sha256(target),
        "limitations": ["district aggregate, not farm-level", "NASA POWER centroid weather proxy",
                        "static modelled SoilGrids soil estimates", "full-season weather means post-season estimation"],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=RAW)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    prepare(args.raw, args.output)
