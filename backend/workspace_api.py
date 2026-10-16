"""Read-only research evidence, archived weather context and exact model trace."""
import csv
import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import URLError
from threading import Lock

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
import yield_service
from models.validated_yield import FEATURES

router = APIRouter()
ROOT = Path(__file__).resolve().parent
WEATHER_LOCK = Lock()


class WeatherRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    start: date
    end: date

    @model_validator(mode="after")
    def valid_period(self):
        if self.start < date(1981, 1, 1) or self.end >= date.today() or not 0 <= (self.end-self.start).days <= 365:
            raise ValueError("Choose 1–366 historical days, from 1981 onwards, ending before today.")
        return self


@router.post("/workspace/weather")
def weather(req: WeatherRequest):
    query = {"latitude": req.latitude, "longitude": req.longitude,
             "start": req.start.strftime("%Y%m%d"), "end": req.end.strftime("%Y%m%d"),
             "parameters": "T2M,PRECTOTCORR,RH2M", "community": "AG", "format": "JSON", "time-standard": "UTC"}
    url = "https://power.larc.nasa.gov/api/temporal/daily/point?" + urlencode(query)
    cache = ROOT / "data/weather_cache"
    key = hashlib.sha256(url.encode()).hexdigest()
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{key}.json"
    with WEATHER_LOCK:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
        try:
            with urlopen(url, timeout=25) as response:
                raw = response.read(5_000_001)
            if len(raw) > 5_000_000:
                raise ValueError("Oversized response")
            payload = json.loads(raw)
            columns = payload["properties"]["parameter"]
            units = {"T2M": "C", "PRECTOTCORR": "mm/day", "RH2M": "%"}
            if payload["header"]["time_standard"] != "UTC" or any(payload["parameters"][k]["units"] != v for k, v in units.items()):
                raise ValueError("Unexpected units or time standard")
            days = [(req.start + timedelta(days=i)).strftime("%Y%m%d") for i in range((req.end-req.start).days+1)]
            values = {k: [float(columns[k][day]) for day in days] for k in units}
            fill = payload["header"]["fill_value"]
            if any(not math.isfinite(v) or v == fill for series in values.values() for v in series):
                raise ValueError("Incomplete period")
            if any(v < 0 for v in values["PRECTOTCORR"]) or any(not 0 <= v <= 100 for v in values["RH2M"]):
                raise ValueError("Invalid weather values")
            result = {"source": "NASA POWER daily point data", "source_url": url,
                      "documentation_url": "https://power.larc.nasa.gov/docs/services/api/temporal/daily/",
                      "retrieved_at": datetime.now(timezone.utc).isoformat(), "raw_sha256": hashlib.sha256(raw).hexdigest(),
                      "latitude": req.latitude, "longitude": req.longitude, "start": req.start.isoformat(), "end": req.end.isoformat(),
                      "days": len(days), "mean_temperature_c": sum(values["T2M"])/len(days),
                      "rainfall_total_mm": sum(values["PRECTOTCORR"]), "mean_humidity_pct": sum(values["RH2M"])/len(days),
                      "complete": True, "time_standard": "UTC",
                      "scope": "Gridded weather context, not a field measurement or forecast. No validated mapping to the synthetic yield model."}
        except (URLError, TimeoutError, ValueError, KeyError, TypeError, OSError) as exc:
            raise HTTPException(502, "Weather data are unavailable or incomplete for this period. Try an older period or retry later.") from exc
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(result), encoding="utf-8")
        temporary.replace(path)
        return result


@router.get("/research/evidence")
def evidence():
    root = ROOT.parent / "research/results"
    runs = [("primary", "rice_pilot_development_20260925", "Full inputs"),
            ("sensitivity", "rice_feature_sensitivity_20260925", "Feature removal"),
            ("weather", "rice_weather_contrasts_20260927", "Weather contrasts")]
    output = []
    for key, directory, title in runs:
        folder = root / directory
        try:
            manifest = json.loads((folder / "run_manifest.json").read_text())
            if manifest["evaluation_stage"] != "development" or manifest["reserved_outcomes_scored"]:
                raise ValueError("Not a development report")
            with (folder / "split_metrics.csv").open(newline="", encoding="utf-8") as handle:
                scores = list(csv.DictReader(handle))
            with (folder / "predictions.csv").open(newline="", encoding="utf-8") as handle:
                predictions = list(csv.DictReader(handle))
            models = []
            for family, variant in sorted({(r["family"], r.get("variant", "full")) for r in scores}):
                rows = [r for r in scores if r["family"] == family and r.get("variant", "full") == variant]
                metrics = {name: float(np.mean([float(r[name]) for r in rows])) for name in ["mae", "rmse", "r2", "coverage_90", "width_90_q_ha"]}
                metrics["rmse_sd"] = float(np.std([float(r["rmse"]) for r in rows], ddof=1)) if len(rows) > 1 else 0
                p = [r for r in predictions if r["family"] == family and r.get("variant", "full") == variant]
                breakdown = {}
                for dimension, slot in [("district", 3), ("year", 2)]:
                    groups = {}
                    for r in p:
                        groups.setdefault(r["row_key"].split("|")[slot], []).append(r)
                    breakdown[dimension] = [{"label": name, "prediction_count": len(group),
                        "rmse": float(np.sqrt(np.mean([(float(r["actual_q_ha"])-float(r["predicted_q_ha"]))**2 for r in group]))),
                        "mae": float(np.mean([abs(float(r["actual_q_ha"])-float(r["predicted_q_ha"])) for r in group]))} for name, group in sorted(groups.items())]
                models.append({"family": family, "variant": variant, "splits": len(rows), **metrics, "breakdown": breakdown})
            output.append({"id": key, "title": title, "directory": directory, "models": models,
                           "completed_at": manifest.get("completed_utc"), "status": "available"})
        except (OSError, ValueError, KeyError) as exc:
            output.append({"id": key, "title": title, "status": "unavailable"})
    return {"runs": output, "scope": "Historical annual rice, 364 development rows in 13 districts; five overlapping geographic splits.",
            "sources": ["ICRISAT–TCI historical district yield archive", "NASA POWER point weather", "SoilGrids static mapped soil (full-input run)"],
            "reserved_outcomes_scored": False, "deployed": False,
            "limitations": "Retrospective district estimation, not a farm forecast. Point weather and static soil are proxies. Repeated splits overlap. No independent external validation or demonstrated quantum advantage."}


def quantum_trace(crop, values):
    release = yield_service.release_id()
    bundle = yield_service.load(crop, release)
    model = bundle["models"]["quantum"]
    X = np.asarray([[values[f] for f in FEATURES]], dtype=float)
    standardized = model.scaler_.transform(X)[0]
    angles = standardized * model.angle_scale
    states = model._states(X)
    similarities = np.abs(states @ model.states_.conj().T)**2
    kernel = model.centerer_.transform(similarities) if getattr(model, "centerer_", None) is not None else similarities
    prediction = float(model.target_.inverse_transform(model.regressor_.predict(kernel)[:, None])[0, 0])
    nearest = np.argsort(similarities[0])[-5:][::-1]
    return {"release_id": release, "crop": crop, "layers": model.layers, "qubits": 4,
            "angle_scale": model.angle_scale, "alpha": model.alpha, "centered": model.center_kernel,
            "features": [{"name": f, "raw": float(X[0, i]), "standardized": float(standardized[i]),
                          "rotation_radians": float(np.pi/2+angles[i] if i < 4 else angles[i]),
                          "gate": "RY" if i < 4 else "RZ", "qubit": i % 4} for i, f in enumerate(FEATURES)],
            "probabilities": [{"basis": format(i, "04b"), "probability": float(abs(v)**2)} for i, v in enumerate(states[0])],
            "neighbors": [{"reference": int(i)+1, "fidelity": float(similarities[0, i])} for i in nearest],
            "reference_count": len(model.states_), "yield_qph": prediction,
            "scope": "Exact classical simulation of the deployed synthetic-data quantum kernel; probabilities are not yield confidence."}
