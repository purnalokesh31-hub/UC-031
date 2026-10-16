"""Fetch sourced district-centroid weather and soil proxies.

Requires research/data/raw/district_centroids.csv. NASA and ISRIC responses
are cached unchanged under data/raw/source_cache/ for provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import csv
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
NASA = "https://power.larc.nasa.gov/api/temporal/daily/point"
SOIL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
SOIL_PROPS = ["nitrogen", "phh2o", "soc", "clay"]
NASA_PARAMS = ["T2M", "T2M_MAX", "PRECTOTCORR", "RH2M"]
SOIL_SCALE = {"nitrogen": 100.0, "phh2o": 10.0, "soc": 10.0, "clay": 10.0}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "CropYieldResearch/0.1 (reproducible academic analysis)"})
    with urlopen(req, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def soil_point(row, cache: Path) -> dict:
    cache_file = cache / "soil" / f"{row.district_id}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
    else:
        query = [("lon", float(row.longitude)), ("lat", float(row.latitude))]
        query += [("property", p) for p in SOIL_PROPS]
        query += [("depth", "0-5cm"), ("value", "Q0.05"),
                  ("value", "Q0.50"), ("value", "Q0.95")]
        payload = get_json(SOIL + "?" + urlencode(query))
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(payload), encoding="utf-8")
        time.sleep(12.2)  # ISRIC REST fair-use policy: five API calls per minute.
    layers = payload.get("properties", {}).get("layers", [])
    out = {"district_id": str(row.district_id), "depth_cm": "0-5",
           "statistic": "Q0.50", "source_version": "SoilGrids v2.0",
           "retrieved_utc": pd.Timestamp.now(tz="UTC").isoformat()}
    by_name = {layer.get("name"): layer for layer in layers}
    for prop in SOIL_PROPS:
        layer = by_name.get(prop)
        if not layer or not layer.get("depths"):
            out[{"nitrogen": "soil_nitrogen", "phh2o": "soil_ph",
                 "soc": "soil_soc", "clay": "soil_clay"}[prop]] = None
            continue
        values = layer["depths"][0].get("values", {})
        for stat, suffix in [("Q0.05", "q05"), ("Q0.50", ""), ("Q0.95", "q95")]:
            raw = values.get(stat)
            normalized = None if raw is None else float(raw) / SOIL_SCALE[prop]
            key = {"nitrogen": "soil_nitrogen", "phh2o": "soil_ph",
                   "soc": "soil_soc", "clay": "soil_clay"}[prop]
            out[key if not suffix else f"{key}_{suffix}"] = normalized
    return out


def nasa_daily(row, start_year: int, end_year: int, cache: Path) -> pd.DataFrame:
    cache_file = cache / "weather" / f"{row.district_id}_{start_year}_{end_year}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
    else:
        query = urlencode({"parameters": ",".join(NASA_PARAMS), "community": "AG",
                           "longitude": float(row.longitude), "latitude": float(row.latitude),
                           "start": f"{start_year}0101", "end": f"{end_year}1231",
                           "format": "JSON", "time-standard": "UTC"})
        payload = get_json(NASA + "?" + query)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(payload), encoding="utf-8")
    if payload.get("messages"):
        messages = " ".join(map(str, payload["messages"]))
        if "error" in messages.lower():
            raise ValueError(f"NASA POWER API returned messages for {row.district_id}: {messages}")
    parameters = payload.get("properties", {}).get("parameter", {})
    if not parameters:
        raise ValueError(f"NASA POWER response has no parameter data for {row.district_id}")
    table = pd.DataFrame(parameters)
    table.index.name = "date"
    table = table.reset_index()
    table["date"] = pd.to_datetime(table["date"], format="%Y%m%d", errors="coerce")
    table = table.rename(columns={"T2M": "t2m_c", "T2M_MAX": "t2m_max_c",
                                  "PRECTOTCORR": "precip_mm", "RH2M": "rh2m_pct"})
    for col in ["t2m_c", "t2m_max_c", "precip_mm", "rh2m_pct"]:
        if col not in table:
            table[col] = None
        table[col] = pd.to_numeric(table[col], errors="coerce")
        table[col] = table[col].mask(table[col] == -999)
    table["district_id"] = str(row.district_id)
    table["source_version"] = "NASA POWER daily API; version recorded in cached response"
    table["retrieved_utc"] = pd.Timestamp.now(tz="UTC").isoformat()
    return table[["district_id", "date", "t2m_c", "t2m_max_c", "precip_mm", "rh2m_pct",
                  "source_version", "retrieved_utc"]]


def fetch(start_year: int, end_year: int, raw: Path = RAW) -> None:
    source = raw / "district_centroids.csv"
    if not source.exists():
        raise FileNotFoundError(f"Create and source-verify {source} first")
    centroids = pd.read_csv(source)
    required = {"district_id", "latitude", "longitude", "district", "state", "boundary_vintage"}
    if required - set(centroids.columns):
        raise ValueError(f"Centroid file missing: {sorted(required - set(centroids.columns))}")
    if centroids.district_id.duplicated().any():
        raise ValueError("Expected one centroid row per stable district_id")
    if not (centroids.latitude.between(-90, 90).all() and centroids.longitude.between(-180, 180).all()):
        raise ValueError("Invalid latitude/longitude")
    cache = raw / "source_cache"
    soil_rows, weather_rows = [], []
    for row in centroids.itertuples(index=False):
        print(f"Fetching sourced covariates for {row.state}/{row.district}", flush=True)
        soil_rows.append(soil_point(row, cache))
        weather_rows.append(nasa_daily(row, start_year, end_year, cache))
    soil = pd.DataFrame(soil_rows)
    weather = pd.concat(weather_rows, ignore_index=True)
    soil.to_csv(raw / "soil_district.csv", index=False)
    weather.to_csv(raw / "weather_daily.csv", index=False)
    response_files = sorted(path for path in cache.rglob("*.json") if path.is_file())
    request_manifest = {
        "retrieved_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "district_centroids_sha256": file_sha256(source),
        "NASA_POWER": {
            "endpoint": NASA, "community": "AG", "parameters": NASA_PARAMS,
            "start_date": f"{start_year}-01-01", "end_date": f"{end_year}-12-31",
            "time_standard": "UTC", "spatial_support": "one district centroid point",
        },
        "SoilGrids": {
            "endpoint": SOIL, "properties": SOIL_PROPS, "depth": "0-5cm",
            "statistics": ["Q0.05", "Q0.50", "Q0.95"], "scale_divisors": SOIL_SCALE,
            "spatial_support": "one district centroid point; static model estimate",
            "fair_use_delay_seconds": 12.2,
        },
        "raw_response_sha256": {str(path.relative_to(raw)): file_sha256(path) for path in response_files},
    }
    (cache / f"fetch_manifest_{start_year}_{end_year}.json").write_text(
        json.dumps(request_manifest, indent=2), encoding="utf-8")
    print(f"Wrote {len(soil)} soil centroid records and {len(weather)} weather day records")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, required=True)
    parser.add_argument("--raw", type=Path, default=RAW)
    args = parser.parse_args()
    if args.end_year < args.start_year:
        parser.error("end-year must be >= start-year")
    try:
        fetch(args.start_year, args.end_year, args.raw)
    except (HTTPError, URLError) as exc:
        raise SystemExit(f"Source API request failed; raw files are not fabricated: {exc}")
