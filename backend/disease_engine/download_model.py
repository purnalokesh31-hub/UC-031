"""
download_model.py
Downloads and optionally converts the PlantVillage disease model for local inference.

Run from the backend directory:
  python disease_engine/download_model.py           # Download H5
  python disease_engine/download_model.py --onnx    # Download + convert to ONNX (for Python 3.14)

The CropCare AI disease engine runs 100% locally — no external service calls after setup.

Inference backend auto-detection order:
  1. ONNX Runtime  (Python 3.14+) — pip install onnxruntime
  2. TensorFlow    (Python ≤3.11)  — pip install tensorflow-cpu==2.15.0
  3. TFLite        (Python ≤3.11)  — pip install tflite-runtime
"""

import sys, argparse
import urllib.request
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────── #
ENGINE_DIR     = Path(__file__).parent
MODEL_PATH_H5  = ENGINE_DIR / "plant_disease_model.h5"
MODEL_PATH_ONNX= ENGINE_DIR / "plant_disease_model.onnx"
MODEL_PATH_TFL = ENGINE_DIR / "plant_disease_model.tflite"

# Primary model source (binary weights from HF Hub, read-only, no HF account needed)
MODEL_URL = "https://huggingface.co/spaces/EcoTensors/CropCare-AI/resolve/main/plant_disease_model.h5"


# ── Progress bar ──────────────────────────────────────────────────────── #
def _progress(block_num, block_size, total_size):
    downloaded = block_num * block_size
    if total_size > 0:
        pct      = min(downloaded / total_size * 100, 100)
        mb       = downloaded / (1024 * 1024)
        total_mb = total_size / (1024 * 1024)
        bar      = "█" * int(pct // 5) + "░" * (20 - int(pct // 5))
        print(f"\r  [{bar}] {pct:.1f}%  {mb:.1f}/{total_mb:.1f} MB", end="", flush=True)


# ── Download H5 ───────────────────────────────────────────────────────── #
def download_h5() -> bool:
    if MODEL_PATH_H5.exists():
        size_mb = MODEL_PATH_H5.stat().st_size / (1024 * 1024)
        print(f"✅ Model H5 already present  ({size_mb:.1f} MB)")
        return True

    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"⬇  Downloading PlantVillage model weights...")
    print(f"   Destination: {MODEL_PATH_H5}\n")

    try:
        urllib.request.urlretrieve(MODEL_URL, str(MODEL_PATH_H5), reporthook=_progress)
        size_mb = MODEL_PATH_H5.stat().st_size / (1024 * 1024)
        print(f"\n✅ Downloaded → {MODEL_PATH_H5}  ({size_mb:.1f} MB)")
        return True
    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        if MODEL_PATH_H5.exists():
            MODEL_PATH_H5.unlink()
        return False


# ── Convert H5 → ONNX (recommended for Python 3.14) ──────────────────── #
def convert_to_onnx() -> bool:
    """
    Convert the Keras H5 model to ONNX format.
    Requires: tf2onnx + tensorflow (or tensorflow-cpu) on Python ≤3.11
    OR:       Use a Colab notebook and copy the .onnx file over.
    """
    if MODEL_PATH_ONNX.exists():
        size_mb = MODEL_PATH_ONNX.stat().st_size / (1024 * 1024)
        print(f"✅ ONNX model already present  ({size_mb:.1f} MB)")
        return True

    print("\n🔄 Converting H5 → ONNX format (Python 3.14 compatible)...")

    # Method 1: tf2onnx (requires TF + tf2onnx on Python ≤3.11)
    try:
        import tensorflow as tf
        import tf2onnx
        import onnx

        print("   Loading Keras model...")
        model = tf.keras.models.load_model(str(MODEL_PATH_H5), compile=False)

        # Save as TF SavedModel first, then convert
        saved_dir = ENGINE_DIR / "_tmp_savedmodel"
        model.save(str(saved_dir), save_format="tf")

        input_sig = [tf.TensorSpec(model.input_shape, tf.float32, name="input")]
        onnx_model, _ = tf2onnx.convert.from_keras(
            model,
            input_signature=input_sig,
            opset=13,
            output_path=str(MODEL_PATH_ONNX),
        )

        import shutil
        shutil.rmtree(saved_dir, ignore_errors=True)

        size_mb = MODEL_PATH_ONNX.stat().st_size / (1024 * 1024)
        print(f"✅ ONNX model saved → {MODEL_PATH_ONNX}  ({size_mb:.1f} MB)")
        return True

    except ImportError as e:
        missing = str(e).split("'")[1] if "'" in str(e) else str(e)
        print(f"⚠  Missing package '{missing}' for conversion.")
        print()
        print("  Option A — Install on Python ≤3.11 and convert:")
        print("    pip install tensorflow-cpu==2.15.0 tf2onnx")
        print("    python disease_engine/download_model.py --onnx")
        print()
        print("  Option B — Convert in Google Colab (free) and download .onnx:")
        print("    See: https://colab.research.google.com/")
        print("    Then place 'plant_disease_model.onnx' in backend/disease_engine/")
        return False

    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        if MODEL_PATH_ONNX.exists():
            MODEL_PATH_ONNX.unlink()
        return False


# ── Convert H5 → TFLite (for Python ≤3.11 with TF) ──────────────────── #
def convert_to_tflite(model=None) -> bool:
    if MODEL_PATH_TFL.exists():
        size_mb = MODEL_PATH_TFL.stat().st_size / (1024 * 1024)
        print(f"✅ TFLite model already present  ({size_mb:.1f} MB)")
        return True

    print("\n🔄 Converting to TFLite format...")
    try:
        import tensorflow as tf
        if model is None:
            model = tf.keras.models.load_model(str(MODEL_PATH_H5), compile=False)

        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        tflite_model = converter.convert()

        with open(MODEL_PATH_TFL, "wb") as f:
            f.write(tflite_model)

        size_mb = MODEL_PATH_TFL.stat().st_size / (1024 * 1024)
        print(f"✅ TFLite saved → {MODEL_PATH_TFL}  ({size_mb:.1f} MB)")
        return True
    except ImportError:
        print("⚠  TensorFlow not installed — cannot convert to TFLite.")
        return False
    except Exception as e:
        print(f"❌ TFLite conversion failed: {e}")
        return False


# ── Verify ONNX with onnxruntime ──────────────────────────────────────── #
def verify_onnx() -> bool:
    try:
        import onnxruntime as ort
        session = ort.InferenceSession(str(MODEL_PATH_ONNX),
                                       providers=["CPUExecutionProvider"])
        inp = session.get_inputs()[0]
        out = session.get_outputs()[0]
        print(f"✅ ONNX model verified")
        print(f"   Input  : {inp.name}  {inp.shape}  {inp.type}")
        print(f"   Output : {out.name}  {out.shape}  {out.type}")
        return True
    except ImportError:
        print("⚠  onnxruntime not installed — install with: pip install onnxruntime")
        return False
    except Exception as e:
        print(f"❌ ONNX verify failed: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────── #
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download/convert the PlantVillage model for local CropCare AI."
    )
    parser.add_argument("--onnx", action="store_true",
                        help="Convert H5 → ONNX after download (Python 3.14 compatible)")
    parser.add_argument("--tflite", action="store_true",
                        help="Convert H5 → TFLite after download (Python ≤3.11, TF required)")
    parser.add_argument("--onnx-only", action="store_true",
                        help="Only do ONNX conversion (H5 already downloaded)")
    args = parser.parse_args()

    print("=" * 62)
    print("  CropCare AI — Local Model Setup")
    print("  Disease detection runs 100% within this application.")
    print("=" * 62 + "\n")

    if not args.onnx_only:
        ok = download_h5()
        if not ok:
            sys.exit(1)

    if args.onnx or args.onnx_only:
        ok = convert_to_onnx()
        if ok:
            verify_onnx()

    if args.tflite:
        convert_to_tflite()

    print("\n" + "=" * 62)
    print("  Setup complete!")
    print()
    if MODEL_PATH_ONNX.exists():
        print("  ✅ ONNX model ready  → works on Python 3.14 with onnxruntime")
    if MODEL_PATH_TFL.exists():
        print("  ✅ TFLite model ready → works on Python ≤3.11 with tflite-runtime")
    if MODEL_PATH_H5.exists() and not MODEL_PATH_ONNX.exists():
        print("  ✅ H5 model ready     → requires TensorFlow (Python ≤3.11)")
        print()
        print("  ⚠  You are using Python 3.14 — TF/TFLite don't support it yet.")
        print("     Convert to ONNX for full compatibility:")
        print("     python disease_engine/download_model.py --onnx")
        print("     (Run this command on Python ≤3.11 or in Google Colab)")
    print()
    print("  Start the server:")
    print("    uvicorn main:app --reload --port 8000")
    print("=" * 62)
