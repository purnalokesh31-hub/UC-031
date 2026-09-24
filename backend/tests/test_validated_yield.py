"""Regression checks against the actual published crop artifacts and HTTP API."""
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from fastapi.testclient import TestClient
from models.validated_yield import FEATURES, CROPS
import yield_service
# Isolate disease startup persistence from the user's real scan database.
import database.disease_db as db
_temp = tempfile.TemporaryDirectory()
db.DB_PATH = Path(_temp.name) / 'scans.db'
db.IMAGES_DIR = Path(_temp.name) / 'images'
import main


class YieldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(main.app)
        cls.metrics = yield_service.metrics()

    def sample(self, crop='Rice'):
        return {'crop_type': crop, **{f: sum(limits) / 2 for f, limits in
                                    self.metrics[crop]['bounds'].items()}}

    def test_all_crops_inference_and_recommendations(self):
        for crop in CROPS:
            with self.subTest(crop=crop):
                payload = self.sample(crop)
                response = self.client.post('/predict/both', json=payload)
                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()
                self.assertFalse(result['out_of_distribution'])
                winner = min(['classical', 'quantum'], key=lambda f: self.metrics[crop][f]['cv_rmse'])
                self.assertEqual(result['selected_family'], winner)
                self.assertEqual(result['recommended'], result[winner])
                self.assertEqual(result['recommendations']['predicted_yield_qph'], result[winner]['yield_qph'])
                self.assertEqual(result['recommendations']['pest_interventions'], [])
                self.assertEqual(result['recommendations']['npk_deficiencies'], [])
                for family in ['classical', 'quantum']:
                    point = result[family]
                    self.assertLessEqual(point['confidence_low'], point['yield_qph'])
                    self.assertGreaterEqual(point['confidence_high'], point['yield_qph'])
                    standalone = self.client.post('/predict/' + family, json=payload).json()
                    self.assertEqual(standalone['yield_qph'], point['yield_qph'])
                recs = self.client.post('/recommendations', json=payload)
                self.assertEqual(recs.status_code, 200, recs.text)
                self.assertEqual(recs.json()['predicted_yield_qph'], result['recommended']['yield_qph'])

    def test_out_of_range_no_false_interval_or_alert(self):
        response = self.client.post('/predict/both', json={**self.sample(), 'N': 0}).json()
        self.assertTrue(response['out_of_distribution'])
        self.assertIn('N', response['out_of_range_features'])
        self.assertIsNone(response['recommended']['confidence_low'])
        self.assertEqual(response['recommendations']['severity'], 'unassessed')

    def test_validation_and_no_client_injected_yield(self):
        for update in [{'crop_type': '../../x'}, {'rainfall': 900}, {'N': 'NaN'},
                       {'N': 'Infinity'}, {'predicted_yield_qph': 500}]:
            response = self.client.post('/recommendations', json={**self.sample(), **update})
            self.assertEqual(response.status_code, 422, response.text)
        response = self.client.post('/predict/both', json={**self.sample(), 'crop_type': ' rice '})
        self.assertEqual(response.json()['crop_type'], 'Rice')

    def test_missing_models_error_not_fabrication(self):
        with patch.object(yield_service, 'ROOT', Path(_temp.name)):
            response = self.client.post('/recommendations', json=self.sample())
            self.assertEqual(response.status_code, 503)

    def test_quantum_deterministic_all_features_and_psd(self):
        model = yield_service.load('Rice')['models']['quantum']
        x = np.array([[self.sample()[f] for f in FEATURES]])
        np.testing.assert_allclose(model.predict(x), model.predict(x), atol=1e-12)
        states = model._states(np.repeat(x, 9, axis=0) + np.vstack([np.zeros(8), np.eye(8)]))
        kernel = abs(states @ states.conj().T) ** 2
        np.testing.assert_allclose(np.diag(kernel), 1, atol=1e-12)
        np.testing.assert_allclose(kernel, kernel.T, atol=1e-12)
        self.assertGreater(np.linalg.eigvalsh(kernel).min(), -1e-9)
        for i in range(1, 9):
            self.assertLess(kernel[0, i], 1 - 1e-10)

    def test_split_isolation_and_test_scores_reproducible(self):
        import pandas as pd
        data = pd.read_csv(BASE / 'data/crop_data.csv')
        release = yield_service.ROOT / 'releases' / yield_service.release_id()
        splits = json.loads((release / 'splits.json').read_text())
        heldout = json.loads((release / 'test_predictions.json').read_text())
        for crop in CROPS:
            parts = splits[crop]
            sets = [set(parts[k]) for k in ['train', 'calibration', 'test']]
            self.assertEqual(len(set.union(*sets)), 500)
            for i in range(3):
                for j in range(i):
                    self.assertFalse(sets[i] & sets[j])
            bundle = yield_service.load(crop)
            X = data.loc[parts['test'], FEATURES].to_numpy()
            for family in ['classical', 'quantum']:
                np.testing.assert_allclose(bundle['models'][family].predict(X), heldout[crop][family], atol=1e-8)
                self.assertTrue(np.isfinite(self.metrics[crop][family]['test_r2']))

    def test_calibration_radius_is_independent_and_reproducible(self):
        import pandas as pd
        data = pd.read_csv(BASE / 'data/crop_data.csv')
        release = yield_service.ROOT / 'releases' / yield_service.release_id()
        splits = json.loads((release / 'splits.json').read_text())
        for crop in CROPS:
            rows = data.loc[splits[crop]['calibration']]
            bundle = yield_service.load(crop)
            for family in ['classical', 'quantum']:
                errors = np.sort(abs(rows.yield_qph.to_numpy() - bundle['models'][family].predict(rows[FEATURES].to_numpy())))
                rank = min(len(errors), int(np.ceil((len(errors) + 1) * .9)))
                self.assertAlmostEqual(errors[rank - 1], self.metrics[crop][family]['interval_radius_qph'], places=8)

    def test_duplicate_scan_contract_and_upload_limits(self):
        row = {'id': 12, 'predicted_class': 'Tomato___healthy', 'used_local_model': 1,
               'is_healthy': 1, 'top_3_json': '[]'}
        with patch.object(main, '_DISEASE_MODULE', True), patch.object(main._disease_db, 'check_duplicate', return_value=row):
            response = self.client.post('/disease/scan', files={'file': ('test.jpg', b'cached', 'image/jpeg')})
        self.assertTrue(response.json()['success'])
        self.assertEqual(response.json()['scan_id'], 12)
        for blob, expected in [(b'', 400), (b'x' * (10 * 1024 * 1024 + 1), 413)]:
            response = self.client.post('/disease/scan', files={'file': ('test.jpg', blob, 'image/jpeg')})
            self.assertEqual(response.status_code, expected)
        self.assertEqual(self.client.get('/disease/history?limit=-1').status_code, 422)

    def test_db_duplicate_ids(self):
        payload = dict(image_path='test', image_hash='same', predicted_class='healthy', telugu_name='',
                       english_name='', confidence=99, top_3=[], crop_type='Tomato', is_healthy=True,
                       confidence_tier='high', used_local=True)
        first = main._disease_db.save_scan(**payload)
        self.assertGreater(first, 0)
        self.assertEqual(first, main._disease_db.save_scan(**payload))


if __name__ == '__main__':
    unittest.main()
