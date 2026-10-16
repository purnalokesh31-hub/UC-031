import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from disease_engine import inference


class DiseaseInferenceCompatibilityTests(unittest.TestCase):
    def test_supported_38_and_60_class_label_orders(self):
        self.assertEqual(len(inference.class_names_for_count(38)), 38)
        self.assertEqual(len(inference.class_names_for_count(60)), 60)
        self.assertEqual(inference.class_names_for_count(60)[:38], inference.CLASS_NAMES)
        self.assertEqual(len(inference.supported_crops_for_count(38)), 14)
        self.assertEqual(len(inference.supported_crops_for_count(60)), 19)
        with self.assertRaises(ValueError):
            inference.class_names_for_count(39)

    def test_logits_become_normalized_probabilities(self):
        probabilities = inference._as_probabilities(np.array([-2.0, 0.0, 2.0]))
        self.assertTrue(np.isfinite(probabilities).all())
        self.assertTrue(np.all(probabilities >= 0))
        self.assertAlmostEqual(float(probabilities.sum()), 1.0, places=6)
        self.assertEqual(int(probabilities.argmax()), 2)

    def test_existing_probability_output_is_preserved(self):
        scores = np.array([0.1, 0.7, 0.2], dtype=np.float32)
        np.testing.assert_allclose(inference._as_probabilities(scores), scores)

    def test_60_class_scores_receive_the_matching_crop_labels(self):
        scores = np.zeros(60, dtype=np.float32)
        scores[-1] = 5.0
        with patch.object(inference, "_preprocess", return_value=np.zeros((1, 224, 224, 3), dtype=np.float32)), \
             patch.object(inference.engine, "_run_onnx", return_value=scores), \
             patch.object(inference.engine, "_is_onnx", True):
            result = inference.engine._local_predict(b"test")
        self.assertEqual(result["class_name"], "Groundnut___healthy")
        self.assertEqual(result["english_name"], "Healthy Groundnut")
        self.assertEqual(result["crop_type"], "Groundnut")
        self.assertAlmostEqual(result["confidence"], 71.55, places=1)

    def test_shipped_onnx_output_width_matches_active_engine(self):
        if not inference.engine.ready or not inference.engine._is_onnx:
            self.skipTest("Shipped ONNX model is unavailable in this environment")
        scores = inference.engine._run_onnx(np.zeros((1, 224, 224, 3), dtype=np.float32))
        self.assertEqual(np.asarray(scores).size, inference.engine.class_count)
        self.assertEqual(inference.engine.class_count, 38)
        np.testing.assert_allclose(inference._as_probabilities(scores).sum(), 1.0, atol=1e-5)


if __name__ == "__main__":
    unittest.main()
