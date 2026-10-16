"""Development-only input-removal checks with unchanged outer splits and tuning grids."""
import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

import benchmark as b

FAMILIES = ["classical_ridge", "classical_rbf_kernel_control", "quantum_simulated_entangled"]
VARIANTS = {
    "without_soil": ["soil_nitrogen", "soil_ph", "soil_soc", "soil_clay"],
    "without_year": ["year_trend"],
    "weather_only": ["soil_nitrogen", "soil_ph", "soil_soc", "soil_clay", "year_trend"],
}


def run(base, output):
    original = json.loads((base / "run_manifest.json").read_text())
    if original["evaluation_stage"] != "development" or original["reserved_outcomes_scored"]:
        raise ValueError("Requires development-only primary run")
    panel_path = Path(original["panel"])
    lock = json.loads(Path(original["lockbox"]).read_text())
    if b.sha256(panel_path) != original["panel_sha256"]:
        raise ValueError("Panel checksum changed")
    # The executed primary snapshots are the source of truth for comparison.
    if b.sha256(Path(b.__file__)) != b.sha256(base / "benchmark_source.py"):
        raise ValueError("Benchmark source changed since primary run")
    model_path = b.ROOT.parent / "backend/models/validated_yield.py"
    if b.sha256(model_path) != b.sha256(base / "quantum_model_source.py"):
        raise ValueError("Quantum source changed since primary run")
    panel = pd.read_csv(panel_path, dtype={"district_id": str})
    data = b.development_rows(panel, "Rice", lock["crops"]["Rice"])
    manifest = json.loads(panel_path.with_name("manifest.json").read_text())
    features = manifest["features"]
    baseline = pd.read_csv(base / "predictions.csv")
    base_scores = pd.read_csv(base / "split_metrics.csv")
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, output / "feature_sensitivity_source.py")
    plan = Path(__file__).parent / "protocol/RICE_FEATURE_SENSITIVITY.md"
    records, predictions, tuning = [], [], []
    X_full = data[features].to_numpy(float)
    y = data.yield_q_ha.to_numpy(float)
    groups = data.district_id.astype(str).to_numpy()
    for seed in b.SEEDS:
        fitcal, test = next(GroupShuffleSplit(n_splits=1, test_size=.2, random_state=seed).split(X_full, y, groups))
        fit_local, cal_local = next(GroupShuffleSplit(n_splits=1, test_size=.2, random_state=seed+1000).split(X_full[fitcal], y[fitcal], groups[fitcal]))
        fit, cal = fitcal[fit_local], fitcal[cal_local]
        keys = [f"Rice|{data.iloc[i].season}|{data.iloc[i].year}|{groups[i]}" for i in test]
        for variant, removed in VARIANTS.items():
            X = X_full.copy()
            X[:, [features.index(f) for f in removed]] = 0
            for family in FAMILIES:
                print(f"sensitivity seed={seed} inputs={variant} model={family}", flush=True)
                match = baseline[(baseline.seed == seed) & (baseline.family == family)].set_index("row_key")
                if set(match.index) != set(keys) or not np.allclose(match.loc[keys].actual_q_ha, y[test], rtol=0, atol=1e-12):
                    raise ValueError("Sensitivity test rows differ from primary run")
                model, grid = b.estimators(seed, features)[family]
                fitted, cv_rmse, count = b.tune(model, grid, X[fit], y[fit], groups[fit])
                pred = fitted.predict(X[test])
                radius = b.conformal_radius(y[cal], fitted.predict(X[cal]))
                metrics = b.score(y[test], pred, radius)
                prior = base_scores[(base_scores.seed == seed) & (base_scores.family == family)]
                if len(prior) != 1 or count != 25:
                    raise ValueError("Invalid primary result or tuning budget")
                records.append({"seed": seed, "variant": variant, "family": family,
                                "n_train": len(fit), "n_calibration": len(cal), "n_test": len(test),
                                "candidate_count": count, "cv_rmse": cv_rmse, **metrics,
                                "rmse_change_from_full": metrics["rmse"] - float(prior.iloc[0].rmse)})
                tuning.append({"seed": seed, "variant": variant, "family": family,
                               **fitted.research_tuning_report_})
                for k, i, p in zip(keys, test, pred):
                    predictions.append({"seed": seed, "variant": variant, "family": family,
                                        "row_key": k, "actual_q_ha": float(y[i]), "predicted_q_ha": float(p),
                                        "interval_radius_q_ha": radius})
                # Preserve completed fits even if the process is interrupted.
                pd.DataFrame(records).to_csv(output / "split_metrics.csv", index=False)
                pd.DataFrame(predictions).to_csv(output / "predictions.csv", index=False)
                (output / "tuning_results.json").write_text(json.dumps(tuning, indent=2, default=str))
    scores = pd.DataFrame(records)
    summary = scores.groupby(["family", "variant"]).agg(
        mae=("mae", "mean"), rmse=("rmse", "mean"), rmse_sd=("rmse", "std"),
        r2=("r2", "mean"), coverage=("coverage_90", "mean"), width=("width_90_q_ha", "mean"),
        rmse_change=("rmse_change_from_full", "mean"), n_splits=("seed", "count")).reset_index()
    if len(scores) != 45 or not np.isfinite(scores[b.METRICS]).all().all():
        raise ValueError("Incomplete or nonfinite sensitivity results")
    summary.to_csv(output / "summary.csv", index=False)
    lines = ["# Development feature sensitivity", "",
             "All five original district splits; 25 candidates per family and variant. Final tests remain unscored.", "",
             "Mean metrics across overlapping splits. RMSE change is relative to the same family's full inputs; positive means worse after removal. Errors and widths are q/ha. These are predictive information-removal checks, not causal effects.", "",
             "| Family | Inputs removed | MAE | RMSE ± SD | R² | Coverage | Width | RMSE change |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in summary.itertuples():
        lines.append(f"| {r.family} | {r.variant} | {r.mae:.3f} | {r.rmse:.3f} ± {r.rmse_sd:.3f} | {r.r2:.3f} | {r.coverage:.1%} | {r.width:.3f} | {r.rmse_change:+.3f} |")
    lines += ["", "Removed columns were set to constant zero to preserve the eight-slot quantum circuit. Each variant was retuned inside the training fold. Ridge and RBF controls were specified before primary aggregate scores were inspected; this is not an exhaustive ablation of every classical family.", "",
              "Modern mapped soil, point weather, limited geography and overlapping splits remain limitations. See the primary report and protocol for interpretation."]
    (output / "FEATURE_SENSITIVITY.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    (output / "run_manifest.json").write_text(json.dumps({
        "completed_utc": datetime.now(timezone.utc).isoformat(), "evaluation_stage": "development",
        "reserved_outcomes_scored": False, "primary_results": str(base.resolve()),
        "panel_sha256": b.sha256(panel_path), "source_sha256": b.sha256(Path(__file__)),
        "plan_sha256": b.sha256(plan), "seeds": b.SEEDS, "variants": VARIANTS,
        "families": FAMILIES, "completed_fits": len(scores)}, indent=2))
    print(summary.to_string(index=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.primary_results, args.output)
