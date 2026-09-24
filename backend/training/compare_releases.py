"""Audit candidate artifacts against the current release without fitting on test rows.

Run with a candidate release ID. --activate publishes only after integrity checks
and non-regressing training CV scores. Holdout changes are reported, never used
to select hyperparameters, crop models, or the serving family.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from threadpoolctl import threadpool_limits

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from models.validated_yield import FEATURES, CROPS


def compare(candidate_id, activate=False, baseline_id=None):
    root = BASE / 'saved_models'
    active_id = json.loads((root / 'active_release.json').read_text())['release_id']
    previous_id = baseline_id or active_id
    if not candidate_id.isalnum() or not previous_id.isalnum() or candidate_id == previous_id:
        raise ValueError('Pass distinct baseline and candidate release IDs')
    old_dir, new_dir = (root / 'releases' / name for name in [previous_id, candidate_id])
    old_report, new_report = (json.loads((folder / 'report.json').read_text()) for folder in [old_dir, new_dir])
    dataset = BASE / 'data/crop_data.csv'
    assert old_report['dataset_sha256'] == new_report['dataset_sha256'] == hashlib.sha256(dataset.read_bytes()).hexdigest()
    splits = json.loads((new_dir / 'splits.json').read_text())
    assert splits == json.loads((old_dir / 'splits.json').read_text()), 'Evaluation rows must match'
    recorded = json.loads((new_dir / 'test_predictions.json').read_text())
    data = pd.read_csv(dataset)
    rows, selected_changes, holdout_declines = [], [], []
    with threadpool_limits(limits=1):
        for crop in CROPS:
            old, new = (joblib.load(folder / f'{crop.lower()}.joblib') for folder in [old_dir, new_dir])
            train, calibration, test = (set(splits[crop][part]) for part in ['train', 'calibration', 'test'])
            assert not (train & calibration or train & test or calibration & test)
            assert len(train | calibration | test) == 500
            frame = data.loc[splits[crop]['test']]
            X, y = frame[FEATURES].to_numpy(), frame.yield_qph.to_numpy()
            assert new['selected_family'] == min(['classical', 'quantum'], key=lambda f: new['metrics'][f]['cv_rmse'])
            if old['selected_family'] != new['selected_family']:
                selected_changes.append(f'{crop}: {old["selected_family"]} → {new["selected_family"]}')
            for family in ['classical', 'quantum']:
                a, b = old['metrics'][family], new['metrics'][family]
                assert b['cv_rmse'] <= a['cv_rmse'] + 1e-6, f'{crop}/{family}: training CV regressed'
                pred = new['models'][family].predict(X)
                np.testing.assert_allclose(pred, recorded[crop][family], atol=1e-8)
                for field, value in [('test_r2', r2_score(y, pred)), ('test_mae', mean_absolute_error(y, pred)),
                                     ('test_rmse', np.sqrt(mean_squared_error(y, pred)))]:
                    np.testing.assert_allclose(b[field], value, atol=1e-8)
                if b['test_r2'] < a['test_r2'] - 1e-6:
                    holdout_declines.append(f'{crop} {family} R²: {a["test_r2"]:.4f} → {b["test_r2"]:.4f}')
                cal = data.loc[splits[crop]['calibration']]
                errors = np.sort(abs(cal.yield_qph.to_numpy() - new['models'][family].predict(cal[FEATURES].to_numpy())))
                radius = errors[min(len(errors), int(np.ceil((len(errors) + 1) * .9))) - 1]
                np.testing.assert_allclose(radius, b['interval_radius_qph'], atol=1e-8)
                speed = {}
                for label, bundle in [('before', old), ('after', new)]:
                    bundle['models'][family].predict(X[:1])
                    timings = []
                    for _ in range(10):
                        start = time.perf_counter()
                        bundle['models'][family].predict(X[:1])
                        timings.append((time.perf_counter() - start) * 1000)
                    speed[label] = float(np.median(timings))
                rows.append(dict(crop=crop, family=family, before=a, after=b,
                                 test_mape_pct=float(np.mean(abs((y - pred) / y)) * 100),
                                 within_5pct=float(np.mean(abs((y - pred) / y) <= .05) * 100),
                                 inference_median_ms=speed))
    audit = {'previous_release': previous_id, 'candidate_release': candidate_id,
             'dataset_sha256': new_report['dataset_sha256'], 'rows': rows,
             'protocol': 'Same fixed 100 test rows per crop; all tuning uses 300 training rows with 4-fold CV. 100 separate calibration rows.',
             'limitations': 'Synthetic data only. The fixed holdout has been inspected in earlier work; independent external validation is still needed. R2 is not classification accuracy.'}
    (new_dir / 'comparison.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    lines = ['# CropGuard retraining results', '', f'Previous release: `{previous_id}`  ', f'Candidate release: `{candidate_id}`', '',
             audit['protocol'], '', audit['limitations'], '',
             '## Fixed holdout results', '',
             '| Crop | Model | R² before → after | MAE before → after (q/ha) | New MAPE | Within ±5% of actual |',
             '|---|---|---:|---:|---:|---:|']
    for row in rows:
        a, b = row['before'], row['after']
        lines.append(f"| {row['crop']} | {row['family']} | {a['test_r2']:.4f} → {b['test_r2']:.4f} | "
                     f"{a['test_mae']:.3f} → {b['test_mae']:.3f} | {row['test_mape_pct']:.2f}% | {row['within_5pct']:.0f}% |")
    spline_crops = [r['crop'] for r in rows if r['family'] == 'classical' and r['after']['name'].startswith('Spline')]
    classical_changed = [r['crop'] for r in rows if r['family'] == 'classical' and r['after']['name'] != r['before']['name']]
    lines += ['', '## Interpretation', '',
              '- The larger quantum search includes smaller encoding angles, regularization, centered kernels, and one/two encoding layers. The batched exact statevector implementation is checked against Qiskit.',
              f'- Classical candidates include polynomial and spline features plus linear, kernel, and tree regressors. The new classical estimator is {", ".join(classical_changed) if classical_changed else "unchanged across all crops"}; spline candidates won for {", ".join(spline_crops) if spline_crops else "no crops"}.',
              '- Every candidate family matches or lowers the previous training cross-validation error. Holdout improvements vary; declines are listed below and remain visible in this report.',
              f'- Training CV changed the serving family for: {"; ".join(selected_changes) if selected_changes else "no crops"}. Selection never uses the displayed test scores.',
              f'- Holdout R² declined for: {"; ".join(holdout_declines) if holdout_declines else "no crop/model pair"}.',
              '- The dataset and its noise were not changed. Its generator adds independent Gaussian noise with standard deviation 2% of base yield. Further fitting cannot guarantee predicting that random component.',
              '- MAPE is mean absolute percentage error. The ±5% column uses an explicit error tolerance, not exact correctness. These measurements do not establish farm accuracy.',
              '', '## Warm inference timing', '', '| Crop | Quantum before (ms) | Quantum after (ms) |', '|---|---:|---:|']
    for row in rows:
        if row['family'] == 'quantum':
            speed = row['inference_median_ms']
            lines.append(f"| {row['crop']} | {speed['before']:.3f} | {speed['after']:.3f} |")
    lines += ['', 'Median of 10 single-row predictions on this machine; excludes network and cold loading.', '',
              '## Integrity checks', '',
              'Dataset hash unchanged; identical disjoint splits; all 12 serialized pipelines reproduce saved predictions, regression scores and independent calibration radii. Active-family selection and training-CV non-regression checked.', '']
    (new_dir / 'RETRAINING_REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    print('\n'.join(lines))
    if activate:
        temporary = root / 'active_release.tmp'
        temporary.write_text(json.dumps({'release_id': candidate_id, 'dataset_sha256': new_report['dataset_sha256']}), encoding='utf-8')
        os.replace(temporary, root / 'active_release.json')
        print(f'Activated {candidate_id}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate')
    parser.add_argument('--baseline', help='Compare to this older release instead of the current active release')
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    compare(args.candidate, args.activate, args.baseline)
