"""Development-only calendar-half weather investigation; never scores final reserves."""
import argparse
import json
import platform
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.model_selection import GroupShuffleSplit

import benchmark as b
from prepare_rice_pilot import annual_weather, load_responses

ROOT = Path(__file__).resolve().parent
FAMILIES = ["classical_ridge", "classical_rbf_kernel_control", "quantum_simulated_entangled"]
FEATURES = ["half_temp_contrast_c", "half_rain_contrast_mm", "half_rh_contrast_pct", "constant_zero",
            "annual_mean_temp_c", "annual_precip_mm", "annual_mean_rh_pct", "year_trend"]


def weather_features(payload, row):
    year = int(row.year)
    annual = annual_weather(payload, year)  # Validates dates, source units, fill values and ranges.
    for name in FEATURES[4:7]:
        if not np.isclose(annual[name], getattr(row, name), rtol=1e-10, atol=1e-8):
            raise ValueError(f"Annual weather no longer reproduces frozen input: {name}")
    daily = pd.DataFrame(payload["properties"]["parameter"])[["T2M", "PRECTOTCORR", "RH2M"]]
    daily.index = pd.to_datetime(daily.index, format="%Y%m%d")
    early = daily.reindex(pd.date_range(f"{year}-06-01", f"{year}-11-30"))
    late = daily.reindex(pd.date_range(f"{year}-12-01", f"{year+1}-05-31"))
    if len(early) + len(late) != annual["weather_days"]:
        raise ValueError("Calendar halves do not partition the agricultural year")
    return [float(early.T2M.mean() - late.T2M.mean()),
            float(early.PRECTOTCORR.sum() - late.PRECTOTCORR.sum()),
            float(early.RH2M.mean() - late.RH2M.mean()), 0.,
            *[annual[name] for name in FEATURES[4:7]], float(year)]


def run(output):
    primary = ROOT / "results/rice_pilot_development_20260925"
    sensitivity = ROOT / "results/rice_feature_sensitivity_20260925"
    original = json.loads((primary / "run_manifest.json").read_text())
    previous = json.loads((sensitivity / "run_manifest.json").read_text())
    for manifest in [original, previous]:
        if manifest["evaluation_stage"] != "development" or manifest["reserved_outcomes_scored"]:
            raise ValueError("Requires development-only prior results")
    panel_path = Path(original["panel"])
    lock_path = Path(original["lockbox"])
    lock = json.loads(lock_path.read_text())
    if not (b.sha256(panel_path) == original["panel_sha256"] == previous["panel_sha256"] == lock["panel_sha256"]):
        raise ValueError("Frozen panel checksum mismatch")
    model_path = ROOT.parent / "backend/models/validated_yield.py"
    for path, snapshot in [(Path(b.__file__), primary / "benchmark_source.py"),
                           (model_path, primary / "quantum_model_source.py")]:
        if b.sha256(path) != b.sha256(snapshot) or b.sha256(path) != lock["evaluation_code_sha256"][path.name]:
            raise ValueError("Frozen evaluation code changed")
    panel = pd.read_csv(panel_path, dtype={"district_id": str, "source_district_id": str})
    data = b.development_rows(panel, "Rice", lock["crops"]["Rice"])
    del panel
    if len(data) != 364 or data.district_id.nunique() != 13:
        raise ValueError("Unexpected development cohort")
    point_path = ROOT / "district_reference_points.json"
    nasa, nasa_manifest = load_responses(ROOT / "data/raw/pilot_covariates", "nasa", b.sha256(point_path))
    panel_manifest = json.loads(panel_path.with_name("manifest.json").read_text())
    for response in nasa_manifest["responses"]:
        if panel_manifest["source_cache_sha256"].get(response["path"]) != response["sha256"]:
            raise ValueError("Weather cache differs from original panel source")
    X = np.asarray([weather_features(nasa[row.source_district_id], row) for row in data.itertuples()])
    if X.shape != (364, 8) or not np.isfinite(X).all():
        raise ValueError("Invalid contrast features")
    y = data.yield_q_ha.to_numpy(float)
    groups = data.district_id.astype(str).to_numpy()
    keys = [f"Rice|{row.season}|{row.year}|{row.district_id}" for row in data.itertuples()]
    baseline_pred = pd.read_csv(sensitivity / "predictions.csv")
    baseline_scores = pd.read_csv(sensitivity / "split_metrics.csv")
    primary_pred = pd.read_csv(primary / "predictions.csv")
    primary_scores = pd.read_csv(primary / "split_metrics.csv")
    output.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__), Path(b.__file__), model_path, ROOT / "prepare_rice_pilot.py",
               ROOT / "protocol/RICE_WEATHER_CONTRASTS.md", lock_path,
               sensitivity / "split_metrics.csv", sensitivity / "predictions.csv",
               primary / "split_metrics.csv", primary / "predictions.csv"]
    hashes = {str(path.resolve()): b.sha256(path) for path in sources}
    for path in sources[:5]:
        shutil.copyfile(path, output / path.name)
    receipt = {"started_utc": datetime.now(timezone.utc).isoformat(), "evaluation_stage": "development",
               "reserved_outcomes_scored": False, "panel_sha256": b.sha256(panel_path),
               "source_sha256": hashes, "features": FEATURES, "seeds": b.SEEDS,
               "families": FAMILIES, "rows": len(data), "districts": int(data.district_id.nunique()),
               "environment": {"python": platform.python_version(), "numpy": np.__version__,
                               "pandas": pd.__version__, "sklearn": sklearn.__version__}}
    (output / "started.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    (output / "weather_source_manifest.json").write_text(json.dumps(nasa_manifest, indent=2), encoding="utf-8")
    pd.DataFrame(X, columns=FEATURES).assign(row_key=keys).to_csv(output / "development_features.csv", index=False)
    records, predictions, tuning, splits = [], [], [], []
    for seed in b.SEEDS:
        fitcal, test = next(GroupShuffleSplit(n_splits=1, test_size=.2, random_state=seed).split(X, y, groups))
        fit_local, cal_local = next(GroupShuffleSplit(n_splits=1, test_size=.2, random_state=seed+1000).split(X[fitcal], y[fitcal], groups[fitcal]))
        fit, cal = fitcal[fit_local], fitcal[cal_local]
        role_sets = [set(groups[indices]) for indices in [fit, cal, test]]
        if any(role_sets[i] & role_sets[j] for i in range(3) for j in range(i)):
            raise ValueError("Outer district roles overlap")
        splits.append({"seed": seed, **{role: [keys[i] for i in indices]
                      for role, indices in [("train", fit), ("calibration", cal), ("test", test)]}})
        test_keys = [keys[i] for i in test]
        trend = primary_scores[(primary_scores.seed == seed) & (primary_scores.family == "year_trend_baseline")]
        trend_pred = primary_pred[(primary_pred.seed == seed) & (primary_pred.family == "year_trend_baseline")].set_index("row_key")
        if len(trend) != 1 or set(trend_pred.index) != set(test_keys) or not np.allclose(trend_pred.loc[test_keys].actual_q_ha, y[test], rtol=0, atol=1e-12):
            raise ValueError("Year-only comparator rows differ")
        for family in FAMILIES:
            match = baseline_pred[(baseline_pred.seed == seed) & (baseline_pred.family == family) & (baseline_pred.variant == "without_soil")].set_index("row_key")
            prior = baseline_scores[(baseline_scores.seed == seed) & (baseline_scores.family == family) & (baseline_scores.variant == "without_soil")]
            if len(prior) != 1 or set(match.index) != set(test_keys) or not np.allclose(match.loc[test_keys].actual_q_ha, y[test], rtol=0, atol=1e-12):
                raise ValueError("Annual-weather comparator rows differ")
            print(f"weather contrasts seed={seed} model={family}", flush=True)
            model, grid = b.estimators(seed, FEATURES)[family]
            fitted, cv_rmse, count = b.tune(model, grid, X[fit], y[fit], groups[fit])
            pred = fitted.predict(X[test])
            radius = b.conformal_radius(y[cal], fitted.predict(X[cal]))
            metrics = b.score(y[test], pred, radius)
            if count != 25 or int(prior.iloc[0].candidate_count) != count or not np.isfinite(list(metrics.values())).all():
                raise ValueError("Unequal candidate budget or invalid scores")
            records.append({"seed": seed, "family": family, "candidate_count": count,
                            "n_train": len(fit), "n_calibration": len(cal), "n_test": len(test),
                            "cv_rmse": cv_rmse, **metrics,
                            "annual_weather_rmse": float(prior.iloc[0].rmse), "year_only_rmse": float(trend.iloc[0].rmse),
                            "rmse_change_vs_annual": metrics["rmse"] - float(prior.iloc[0].rmse),
                            "rmse_change_vs_year": metrics["rmse"] - float(trend.iloc[0].rmse)})
            tuning.append({"seed": seed, "family": family, **fitted.research_tuning_report_})
            for i, p in zip(test, pred):
                predictions.append({"seed": seed, "family": family, "row_key": keys[i],
                                    "actual_q_ha": float(y[i]), "predicted_q_ha": float(p), "interval_radius_q_ha": radius})
            pd.DataFrame(records).to_csv(output / "split_metrics.csv", index=False)
            pd.DataFrame(predictions).to_csv(output / "predictions.csv", index=False)
            (output / "tuning_results.json").write_text(json.dumps(tuning, indent=2, default=str), encoding="utf-8")
    for path in sources:
        if b.sha256(path) != hashes[str(path.resolve())]:
            raise ValueError("Source changed during experiment")
    scores = pd.DataFrame(records)
    if len(scores) != 15 or set(p["row_key"] for p in predictions) - set(keys):
        raise ValueError("Incomplete experiment or reserved-row leakage")
    summary = scores.groupby("family").agg(mae=("mae", "mean"), rmse=("rmse", "mean"), rmse_sd=("rmse", "std"),
        r2=("r2", "mean"), coverage=("coverage_90", "mean"), width=("width_90_q_ha", "mean"),
        annual_rmse=("annual_weather_rmse", "mean"), year_rmse=("year_only_rmse", "mean"),
        change_annual=("rmse_change_vs_annual", "mean"), change_year=("rmse_change_vs_year", "mean")).reset_index()
    summary.to_csv(output / "summary.csv", index=False)
    (output / "splits.json").write_text(json.dumps(splits, indent=2), encoding="utf-8")
    lines = ["# Calendar-half weather contrasts: development results", "",
             "Exploratory follow-up on 364 frozen development rows, 13 districts, five overlapping district splits. Reserved outcomes were not scored. No application model was changed.", "",
             "Annual weather and year were retained; June–November minus December–May temperature, rainfall and humidity contrasts were added. Calendar halves are not crop-season labels. Every family received the original 25 candidates and grouped tuning folds.", "",
             "Errors and widths are q/ha. SD describes variation across overlapping splits, not a confidence interval. Negative RMSE change means lower error. R² is not percentage accuracy.", "",
             "| Family | MAE | RMSE ± SD | R² | Coverage | Width | Annual-only RMSE | Change vs annual | Change vs year-only |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in summary.itertuples():
        lines.append(f"| {r.family} | {r.mae:.3f} | {r.rmse:.3f} ± {r.rmse_sd:.3f} | {r.r2:.3f} | {r.coverage:.1%} | {r.width:.3f} | {r.annual_rmse:.3f} | {r.change_annual:+.3f} | {r.change_year:+.3f} |")
    lines += ["", f"The reused year-only control has mean RMSE {summary.iloc[0].year_rmse:.3f} q/ha. The annual-weather/year comparators come from the previous without-soil sensitivity run; their row keys and outcomes match exactly.", "",
              "## Interpretation limits", "", "This amendment was chosen after earlier development results. Repeated development comparisons can overfit the study design. This experiment provides no independent external validation, significance claim or quantum-computing advantage. Point weather, omitted management, annual outcomes and limited historical geography remain limitations. Do not deploy solely from these development scores.", "",
              "## Reproduction", "", "Run `python research/weather_contrasts.py --output research/results/NEW_UNIQUE_DIRECTORY` from the project root with the preserved panel and NASA response cache. The run verifies panel/code/source checksums, daily completeness, annual feature reconstruction, role separation, comparator keys/outcomes and all 15 candidate counts. Source snapshots, input hashes, environment, tuning results and predictions accompany this report."]
    (output / "WEATHER_CONTRASTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output / "run_manifest.json").write_text(json.dumps({**receipt,
        "completed_utc": datetime.now(timezone.utc).isoformat(), "completed_fits": len(scores),
        "output_sha256": {p.name: b.sha256(p) for p in output.iterdir() if p.is_file()}}, indent=2), encoding="utf-8")
    print(summary.to_string(index=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
