"""Reproducible CV selection, independent calibration/test, atomic releases.

Run from any directory: .venv/Scripts/python -X utf8 -u backend/training/train_validated.py
Does not generate or alter the dataset. Test rows never select models or parameters.
"""
import sys
from pathlib import Path
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
import json
import os
import time
import hashlib
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import joblib
import sklearn
import qiskit
from sklearn.model_selection import KFold, GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.preprocessing import StandardScaler, PolynomialFeatures, SplineTransformer
from sklearn.compose import TransformedTargetRegressor
from sklearn.linear_model import Ridge
from sklearn.svm import SVR
from sklearn.ensemble import (ExtraTreesRegressor, GradientBoostingRegressor,
                              HistGradientBoostingRegressor, RandomForestRegressor)
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from threadpoolctl import threadpool_limits
from models.validated_yield import FEATURES, CROPS, QuantumKernelRegressor

SEED = 20260922


def search(estimator, grid, X, y):
    return GridSearchCV(estimator, grid, scoring='neg_root_mean_squared_error',
                        cv=KFold(4, shuffle=True, random_state=SEED), n_jobs=1,
                        error_score='raise', return_train_score=False).fit(X, y)


def classical_search(X, y):
    pipeline = Pipeline([('scale', StandardScaler()), ('features', 'passthrough'),
                         ('model', Ridge())])
    estimator = TransformedTargetRegressor(regressor=pipeline, transformer=StandardScaler())
    grid = [
        {'regressor__features': ['passthrough'], 'regressor__model': [Ridge()],
         'regressor__model__alpha': [0.01, 0.1, 1, 10]},
        {'regressor__features': [PolynomialFeatures(2, include_bias=False),
                                 PolynomialFeatures(3, include_bias=False)],
         'regressor__model': [Ridge()], 'regressor__model__alpha': [0.01, 0.1, 1, 10]},
        {'regressor__features': [FeatureUnion([
            ('interactions', PolynomialFeatures(2, include_bias=False)),
            ('curves', SplineTransformer(n_knots=knots, degree=degree, include_bias=False)),
         ]) for knots in [3, 5] for degree in [1, 3]],
         'regressor__model': [Ridge()], 'regressor__model__alpha': [0.01, 0.1, 1, 10]},
        {'regressor__features': ['passthrough'], 'regressor__model': [SVR()],
         'regressor__model__C': [1, 10, 100], 'regressor__model__gamma': [0.01, 0.1],
         'regressor__model__epsilon': [0.05, 0.1]},
        {'regressor__features': ['passthrough'],
         'regressor__model': [HistGradientBoostingRegressor(random_state=SEED, max_iter=150)],
         'regressor__model__max_leaf_nodes': [7, 15],
         'regressor__model__l2_regularization': [1, 10]},
        {'regressor__features': ['passthrough'],
         'regressor__model': [RandomForestRegressor(random_state=SEED, n_estimators=250,
                                                     n_jobs=1)],
         'regressor__model__max_features': [0.7, 1.0],
         'regressor__model__min_samples_leaf': [1, 3]},
        {'regressor__features': ['passthrough'],
         'regressor__model': [ExtraTreesRegressor(random_state=SEED, n_estimators=250,
                                                  n_jobs=1)],
         'regressor__model__max_features': [0.7, 1.0],
         'regressor__model__min_samples_leaf': [1, 3]},
        {'regressor__features': ['passthrough'],
         'regressor__model': [GradientBoostingRegressor(random_state=SEED)],
         'regressor__model__n_estimators': [100, 250],
         'regressor__model__learning_rate': [0.03, 0.08],
         'regressor__model__max_depth': [2, 3],
         'regressor__model__min_samples_leaf': [3, 8]},
    ]
    return search(estimator, grid, X, y)


def model_name(estimator, family):
    if family == 'quantum':
        return f'Exact quantum kernel ridge (4 qubits, {estimator.layers} encoding layers)'
    pipe = estimator.regressor_
    features = pipe['features']
    prefix = ('Quadratic ' if features.degree == 2 else 'Cubic ') if isinstance(features, PolynomialFeatures) else ''
    if isinstance(features, FeatureUnion):
        prefix = 'Spline + quadratic '
    return prefix + type(pipe['model']).__name__


def score(y, prediction):
    return {'test_r2': float(r2_score(y, prediction)),
            'test_mse': float(mean_squared_error(y, prediction)),
            'test_rmse': float(np.sqrt(mean_squared_error(y, prediction))),
            'test_mae': float(mean_absolute_error(y, prediction))}


def run(activate=True):
    started = time.perf_counter()
    source = BASE / 'data/crop_data.csv'
    dataset_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    df = pd.read_csv(source)
    if set(df.crop_type) != set(CROPS):
        raise ValueError('Dataset must contain exactly the six supported crops')
    if df.duplicated(FEATURES + ['crop_type']).any():
        raise ValueError('Duplicate feature rows must be grouped or removed before splitting')
    if not np.isfinite(df[FEATURES + ['yield_qph']].to_numpy()).all():
        raise ValueError('Missing/nonfinite training values')
    release_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    release = BASE / 'saved_models/releases' / release_id
    release.mkdir(parents=True)
    all_metrics, split_indices, predictions, leaderboard = {}, {}, {}, {}
    with threadpool_limits(limits=1):
        for crop in CROPS:
            sub = df[df.crop_type == crop]
            if len(sub) < 200:
                raise ValueError(f'{crop}: insufficient rows for train/calibration/test')
            train_cal, test = train_test_split(sub.index.to_numpy(), test_size=0.2, random_state=SEED)
            train, calibration = train_test_split(train_cal, test_size=0.25, random_state=SEED)
            split_indices[crop] = {name: idx.tolist() for name, idx in
                                   [('train', train), ('calibration', calibration), ('test', test)]}
            X = df.loc[train, FEATURES].to_numpy()
            y = df.loc[train, 'yield_qph'].to_numpy()
            X_cal = df.loc[calibration, FEATURES].to_numpy()
            y_cal = df.loc[calibration, 'yield_qph'].to_numpy()
            X_test = df.loc[test, FEATURES].to_numpy()
            y_test = df.loc[test, 'yield_qph'].to_numpy()
            print(f'{crop}: {len(train)} training / {len(calibration)} calibration / {len(test)} test', flush=True)
            bundle = {'schema': 1, 'crop': crop, 'features': FEATURES, 'models': {},
                      'bounds': {f: [float(X[:, i].min()), float(X[:, i].max())]
                                 for i, f in enumerate(FEATURES)}, 'metrics': {}}
            leaderboard[crop], predictions[crop] = {}, {'row_ids': test.tolist(), 'actual': y_test.tolist()}
            for family in ['classical', 'quantum']:
                t0 = time.perf_counter()
                fitted = (classical_search(X, y) if family == 'classical' else
                          search(QuantumKernelRegressor(),
                                 {'angle_scale': [0.01, 0.03, 0.05, 0.15, 0.4],
                                  'alpha': [0.00000001, 0.000001, 0.00001, 0.001, 0.1],
                                  'layers': [1, 2], 'center_kernel': [False, True]}, X, y))
                estimator = fitted.best_estimator_
                calibration_error = np.abs(y_cal - estimator.predict(X_cal))
                # Finite sample split-conformal quantile: rank ceil((n+1)*0.9).
                rank = min(len(calibration_error), int(np.ceil((len(calibration_error) + 1) * 0.9)))
                radius = float(np.sort(calibration_error)[rank - 1])
                pred = estimator.predict(X_test)
                metrics = score(y_test, pred)
                metrics.update({'name': model_name(estimator, family), 'cv_rmse': -float(fitted.best_score_),
                                'interval_radius_qph': radius, 'interval_level': 0.9,
                                'test_interval_coverage': float(np.mean(np.abs(y_test - pred) <= radius)),
                                'train_samples': len(train), 'calibration_samples': len(calibration),
                                'test_samples': len(test), 'train_time_s': time.perf_counter() - t0})
                if family == 'quantum':
                    metrics.update(n_qubits=4, reps=estimator.layers,
                                   feature_map='RY/RZ all 8 features with CNOT chain per layer',
                                   kernel_centered=estimator.center_kernel, simulator='exact statevector')
                bundle['models'][family], bundle['metrics'][family] = estimator, metrics
                predictions[crop][family] = pred.tolist()
                leaderboard[crop][family] = [
                    {'params': {k: str(v) for k, v in params.items()}, 'cv_rmse': float(-mean),
                     'cv_std_rmse': float(std)} for params, mean, std in zip(
                         fitted.cv_results_['params'], fitted.cv_results_['mean_test_score'],
                         fitted.cv_results_['std_test_score'])]
                print(f'  {family}: CV RMSE={metrics["cv_rmse"]:.3f}; test R2={metrics["test_r2"]:.4f}; '
                      f'MAE={metrics["test_mae"]:.3f} q/ha; {metrics["train_time_s"]:.1f}s', flush=True)
            # Selection uses training-fold validation scores, never test scores.
            selected = min(bundle['metrics'], key=lambda f: bundle['metrics'][f]['cv_rmse'])
            bundle['selected_family'] = selected
            bundle['metrics']['selected_family'] = selected
            bundle['metrics']['bounds'] = bundle['bounds']
            bundle['metrics']['scope'] = 'Synthetic demo data; no field validation'
            bundle['metrics']['crop_type'] = crop
            baseline = np.full_like(y_test, y.mean())
            bundle['metrics']['mean_baseline'] = score(y_test, baseline)
            all_metrics[crop] = bundle['metrics']
            filename = release / f'{crop.lower()}.joblib'
            joblib.dump(bundle, filename)
            restored = joblib.load(filename)
            for family in ['classical', 'quantum']:
                np.testing.assert_allclose(restored['models'][family].predict(X_test[:3]),
                                           bundle['models'][family].predict(X_test[:3]), atol=1e-9)
    report = {'release_id': release_id, 'dataset_sha256': dataset_hash, 'seed': SEED,
              'dataset_scope': 'Existing synthetic dataset, unchanged; internal holdout is not external validation',
              'protocol': '60% fit (4-fold CV), 20% interval calibration, 20% identical final test for both models',
              'versions': {'python': sys.version, 'sklearn': sklearn.__version__, 'qiskit': qiskit.__version__},
              'elapsed_s': time.perf_counter() - started, 'crops': all_metrics}
    for name, value in [('metrics.json', all_metrics), ('report.json', report),
                        ('splits.json', split_indices), ('test_predictions.json', predictions),
                        ('cv_candidates.json', leaderboard)]:
        (release / name).write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')
    # One pointer publishes the complete set; a failed run never activates partial models.
    if activate:
        pointer = BASE / 'saved_models/active_release.json'
        temp = pointer.with_suffix('.tmp')
        temp.write_text(json.dumps({'release_id': release_id, 'dataset_sha256': dataset_hash}), encoding='utf-8')
        os.replace(temp, pointer)
    print(f'{"Activated" if activate else "Saved candidate"} complete release: {release_id}; '
          f'elapsed={report["elapsed_s"]:.1f}s', flush=True)
    return release


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-activate', action='store_true', help='Save a complete candidate without changing live models')
    args = parser.parse_args()
    run(activate=not args.no_activate)
