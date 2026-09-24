"""
active_learning.py
Manages the feedback loop and fine-tuning pipeline.

When 50+ user-corrected images accumulate in the queue,
a background thread fine-tunes the local TF model using
transfer learning (freeze base → train top classifier only).
"""

from __future__ import annotations
import os, json, shutil, threading
from pathlib import Path
from typing import Optional

ENGINE_DIR  = Path(__file__).parent
MODEL_PATH  = ENGINE_DIR / "plant_disease_model.h5"
MODEL_BKP   = ENGINE_DIR / "plant_disease_model.bkp.h5"
FINETUNE_DIR = ENGINE_DIR.parent / "data" / "finetune_images"
FINE_TUNE_THRESHOLD = 50   # Trigger fine-tune after this many corrections

_fine_tune_lock = threading.Lock()
_is_fine_tuning = False


class ActiveLearningEngine:
    """
    Monitors the correction queue and triggers fine-tuning
    when sufficient labelled corrections accumulate.
    """

    def get_status(self, db) -> dict:
        """Return active learning readiness status."""
        queue = db.get_active_learning_queue()
        pending = len([q for q in queue if q["status"] == "pending"])
        return {
            "pending_corrections": pending,
            "fine_tune_threshold": FINE_TUNE_THRESHOLD,
            "fine_tune_ready":     pending >= FINE_TUNE_THRESHOLD,
            "is_fine_tuning":      _is_fine_tuning,
            "model_exists_local":  MODEL_PATH.exists(),
            "finetune_dir":        str(FINETUNE_DIR),
        }

    def maybe_trigger_finetune(self, db) -> Optional[str]:
        """
        Called after every correction saved.
        If threshold reached and TF available, launches fine-tune in background.
        Returns status message.
        """
        global _is_fine_tuning
        queue = db.get_active_learning_queue()
        pending = len(queue)

        if pending < FINE_TUNE_THRESHOLD:
            return f"Queued {pending}/{FINE_TUNE_THRESHOLD} corrections for fine-tuning"

        if _is_fine_tuning:
            return "Fine-tuning already in progress..."

        try:
            import tensorflow as tf
            TF_OK = MODEL_PATH.exists()
        except ImportError:
            TF_OK = False

        if not TF_OK:
            return f"⚠ {pending} corrections ready but TF/model not available for fine-tuning"

        # Launch background fine-tune
        thread = threading.Thread(
            target=self._run_finetune,
            args=(db, queue),
            daemon=True,
            name="FineTuneThread"
        )
        thread.start()
        return f"🚀 Fine-tuning started with {pending} corrections!"

    def _run_finetune(self, db, queue: list):
        """
        Background fine-tuning using transfer learning.
        Only trains the classification head — base CNN layers frozen.
        """
        global _is_fine_tuning
        with _fine_tune_lock:
            _is_fine_tuning = True
            print("[ActiveLearning] 🔧 Starting fine-tuning...")

            try:
                import tensorflow as tf
                from tensorflow.keras.preprocessing.image import ImageDataGenerator

                # ── 1. Prepare fine-tune dataset ─────────────────────── #
                FINETUNE_DIR.mkdir(parents=True, exist_ok=True)

                valid_items = []
                for item in queue:
                    img_path = Path(item["image_path"])
                    cls      = item["corrected_class"]
                    if img_path.exists() and cls:
                        cls_dir = FINETUNE_DIR / cls.replace("/", "_")
                        cls_dir.mkdir(parents=True, exist_ok=True)
                        dest = cls_dir / img_path.name
                        if not dest.exists():
                            shutil.copy2(img_path, dest)
                        valid_items.append(item)

                if len(valid_items) < 10:
                    print(f"[ActiveLearning] ⚠ Only {len(valid_items)} valid items — skipping")
                    return

                print(f"[ActiveLearning] Training on {len(valid_items)} corrected images")

                # ── 2. Load model + freeze base ──────────────────────── #
                model = tf.keras.models.load_model(str(MODEL_PATH), compile=False)

                # Freeze all layers except the last 3 (classifier head)
                for layer in model.layers[:-3]:
                    layer.trainable = False

                model.compile(
                    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
                    loss="categorical_crossentropy",
                    metrics=["accuracy"]
                )

                # ── 3. Data generator ────────────────────────────────── #
                datagen = ImageDataGenerator(
                    rescale=1.0 / 255,
                    rotation_range=20,
                    width_shift_range=0.1,
                    height_shift_range=0.1,
                    horizontal_flip=True,
                    validation_split=0.2,
                )

                train_gen = datagen.flow_from_directory(
                    str(FINETUNE_DIR),
                    target_size=(224, 224),
                    batch_size=16,
                    class_mode="categorical",
                    subset="training",
                )

                # ── 4. Fine-tune ─────────────────────────────────────── #
                model.fit(train_gen, epochs=5, verbose=1)

                # ── 5. Save (backup old model first) ─────────────────── #
                if MODEL_PATH.exists():
                    shutil.copy2(MODEL_PATH, MODEL_BKP)
                model.save(str(MODEL_PATH))

                # ── 6. Reload engine singleton ────────────────────────── #
                from disease_engine.inference import DiseaseInferenceEngine
                eng = DiseaseInferenceEngine()
                eng.model     = model
                eng.use_local = True

                # Mark queue processed
                db.mark_queue_processed([item["id"] for item in valid_items])

                print(f"[ActiveLearning] ✅ Fine-tuning complete! Model updated.")

            except Exception as e:
                print(f"[ActiveLearning] ❌ Fine-tuning failed: {e}")
            finally:
                _is_fine_tuning = False


# Module-level singleton
active_learner = ActiveLearningEngine()
