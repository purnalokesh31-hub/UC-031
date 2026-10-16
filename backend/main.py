"""
main.py — FastAPI Backend for CropGuard AI (UC-031)

Endpoints:
  POST /predict/both          — Run both models, return comparison
  POST /predict/quantum       — QSVR prediction only
  POST /predict/classical     — Classical SVR prediction only
  GET  /metrics               — Trained model metrics
  POST /recommendations       — CropGuard interventions if yield is critical
  GET  /health                — Health check

  ── CropCare AI — Disease Detection Module (100% local) ─────────────
  POST /disease/scan          — Upload leaf image → local AI disease detection
  POST /disease/feedback      — Record user correction (active learning)
  GET  /disease/history       — Last N scan results
  GET  /disease/analytics     — Confidence stats & disease frequency
  GET  /disease/retrain-status — Active learning queue status
  GET  /disease/engine-status  — Local model status & setup instructions

Run: uvicorn main:app --reload --port 8000
"""

from __future__ import annotations
import os, json, time, sys

# ── Force UTF-8 on Windows (fixes 'charmap' codec errors with Unicode chars) ─ #
os.environ.setdefault("PYTHONUTF8", "1")
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from pathlib import Path
from typing import Optional, List
from threading import RLock

import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ── Path resolution ───────────────────────────────────────────────────── #
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# ── App ───────────────────────────────────────────────────────────────── #
app = FastAPI(
    title="CropGuard AI — Quantum Yield Predictor",
    description=(
        "Hybrid Quantum-Classical crop yield prediction API. "
        "Uses a 4-qubit ZZFeatureMap Quantum SVR vs Classical RBF SVR. "
        "Built for UC-031: AP Agriculture Dept / RBKs / Agri-fintech."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "CROPGUARD_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Disease Detection Module ──────────────────────────────────────────── #
try:
    from database.disease_db   import DiseaseDB
    from disease_engine.inference import engine as disease_engine, InvalidImageError
    from disease_engine.active_learning import active_learner

    _disease_db = DiseaseDB()
    _disease_db.init()
    _DISEASE_MODULE = True
    print("[CropGuard] [OK] Disease Detection module loaded")
except Exception as _e:
    _DISEASE_MODULE = False
    _err_str = str(_e).encode("ascii", errors="replace").decode("ascii")
    print(f"[CropGuard] [WARN] Disease module unavailable: {_err_str}")

# Solutions lookup for disease enrichment
_disease_solutions: dict = {}
try:
    _sol_path = BASE_DIR / "data" / "solutions.json"
    if _sol_path.exists():
        import json as _json
        with open(_sol_path, encoding="utf-8") as _f:
            _disease_solutions = _json.load(_f)
except Exception:
    pass


def _enrich_with_solutions(class_name: str) -> dict:
    """Return disease-specific advice only when a matching record exists.

    The checked-in solutions file currently contains yield interventions, not
    PlantVillage disease records. Generic fallback text must not be presented
    as a crop-specific diagnosis or treatment recommendation.
    """
    # Normalise Corn class names to match solutions.json keys
    _CLASS_MAPPING = {
        "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
        "Corn_(maize)___Common_rust_": "Corn_(maize)___Common_rust_",
        "Corn_(maize)___Northern_Leaf_Blight": "Corn_(maize)___Northern_Leaf_Blight",
        "Corn_(maize)___healthy": "Corn_(maize)___healthy",
        "Cherry___Powdery_mildew": "Cherry_(including_sour)___Powdery_mildew",
        "Cherry___healthy": "Cherry_(including_sour)___healthy",
    }
    mapped = _CLASS_MAPPING.get(class_name, class_name)
    info   = _disease_solutions.get(mapped, {})
    return {
        "telugu_name": info.get("telugu_name", ""),
        "solution":    info.get("solution", ""),
        "fungicide":   info.get("pesticide", ""),
        "insecticide": info.get("insecticide", ""),
    }


# Yield pipelines are stored together in immutable releases.
import yield_service
from models.validated_yield import FEATURES, CROPS
from pydantic import ConfigDict, field_validator
from fastapi import Query
from starlette.concurrency import run_in_threadpool


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    N: float = Field(..., ge=0, le=300)
    P: float = Field(..., ge=0, le=150)
    K: float = Field(..., ge=0, le=200)
    pH: float = Field(..., ge=3, le=10)
    moisture: float = Field(..., ge=0, le=100)
    temperature: float = Field(..., ge=5, le=50)
    humidity: float = Field(..., ge=0, le=100)
    rainfall: float = Field(..., ge=0, le=500)
    crop_type: str

    @field_validator("crop_type")
    @classmethod
    def validate_crop(cls, value):
        names = {name.casefold(): name for name in CROPS}
        if value.strip().casefold() not in names:
            raise ValueError("Unsupported crop; choose " + ", ".join(CROPS))
        return names[value.strip().casefold()]


from workspace_api import router as workspace_router, quantum_trace
app.include_router(workspace_router)

@app.post("/quantum/walkthrough")
def walkthrough(req: PredictRequest):
    return quantum_trace(req.crop_type, req.model_dump())


def get_metrics():
    return yield_service.metrics()


def get_solutions():
    return _disease_solutions


@app.get("/health")
def health():
    return {"status": "ok", "service": "CropGuard AI — UC-031"}


@app.get("/metrics")
def metrics():
    return get_metrics()


@app.post("/predict/classical")
def predict_classical(req: PredictRequest):
    result = yield_service.predict(req.crop_type, req.model_dump(), ("classical",))
    return {**result["classical"], "warnings": result["warnings"],
            "release_id": result["release_id"],
            "out_of_distribution": result["out_of_distribution"]}


@app.post("/predict/quantum")
def predict_quantum(req: PredictRequest):
    result = yield_service.predict(req.crop_type, req.model_dump(), ("quantum",))
    return {**result["quantum"], "warnings": result["warnings"],
            "release_id": result["release_id"],
            "out_of_distribution": result["out_of_distribution"]}


def _recommendations(req, prediction):
    crop = req.crop_type
    crop_data = get_solutions()["interventions"][crop]
    baseline = crop_data["baseline_yield_qph"]
    selected = prediction["recommended"]
    pred = selected["yield_qph"]
    ratio = pred / baseline
    thresholds = get_solutions()["yield_thresholds"]
    severity = ("unassessed" if prediction["out_of_distribution"] else
                "critical" if ratio < thresholds["critical"] else
                "warning" if ratio < thresholds["warning"] else "normal")
    # A yield regressor does not establish nutrient deficiency or pest presence.
    # The former global N<60 rule incorrectly diagnosed normal Groundnut inputs.
    return {"crop": crop, "predicted_yield_qph": pred,
            "prediction_model": selected["model"], "baseline_yield_qph": baseline,
            "yield_ratio": round(ratio, 3), "severity": severity,
            "npk_deficiencies": [], "weather_alerts": [], "pest_interventions": [],
            "assessment_note": "Yield estimates do not diagnose nutrient deficiencies or pests. Treatment decisions need a separate field assessment.",
            "warnings": prediction["warnings"], "source": "CropGuard demo knowledge base"}


@app.post("/predict/both")
def predict_both(req: PredictRequest):
    result = yield_service.predict(req.crop_type, req.model_dump())
    result["recommendations"] = _recommendations(req, result)
    return result


@app.post("/predict/selected")
def predict_selected(req: PredictRequest):
    """Return the CV-selected estimate promptly; research comparisons are opt-in."""
    result = yield_service.predict(req.crop_type, req.model_dump(), ("selected",))
    result["recommendations"] = _recommendations(req, result)
    return result


@app.post("/recommendations")
def recommendations(req: PredictRequest):
    # Never trust client-supplied yields, or fabricate a value on model failure.
    result = yield_service.predict(req.crop_type, req.model_dump(), ("selected",))
    return _recommendations(req, result)


# ═══════════════════════════════════════════════════════════════════════════ #
#  DISEASE DETECTION ROUTES  (CropCare AI Module)                            #
# ═══════════════════════════════════════════════════════════════════════════ #

def _disease_module_check():
    if not _DISEASE_MODULE:
        raise HTTPException(503, "Disease Detection module not available. Check server logs.")


# ── POST /disease/scan ─────────────────────────────────────────────────── #
@app.post("/disease/scan")
async def disease_scan(file: UploadFile = File(...)):
    """
    Upload a leaf image → AI disease detection.
    1. Read image bytes
    2. Check SHA256 duplicate cache
    3. Run local TF model (or HF proxy fallback)
    4. Enrich with Telugu name + remedy from solutions.json
    5. Store in SQLite
    6. Return full result with top-3 alternatives
    """
    _disease_module_check()

    # Validate file type
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(400, "Please upload an image file (JPG, PNG, WEBP).")

    image_bytes = await file.read(10 * 1024 * 1024 + 1)
    if len(image_bytes) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(413, "Image too large. Please upload an image under 10 MB.")
    if not image_bytes:
        raise HTTPException(400, "The uploaded image is empty.")

    # ── Duplicate check ─────────────────────────────────────────────────── #
    import hashlib
    img_hash = hashlib.sha256(image_bytes).hexdigest()
    cached = _disease_db.check_duplicate(img_hash)
    if cached:
        import json as _json
        cached["from_cache"]  = True
        cached["top_3"]       = _json.loads(cached.get("top_3_json") or "[]")
        cached["success"] = True
        cached["scan_id"] = cached["id"]
        cached["class_name"] = cached.get("predicted_class", "")
        cached["used_local"] = bool(cached.get("used_local_model"))
        cached["is_healthy"] = bool(cached.get("is_healthy"))
        cached["supported_crops"] = disease_engine.supported_crops
        return JSONResponse(content=cached)

    # ── Run inference ───────────────────────────────────────────────────── #
    try:
        result = await run_in_threadpool(disease_engine.predict, image_bytes)
    except InvalidImageError as exc:
        raise HTTPException(400, str(exc)) from exc

    if not result.get("success"):
        # Low confidence or model error
        return JSONResponse(content={
            "success":          False,
            "error":            result.get("error", "Analysis failed."),
            "low_confidence":   result.get("low_confidence", False),
            "confidence":       result.get("confidence", 0),
            "confidence_tier":  result.get("confidence_tier", "rejected"),
        }, status_code=200)

    # ── Enrich with solutions.json ──────────────────────────────────────── #
    class_name = result.get("class_name") or ""
    if class_name:
        sol = _enrich_with_solutions(class_name)
        result["telugu_name"]  = sol["telugu_name"]
        result["solution"]     = sol["solution"]
        result["fungicide"]    = sol["fungicide"]
        result["insecticide"]  = sol["insecticide"]
    else:
        # Proxy path already has telugu_name from HF Space
        result.setdefault("telugu_name",  "")
        result.setdefault("solution",     "")
        result.setdefault("fungicide",    "")
        result.setdefault("insecticide",  "")

    # ── Save image + scan to DB ─────────────────────────────────────────── #
    image_path, _ = _disease_db.save_image(image_bytes)
    scan_id = _disease_db.save_scan(
        image_path      = image_path,
        image_hash      = img_hash,
        predicted_class = class_name or result.get("telugu_name", "unknown"),
        telugu_name     = result.get("telugu_name", ""),
        english_name    = result.get("english_name", ""),
        confidence      = result.get("confidence", 0),
        top_3           = result.get("top_3", []),
        crop_type       = result.get("crop_type") or (class_name.split("___")[0] if class_name else "Unknown"),
        is_healthy      = result.get("is_healthy", False),
        confidence_tier = result.get("confidence_tier", "medium"),
        used_local      = result.get("used_local", False),
        solution        = result.get("solution", ""),
        fungicide       = result.get("fungicide", ""),
        insecticide     = result.get("insecticide", ""),
    )

    result["scan_id"]       = scan_id
    result["from_cache"]    = False
    result["supported_crops"] = disease_engine.supported_crops if _DISEASE_MODULE else []
    return JSONResponse(content=result)


# ── POST /disease/feedback ─────────────────────────────────────────────── #
class FeedbackRequest(BaseModel):
    scan_id:         int
    feedback:        str   = "correct"   # "correct" | "wrong"
    corrected_class: Optional[str] = None

@app.post("/disease/feedback")
def disease_feedback(req: FeedbackRequest):
    """
    Record user feedback on a scan result.
    If 'wrong', adds image to active learning queue.
    Triggers fine-tune if threshold (50) is reached.
    """
    _disease_module_check()
    if req.feedback not in ("correct", "wrong"):
        raise HTTPException(400, "feedback must be 'correct' or 'wrong'")

    _disease_db.save_feedback(req.scan_id, req.feedback, req.corrected_class)

    # Check if fine-tuning should be triggered
    msg = active_learner.maybe_trigger_finetune(_disease_db)

    return {
        "success":  True,
        "message":  msg,
        "feedback": req.feedback,
    }


# ── GET /disease/history ───────────────────────────────────────────────── #
@app.get("/disease/history")
def disease_history(limit: int = Query(10, ge=1, le=50)):
    """Return the last N disease scan results."""
    _disease_module_check()
    rows = _disease_db.get_history(min(limit, 50))
    import json as _j
    for r in rows:
        try:
            r["top_3"] = _j.loads(r.get("top_3_json") or "[]")
        except Exception:
            r["top_3"] = []
    return {"scans": rows, "count": len(rows)}


# ── GET /disease/analytics ─────────────────────────────────────────────── #
@app.get("/disease/analytics")
def disease_analytics():
    """Aggregate stats: total scans, avg confidence, most common disease, trend."""
    _disease_module_check()
    return _disease_db.get_analytics()


# ── GET /disease/retrain-status ────────────────────────────────────────── #
@app.get("/disease/retrain-status")
def retrain_status():
    """Active learning queue status — how many corrections, is fine-tune ready."""
    _disease_module_check()
    return active_learner.get_status(_disease_db)


# -- GET /disease/engine-status ------------------------------------------------ #
@app.get("/disease/engine-status")
def engine_status():
    """Returns local model readiness status and setup instructions."""
    if not _DISEASE_MODULE:
        return {"module_available": False}

    from disease_engine.inference import (
        MODEL_PATH_H5, MODEL_PATH_TFL, MODEL_PATH_TF, MODEL_PATH_ONNX,
    )
    model_h5_exists   = MODEL_PATH_H5.exists()
    model_tfl_exists  = MODEL_PATH_TFL.exists()
    model_onnx_exists = MODEL_PATH_ONNX.exists()
    model_exists      = model_onnx_exists or model_tfl_exists or model_h5_exists

    if not model_exists:
        setup_command = "python disease_engine/download_model.py"
    elif model_h5_exists and not model_onnx_exists and not model_tfl_exists:
        setup_command = "See disease_engine/colab_convert_to_onnx.py to convert H5 -> ONNX"
    else:
        setup_command = None

    return {
        "module_available":    _DISEASE_MODULE,
        "inference_mode":      disease_engine.mode,
        "model_ready":         disease_engine.ready,
        "class_count":         disease_engine.class_count,
        "model_h5_exists":     model_h5_exists,
        "model_onnx_exists":   model_onnx_exists,
        "model_tflite_exists": model_tfl_exists,
        "supported_crops":     disease_engine.supported_crops,
        "setup_command":       setup_command,
    }
