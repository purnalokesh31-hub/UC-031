"""Recompute development scores from saved predictions and verify split containment."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

import benchmark as b


def verify(primary, sensitivity):
    run = json.loads((primary / "run_manifest.json").read_text())
    lock_path = Path(run["lockbox"])
    lock = json.loads(lock_path.read_text())
    panel_path = Path(run["panel"])
    assert b.sha256(panel_path) == lock["panel_sha256"] == run["panel_sha256"]
    assert b.sha256(lock_path) == run["lockbox_sha256"]
    for path in (Path(b.__file__), b.ROOT.parent / "backend/models/validated_yield.py"):
        assert b.sha256(path) == lock["evaluation_code_sha256"][path.name] == run["evaluation_code_sha256"][path.name]
    assert not lock_path.with_name(lock_path.name + ".reserved_started.json").exists()
    data = b.development_rows(pd.read_csv(panel_path, dtype={"district_id": str}), "Rice", lock["crops"]["Rice"])
    actuals = dict(zip(data.crop + "|" + data.season + "|" + data.year.astype(str) + "|" + data.district_id, data.yield_q_ha))
    counts = {}
    for directory, identity, expected in ((primary, ["seed", "family"], 60),
                                           (sensitivity, ["seed", "family", "variant"], 45)):
        manifest = json.loads((directory / "run_manifest.json").read_text())
        assert manifest["evaluation_stage"] == "development" and not manifest["reserved_outcomes_scored"]
        scores = pd.read_csv(directory / "split_metrics.csv")
        predictions = pd.read_csv(directory / "predictions.csv")
        assert len(scores) == expected
        assert not scores.duplicated(identity).any()
        assert not predictions.duplicated(identity + ["row_key"]).any()
        assert set(predictions.row_key).issubset(actuals)
        np.testing.assert_allclose(predictions.actual_q_ha, predictions.row_key.map(actuals), rtol=0, atol=1e-12)
        for _, row in scores.iterrows():
            selected = np.ones(len(predictions), dtype=bool)
            for name in identity:
                selected &= predictions[name].eq(row[name]).to_numpy()
            subset = predictions[selected]
            assert len(subset) == int(row.n_test) == 84
            actual = subset.actual_q_ha.to_numpy()
            error = actual - subset.predicted_q_ha.to_numpy()
            expected_metrics = {
                "mae": np.abs(error).mean(), "rmse": np.sqrt(np.mean(error**2)),
                "r2": 1 - np.sum(error**2) / np.sum((actual - actual.mean())**2),
                "coverage_90": np.mean(np.abs(error) <= subset.interval_radius_q_ha.to_numpy()),
                "width_90_q_ha": 2 * subset.interval_radius_q_ha.mean(),
            }
            for name, value in expected_metrics.items():
                np.testing.assert_allclose(row[name], value, rtol=1e-9, atol=1e-9)
        counts[directory.name] = {"score_rows": len(scores), "prediction_rows": len(predictions)}
    result = {"status": "passed", "checks": "Saved metrics independently recomputed; prediction keys and targets match fit role; panel/protocol/code hashes match; no reserved evaluation receipt", "counts": counts}
    (primary / "results_verification.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    root = Path(__file__).parent / "results"
    verify(root / "rice_pilot_development_20260925", root / "rice_feature_sensitivity_20260925")
