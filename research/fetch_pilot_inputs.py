"""Cache unmodified NASA POWER and SoilGrids responses for documented points."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent


def cached_request(url, cache, provider, district):
    token = hashlib.sha256(url.encode()).hexdigest()
    path = cache / provider / f"{district}_{token}.json"
    meta = path.with_suffix(".metadata.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and meta.exists():
        metadata = json.loads(meta.read_text())
        if metadata["sha256"] != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError(f"Cache hash mismatch: {path}")
        return metadata
    for attempt in range(3):
        try:
            request = Request(url, headers={"User-Agent": "CropYieldResearch/0.2"})
            with urlopen(request, timeout=60) as response:
                blob = response.read()
            payload = json.loads(blob)
            if not isinstance(payload, dict):
                raise ValueError("Expected JSON object")
            path.write_bytes(blob)
            metadata = {"url": url, "provider": provider, "district_id": district,
                        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                        "path": str(path.resolve()), "sha256": hashlib.sha256(blob).hexdigest()}
            meta.write_text(json.dumps(metadata, indent=2))
            return metadata
        except Exception:
            if attempt == 2:
                raise
            time.sleep(15 if provider == "soilgrids" else 3 * (attempt + 1))


def fetch(provider, points_path, cache):
    points = json.loads(points_path.read_text())["points"]
    def one(point):
        if provider == "nasa":
            query = {"parameters": "T2M,T2M_MAX,PRECTOTCORR,RH2M", "community": "AG",
                     "latitude": point["latitude"], "longitude": point["longitude"],
                     "start": "19810601", "end": "20130531", "format": "JSON", "time-standard": "UTC"}
            url = "https://power.larc.nasa.gov/api/temporal/daily/point?" + urlencode(query)
        else:
            query = [("lat", point["latitude"]), ("lon", point["longitude"])]
            query += [("property", p) for p in ["nitrogen", "phh2o", "soc", "clay"]]
            query += [("depth", "0-5cm")] + [("value", p) for p in ["Q0.05", "Q0.5", "Q0.95"]]
            url = "https://rest.isric.org/soilgrids/v2.0/properties/query?" + urlencode(query)
        result = cached_request(url, cache, provider, point["district_id"])
        print(f"{provider}: {point['district_id']} {point['district']} cached", flush=True)
        return result
    results, errors = [], []
    if provider == "nasa":
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {pool.submit(one, point): point for point in points}
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as exc:
                    errors.append({"district_id": futures[future]["district_id"], "error": str(exc)})
    else:
        for point in points:
            started = time.monotonic()
            try:
                results.append(one(point))
            except Exception as exc:
                errors.append({"district_id": point["district_id"], "error": str(exc)})
            # ISRIC allows five requests/minute. Keep starts at least 12.5s apart.
            time.sleep(max(0, 12.5 - (time.monotonic() - started)))
    manifest = {"provider": provider, "points_sha256": hashlib.sha256(points_path.read_bytes()).hexdigest(),
                "responses": sorted(results, key=lambda x: x["district_id"]), "errors": errors}
    (cache / f"{provider}_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({"provider": provider, "cached": len(results), "errors": errors}), flush=True)
    if errors:
        raise RuntimeError("Some downloads failed; successful responses are cached for a retry")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=["nasa", "soilgrids"], required=True)
    parser.add_argument("--points", type=Path, default=ROOT / "district_reference_points.json")
    parser.add_argument("--cache", type=Path, default=ROOT / "data/raw/pilot_covariates")
    args = parser.parse_args()
    fetch(args.provider, args.points, args.cache)
