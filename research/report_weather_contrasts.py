"""Independently recompute reported scores and plot the development comparison."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import benchmark as b


def report(folder):
    manifest = json.loads((folder / "run_manifest.json").read_text())
    if manifest["reserved_outcomes_scored"] or manifest["completed_fits"] != 15:
        raise ValueError("Requires complete development-only results")
    for name, digest in manifest["output_sha256"].items():
        if b.sha256(folder / name) != digest:
            raise ValueError(f"Output checksum mismatch: {name}")
    predictions = pd.read_csv(folder / "predictions.csv")
    scores = pd.read_csv(folder / "split_metrics.csv")
    features = pd.read_csv(folder / "development_features.csv")
    splits = json.loads((folder / "splits.json").read_text())
    keys = set(features.row_key)
    if len(features) != 364 or len(keys) != 364 or not set(predictions.row_key) <= keys:
        raise ValueError("Invalid development keys")
    checked = 0
    for row in scores.itertuples():
        p = predictions[(predictions.seed == row.seed) & (predictions.family == row.family)]
        split = next(s for s in splits if s["seed"] == row.seed)
        if p.row_key.duplicated().any() or set(p.row_key) != set(split["test"]):
            raise ValueError("Prediction split keys differ")
        if p.interval_radius_q_ha.nunique() != 1 or len(p) != row.n_test or row.candidate_count != 25:
            raise ValueError("Invalid predictions or tuning budget")
        actual = p.actual_q_ha.to_numpy()
        predicted = p.predicted_q_ha.to_numpy()
        error = np.abs(actual - predicted)
        radius = float(p.interval_radius_q_ha.iloc[0])
        recomputed = {"mae": error.mean(), "median_ae": np.median(error),
                      "rmse": np.sqrt(np.mean(error ** 2)),
                      "r2": 1 - np.sum(error ** 2) / np.sum((actual - actual.mean()) ** 2),
                      "mape_pct": np.mean(error / np.abs(actual)) * 100,
                      "within_5pct": np.mean(error / np.abs(actual) <= .05),
                      "coverage_90": np.mean(error <= radius), "width_90_q_ha": 2 * radius}
        for name, value in recomputed.items():
            if not np.isclose(value, getattr(row, name), rtol=1e-10, atol=1e-10):
                raise ValueError(f"Score mismatch: {row.seed}/{row.family}/{name}")
        checked += 1
    if checked != 15:
        raise ValueError("Incomplete score verification")
    summary = pd.read_csv(folder / "summary.csv").set_index("family")
    families = ["classical_ridge", "classical_rbf_kernel_control", "quantum_simulated_entangled"]
    labels = ["Ridge", "Classical RBF kernel", "Simulated quantum kernel"]
    for family in families:
        group = scores[scores.family == family]
        for label, value in {"rmse": group.rmse.mean(), "rmse_sd": group.rmse.std(),
                             "mae": group.mae.mean(), "r2": group.r2.mean(),
                             "coverage": group.coverage_90.mean(), "width": group.width_90_q_ha.mean(),
                             "annual_rmse": group.annual_weather_rmse.mean(), "year_rmse": group.year_only_rmse.mean(),
                             "change_annual": group.rmse_change_vs_annual.mean(), "change_year": group.rmse_change_vs_year.mean()}.items():
            if not np.isclose(summary.loc[family, label], value, rtol=1e-10, atol=1e-10):
                raise ValueError("Aggregate score mismatch")
    annual = [scores[scores.family == f].annual_weather_rmse for f in families]
    updated = [scores[scores.family == f].rmse for f in families]
    fig, ax = plt.subplots(figsize=(9, 5.2), layout="constrained")
    position = np.arange(3)
    ax.barh(position-.18, [v.mean() for v in annual], height=.32,
            xerr=[v.std() for v in annual], color="#b8c5cc", capsize=4, label="Annual weather + year")
    ax.barh(position+.18, [v.mean() for v in updated], height=.32,
            xerr=[v.std() for v in updated], color="#438967", capsize=4, label="Add calendar-half contrasts")
    trend = float(scores.year_only_rmse.mean())
    ax.axvline(trend, color="#456b9b", linestyle="--", linewidth=1.5, label=f"Year-only mean: {trend:.2f}")
    ax.set_yticks(position, labels)
    ax.invert_yaxis()
    ax.set_xlim(left=0)
    ax.set_xlabel("RMSE (q/ha) · lower is better")
    ax.set_title("Do within-year weather contrasts help?", loc="left", fontsize=16, pad=16)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", alpha=.15)
    ax.set_axisbelow(True)
    ax.legend(loc="upper right", fontsize=8, frameon=False)
    fig.supxlabel("Development only · 5 overlapping district splits · error bars = split SD, not confidence intervals\n364 rows / 13 districts · final reserved outcomes unscored", fontsize=9, color="#5c6870")
    fig.savefig(folder / "weather_contrast_comparison.png", dpi=180)
    fig.savefig(folder / "weather_contrast_comparison.pdf")
    plt.close(fig)
    record = {"status": "passed", "split_score_groups_recomputed": checked,
              "prediction_rows": len(predictions), "development_rows": len(keys),
              "original_output_hashes_verified": True, "aggregate_scores_recomputed": True,
              "reserved_outcomes_scored": False, "report_source_sha256": b.sha256(Path(__file__)),
              "figure_sha256": b.sha256(folder / "weather_contrast_comparison.png")}
    (folder / "report_verification.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    report(parser.parse_args().results)
