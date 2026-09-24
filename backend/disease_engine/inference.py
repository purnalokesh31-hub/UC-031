"""
inference.py
Disease detection inference engine for UC-031 CropCare module.

Runs the 38-class PlantVillage CNN entirely within this application.
NO external service calls — fully self-contained.

Backend priority (auto-detected at startup):
  1. ONNX Runtime     — pip install onnxruntime   (works on Python 3.14, recommended)
  2. TensorFlow full  — pip install tensorflow-cpu  (Python ≤3.11 only)
  3. TFLite Runtime   — pip install tflite-runtime  (Python ≤3.11 only)
  4. Not-ready state  — user-friendly setup message shown in UI

Model files (auto-detected, checked in order):
  disease_engine/plant_disease_model.onnx    ← preferred
  disease_engine/plant_disease_model.h5      ← TF/TFLite path
  disease_engine/plant_disease_model.tflite  ← TFLite path

To download/convert the model:
  python disease_engine/download_model.py
"""

from __future__ import annotations
import io, time
from pathlib import Path
from threading import Lock
from typing import Optional

import numpy as np
from PIL import Image, ImageOps

# ── Paths ──────────────────────────────────────────────────────────────── #
ENGINE_DIR      = Path(__file__).parent
MODEL_PATH_ONNX = ENGINE_DIR / "plant_disease_model.onnx"
MODEL_PATH_H5   = ENGINE_DIR / "plant_disease_model.h5"
MODEL_PATH_TF   = ENGINE_DIR / "plant_disease_model"        # SavedModel dir
MODEL_PATH_TFL  = ENGINE_DIR / "plant_disease_model.tflite"

# ── Backend detection (best available) ────────────────────────────────── #
_BACKEND = "none"

try:
    import onnxruntime as _ort
    _BACKEND = "onnxruntime"
    print(f"[DiseaseEngine] [OK] ONNX Runtime {_ort.__version__} available")
except ImportError:
    pass

if _BACKEND == "none":
    try:
        import tensorflow as _tf
        _tf.get_logger().setLevel("ERROR")
        _BACKEND = "tensorflow"
        print(f"[DiseaseEngine] [OK] TensorFlow {_tf.__version__} available")
    except ImportError:
        pass

if _BACKEND == "none":
    try:
        import tflite_runtime.interpreter as _tflite
        _BACKEND = "tflite_runtime"
        print("[DiseaseEngine] [OK] TFLite Runtime available")
    except ImportError:
        try:
            import tensorflow.lite as _tflite
            _BACKEND = "tflite_tf"
            print("[DiseaseEngine] [OK] TFLite (bundled with TF) available")
        except Exception:
            pass

if _BACKEND == "none":
    print("[DiseaseEngine] [WARN] No inference backend found.")
    print("[DiseaseEngine]    Recommended: pip install onnxruntime")

# ── Class definitions for the checked-in 38-output PlantVillage model ──── #
CLASS_NAMES = [
    # ── PlantVillage original 38 classes ────────────────────────────── #
    "Apple___Apple_scab", "Apple___Black_rot", "Apple___Cedar_apple_rust",
    "Apple___healthy", "Blueberry___healthy",
    "Cherry_(including_sour)___Powdery_mildew", "Cherry_(including_sour)___healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "Corn_(maize)___Common_rust_", "Corn_(maize)___Northern_Leaf_Blight",
    "Corn_(maize)___healthy", "Grape___Black_rot",
    "Grape___Esca_(Black_Measles)", "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)",
    "Grape___healthy", "Orange___Haunglongbing_(Citrus_greening)",
    "Peach___Bacterial_spot", "Peach___healthy",
    "Pepper,_bell___Bacterial_spot", "Pepper,_bell___healthy",
    "Potato___Early_blight", "Potato___Late_blight", "Potato___healthy",
    "Raspberry___healthy", "Soybean___healthy", "Squash___Powdery_mildew",
    "Strawberry___Leaf_scorch", "Strawberry___healthy",
    "Tomato___Bacterial_spot", "Tomato___Early_blight", "Tomato___Late_blight",
    "Tomato___Leaf_Mold", "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite", "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus", "Tomato___Tomato_mosaic_virus",
    "Tomato___healthy",
]

# Human-readable English names
ENGLISH_NAMES: dict[str, str] = {
    # ── Original PlantVillage 38 ─────────────────────────────────────── #
    "Apple___Apple_scab":                                   "Apple Scab",
    "Apple___Black_rot":                                    "Apple Black Rot",
    "Apple___Cedar_apple_rust":                             "Apple Cedar Rust",
    "Apple___healthy":                                      "Healthy Apple",
    "Blueberry___healthy":                                  "Healthy Blueberry",
    "Cherry_(including_sour)___Powdery_mildew":             "Cherry Powdery Mildew",
    "Cherry_(including_sour)___healthy":                    "Healthy Cherry",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot":   "Corn Gray Leaf Spot",
    "Corn_(maize)___Common_rust_":                          "Corn Common Rust",
    "Corn_(maize)___Northern_Leaf_Blight":                  "Corn Northern Leaf Blight",
    "Corn_(maize)___healthy":                               "Healthy Corn / Maize",
    "Grape___Black_rot":                                    "Grape Black Rot",
    "Grape___Esca_(Black_Measles)":                         "Grape Esca (Black Measles)",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)":           "Grape Leaf Blight",
    "Grape___healthy":                                      "Healthy Grape",
    "Orange___Haunglongbing_(Citrus_greening)":             "Citrus Greening (HLB)",
    "Peach___Bacterial_spot":                               "Peach Bacterial Spot",
    "Peach___healthy":                                      "Healthy Peach",
    "Pepper,_bell___Bacterial_spot":                        "Bell Pepper Bacterial Spot",
    "Pepper,_bell___healthy":                               "Healthy Bell Pepper",
    "Potato___Early_blight":                                "Potato Early Blight",
    "Potato___Late_blight":                                 "Potato Late Blight",
    "Potato___healthy":                                     "Healthy Potato",
    "Raspberry___healthy":                                  "Healthy Raspberry",
    "Soybean___healthy":                                    "Healthy Soybean",
    "Squash___Powdery_mildew":                              "Squash Powdery Mildew",
    "Strawberry___Leaf_scorch":                             "Strawberry Leaf Scorch",
    "Strawberry___healthy":                                 "Healthy Strawberry",
    "Tomato___Bacterial_spot":                              "Tomato Bacterial Spot",
    "Tomato___Early_blight":                                "Tomato Early Blight",
    "Tomato___Late_blight":                                 "Tomato Late Blight",
    "Tomato___Leaf_Mold":                                   "Tomato Leaf Mold",
    "Tomato___Septoria_leaf_spot":                          "Tomato Septoria Leaf Spot",
    "Tomato___Spider_mites Two-spotted_spider_mite":        "Tomato Spider Mites",
    "Tomato___Target_Spot":                                 "Tomato Target Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus":               "Tomato Yellow Leaf Curl Virus",
    "Tomato___Tomato_mosaic_virus":                         "Tomato Mosaic Virus",
    "Tomato___healthy":                                     "Healthy Tomato",
}

# Crop species represented in the checked-in model's 38 class outputs.
SUPPORTED_CROPS = [
    "Apple", "Blueberry", "Cherry", "Corn", "Grape", "Orange", "Peach",
    "Bell Pepper", "Potato", "Raspberry", "Soybean", "Squash", "Strawberry", "Tomato",
]
MODEL_CLASS_COUNT = 38
assert len(CLASS_NAMES) == MODEL_CLASS_COUNT, "Class labels must match the shipped model output."
MAX_IMAGE_PIXELS = 40_000_000


class InvalidImageError(ValueError):
    """Raised when an uploaded image is invalid or too costly to decode safely."""

# Confidence tier thresholds
TIER_REJECTED  = 50.0
TIER_UNCERTAIN = 70.0
TIER_MEDIUM    = 85.0
# > 85% → high


def _confidence_tier(conf: float) -> str:
    if conf < TIER_REJECTED:  return "rejected"
    if conf < TIER_UNCERTAIN: return "uncertain"
    if conf < TIER_MEDIUM:    return "medium"
    return "high"


# ── Image preprocessing ───────────────────────────────────────────────── #
def _preprocess(image_bytes: bytes) -> np.ndarray:
    """Decode a bounded image into the model's normalized 224×224 input."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as source:
            if source.width * source.height > MAX_IMAGE_PIXELS:
                raise InvalidImageError("Image dimensions are too large. Please upload a smaller image.")
            img = ImageOps.exif_transpose(source).convert("RGB")
    except InvalidImageError:
        raise
    except (OSError, Image.DecompressionBombError, Image.UnidentifiedImageError) as exc:
        raise InvalidImageError("The uploaded file is not a valid image.") from exc
    w, h = img.size
    m = min(w, h)
    img = img.crop(((w - m) // 2, (h - m) // 2,
                    (w + m) // 2, (h + m) // 2))
    img = img.resize((224, 224), Image.LANCZOS)
    arr = np.asarray(img, dtype=np.uint8).astype(np.float32)
    arr *= 1.0 / 255.0
    return np.expand_dims(arr, axis=0)


# ── Helper: find best available model file ────────────────────────────── #
def _find_model() -> Optional[Path]:
    """Return the best available local model path, or None. ONNX preferred."""
    if MODEL_PATH_ONNX.exists():
        return MODEL_PATH_ONNX
    if MODEL_PATH_TFL.exists():
        return MODEL_PATH_TFL
    if MODEL_PATH_H5.exists():
        return MODEL_PATH_H5
    if MODEL_PATH_TF.exists() and (MODEL_PATH_TF / "saved_model.pb").exists():
        return MODEL_PATH_TF
    return None


# ── Check if any model file exists at all ─────────────────────────────── #
def _any_model_exists() -> bool:
    return (
        MODEL_PATH_ONNX.exists() or MODEL_PATH_TFL.exists()
        or MODEL_PATH_H5.exists()
        or (MODEL_PATH_TF.exists() and (MODEL_PATH_TF / "saved_model.pb").exists())
    )

# ── Main Engine class ─────────────────────────────────────────────────── #
class DiseaseInferenceEngine:
    """
    Singleton inference engine — runs entirely within this application.
    Backend priority: ONNX Runtime → TensorFlow → TFLite. No external calls.
    """
    _instance: Optional["DiseaseInferenceEngine"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.model        = None
        self._backend     = "none"
        self._model_path  = None
        self._is_tflite   = False
        self._is_onnx     = False
        self._onnx_inp    = None
        self._onnx_out    = None
        self._tflite_inp  = None
        self._tflite_out  = None
        self._inference_lock = Lock()
        self._load_model()
        self._initialized = True

    # ── Model loading ─────────────────────────────────────────────────── #
    def _load_model(self):
        model_path = _find_model()

        if model_path is None:
            print("[DiseaseEngine] [WARN] No local model found.")
            print("[DiseaseEngine]    Run: python disease_engine/download_model.py")
            return

        self._model_path = model_path

        # ── ONNX Runtime (Python 3.14 compatible, fastest path) ───────── #
        if model_path.suffix == ".onnx" and _BACKEND == "onnxruntime":
            try:
                self._load_onnx(model_path)
                return
            except Exception as e:
                print(f"[DiseaseEngine] ONNX load error: {e}")

        # If ONNX runtime is available but we have H5/TFLite, still try ONNX path
        # (model files don't match — tell user to convert)
        if _BACKEND == "onnxruntime" and model_path.suffix != ".onnx":
            print(f"[DiseaseEngine] [WARN] ONNX Runtime is available but model is '{model_path.name}'.")
            print("[DiseaseEngine]    Convert it: python disease_engine/download_model.py --onnx")
            print("[DiseaseEngine]    Trying TF/TFLite as fallback...")

        # ── TFLite path ───────────────────────────────────────────────── #
        if model_path.suffix == ".tflite":
            try:
                self._load_tflite(model_path)
                return
            except Exception as e:
                print(f"[DiseaseEngine] TFLite load error: {e}")

        # ── Full TensorFlow ───────────────────────────────────────────── #
        if _BACKEND == "tensorflow":
            try:
                import tensorflow as tf
                self.model    = tf.keras.models.load_model(str(model_path), compile=False)
                self._backend = "tensorflow"
                self._is_tflite = False
                self._is_onnx   = False
                print(f"[DiseaseEngine] [OK] TF model loaded: {model_path.name}")
                return
            except Exception as e:
                print(f"[DiseaseEngine] TF load error: {e}")

        # ── TFLite from H5 (bundled TFLite interpreter) ───────────────── #
        if _BACKEND in ("tflite_runtime", "tflite_tf"):
            try:
                self._load_tflite(model_path)
                return
            except Exception as e:
                print(f"[DiseaseEngine] TFLite-from-H5 error: {e}")

        print(f"[DiseaseEngine] [ERR] Could not load model from {model_path}")

    def _load_onnx(self, model_path: Path):
        """Load model using ONNX Runtime (Python 3.14 compatible)."""
        import onnxruntime as ort
        sess_opts = ort.SessionOptions()
        sess_opts.log_severity_level = 3   # suppress verbose logs
        session = ort.InferenceSession(
            str(model_path),
            sess_options=sess_opts,
            providers=["CPUExecutionProvider"],
        )
        self.model    = session
        self._backend = "onnxruntime"
        self._is_onnx = True
        self._is_tflite = False
        self._onnx_inp  = session.get_inputs()[0].name
        self._onnx_out  = session.get_outputs()[0].name
        print(f"[DiseaseEngine] [OK] ONNX model loaded: {model_path.name}")

    def _load_tflite(self, model_path: Path):
        """Load as TFLite Interpreter (works with tflite-runtime or tf.lite)."""
        try:
            import tflite_runtime.interpreter as tflite_rt
            interp = tflite_rt.Interpreter(model_path=str(model_path))
        except ImportError:
            import tensorflow as tf
            interp = tf.lite.Interpreter(model_path=str(model_path))

        interp.allocate_tensors()
        self.model       = interp
        self._backend    = "tflite"
        self._is_tflite  = True
        self._is_onnx    = False
        self._tflite_inp = interp.get_input_details()[0]["index"]
        self._tflite_out = interp.get_output_details()[0]["index"]
        print(f"[DiseaseEngine] [OK] TFLite model loaded: {model_path.name}")


    @property
    def ready(self) -> bool:
        return self.model is not None

    @property
    def mode(self) -> str:
        if not self.ready:
            return "not_ready"
        return self._backend

    # ── Unified predict ───────────────────────────────────────────────── #
    def predict(self, image_bytes: bytes) -> dict:
        """
        Run local inference. Returns a standardised result dict.
        Raises RuntimeError if model not loaded (call .ready first).
        """
        if not self.ready:
            return {
                "success": False,
                "error":   (
                    "Local model not loaded. "
                    "Run: python disease_engine/download_model.py "
                    "then restart the server."
                ),
                "setup_required": True,
            }

        t0 = time.perf_counter()
        result = self._local_predict(image_bytes)
        result["inference_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        return result

    # ── Local inference ───────────────────────────────────────────────── #
    def _local_predict(self, image_bytes: bytes) -> dict:
        arr = _preprocess(image_bytes)

        if self._is_onnx:
            preds = self._run_onnx(arr)
        elif self._is_tflite:
            # TFLite reuses a mutable interpreter tensor buffer across requests.
            with self._inference_lock:
                preds = self._run_tflite(arr)
        else:
            preds = self.model.predict(arr, verbose=0)[0]

        if np.asarray(preds).size != MODEL_CLASS_COUNT:
            raise RuntimeError(
                f"Disease model returned {np.asarray(preds).size} classes; expected {MODEL_CLASS_COUNT}."
            )

        top3 = np.argsort(preds)[-3:][::-1]
        best_class = CLASS_NAMES[top3[0]]
        best_conf  = float(round(preds[top3[0]] * 100, 2))
        tier       = _confidence_tier(best_conf)

        top_3_list = [
            {
                "class_name":   CLASS_NAMES[i],
                "english_name": ENGLISH_NAMES.get(CLASS_NAMES[i], CLASS_NAMES[i]),
                "confidence":   float(round(preds[i] * 100, 2)),
            }
            for i in top3
        ]

        return {
            "success":         tier != "rejected",
            "used_local":      True,
            "class_name":      best_class,
            "english_name":    ENGLISH_NAMES.get(best_class, best_class),
            "crop_type":       best_class.split("___")[0].replace("_", " "),
            "is_healthy":      "healthy" in best_class.lower(),
            "confidence":      best_conf,
            "confidence_tier": tier,
            "top_3":           top_3_list,
            "low_confidence":  tier in ("rejected", "uncertain"),
            "error":           "Low confidence — please retake with a clearer leaf photo." if tier == "rejected" else None,
        }

    def _run_onnx(self, arr: np.ndarray) -> np.ndarray:
        """Run ONNX Runtime inference (Python 3.14 compatible)."""
        outputs = self.model.run(
            [self._onnx_out],
            {self._onnx_inp: arr},
        )
        return outputs[0][0]   # shape [38]

    def _run_tflite(self, arr: np.ndarray) -> np.ndarray:
        """Run TFLite interpreter on a preprocessed image array."""
        self.model.set_tensor(self._tflite_inp, arr)
        self.model.invoke()
        return self.model.get_tensor(self._tflite_out)[0]

    def reload(self):
        """Reload model from disk (call after fine-tuning or new download)."""
        with self._inference_lock:
            self._initialized = False
            self.model = None
            self._load_model()
            self._initialized = True


# ── Module-level singleton ────────────────────────────────────────────── #
engine = DiseaseInferenceEngine()
