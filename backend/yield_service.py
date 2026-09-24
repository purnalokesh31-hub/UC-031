"""Serve immutable, validated releases using their own complete pipelines."""
import json
import time
from functools import lru_cache
from pathlib import Path
from threading import RLock
import joblib
import numpy as np
from fastapi import HTTPException
from models.validated_yield import FEATURES, CROPS

ROOT = Path(__file__).resolve().parent / 'saved_models'
_lock = RLock()


def release_id():
    try:
        name = json.loads((ROOT / 'active_release.json').read_text(encoding='utf-8'))['release_id']
        if not isinstance(name, str) or not name.isalnum():
            raise ValueError('Invalid release identifier')
        return name
    except (OSError, ValueError, KeyError) as exc:
        raise HTTPException(503, 'No validated model release is available. Run training/train_validated.py.') from exc


@lru_cache(maxsize=12)
def _load(release, crop):
    bundle = joblib.load(ROOT / 'releases' / release / f'{crop.lower()}.joblib')
    if bundle['features'] != FEATURES or bundle['crop'] != crop:
        raise ValueError('Model schema mismatch')
    return bundle


def load(crop, release=None):
    if crop not in CROPS:
        raise HTTPException(422, 'Unsupported crop')
    with _lock:
        try:
            return _load(release or release_id(), crop)
        except (OSError, ValueError, KeyError) as exc:
            raise HTTPException(503, 'The active crop model cannot be loaded.') from exc


def metrics():
    current = release_id()
    try:
        rows = json.loads((ROOT / 'releases' / current / 'metrics.json').read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise HTTPException(503, 'Release metrics unavailable') from exc
    return {**rows, 'release_id': current, 'dataset_scope': 'synthetic',
            'evaluation': 'Identical holdout rows; selection by 4-fold training CV'}


def predict(crop, values, families=('classical', 'quantum')):
    current = release_id()
    bundle = load(crop, current)
    if families == ('selected',):
        families = (bundle['selected_family'],)
    X = np.asarray([[values[f] for f in FEATURES]], dtype=float)
    if not np.isfinite(X).all():
        raise HTTPException(422, 'All input values must be finite')
    outside = [f for i, f in enumerate(FEATURES)
               if not bundle['bounds'][f][0] <= X[0, i] <= bundle['bounds'][f][1]]
    warnings = ['Trained and evaluated on synthetic data; field accuracy has not been established.']
    if outside:
        warnings.append('Outside the training range: ' + ', '.join(outside) +
                        '. This is an extrapolation; calibrated intervals and yield alerts are unavailable.')
    result = {'crop_type': crop, 'release_id': current, 'warnings': warnings,
              'out_of_distribution': bool(outside), 'out_of_range_features': outside,
              'selected_family': bundle['selected_family'], 'metrics': bundle['metrics']}
    for family in families:
        start = time.perf_counter()
        pred = float(bundle['models'][family].predict(X)[0])
        duration = (time.perf_counter() - start) * 1000
        if not np.isfinite(pred):
            raise HTTPException(503, 'The model returned a nonfinite prediction')
        measured = bundle['metrics'][family]
        radius = measured['interval_radius_qph']
        result[family] = {'model': measured['name'], 'yield_qph': round(pred, 2),
                          'confidence_low': None if outside else round(pred - radius, 2),
                          'confidence_high': None if outside else round(pred + radius, 2),
                          'interval_level': 0.9, 'interval_method': 'split conformal',
                          'inference_time_ms': round(duration, 3)}
    if bundle['selected_family'] in result:
        result['recommended'] = result[bundle['selected_family']]
    if len(families) == 2:
        c = bundle['metrics']['classical']['test_r2']
        q = bundle['metrics']['quantum']['test_r2']
        result['quantum_advantage'] = q > c
        result['improvement_pct'] = round((q - c) * 100, 2)  # R² percentage points, not relative accuracy
    return result
