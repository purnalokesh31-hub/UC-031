"""Verify development-only predictions and write a concise research result report."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

LABELS = {
    "mean_baseline": "Training mean", "year_trend_baseline": "Year trend only",
    "classical_ridge": "Ridge", "classical_svr": "RBF SVR",
    "classical_random_forest": "Random forest", "classical_extra_trees": "Extra Trees",
    "classical_hist_gradient_boosting": "Histogram gradient boosting",
    "classical_rbf_kernel_control": "Classical RBF kernel ridge",
    "quantum_simulated_entangled": "Simulated quantum kernel",
    "quantum_no_entanglement": "Quantum: no entanglement",
    "quantum_one_layer": "Quantum: one layer",
    "quantum_uncentered_kernel": "Quantum: uncentered kernel",
}


def report(output):
    run = json.loads((output / "run_manifest.json").read_text())
    if run["evaluation_stage"] != "development" or run["reserved_outcomes_scored"]:
        raise ValueError("This report is only for development experiments")
    if run["errors_or_skipped_crops"]:
        raise ValueError("Resolve incomplete evaluations before making a summary")
    scores = pd.read_csv(output / "split_metrics.csv")
    predictions = pd.read_csv(output / "predictions.csv", dtype={"district_id": str})
    summary = pd.read_csv(output / "district_summary.csv").sort_values("rmse_mean")
    panel = pd.read_csv(run["panel"], dtype={"district_id": str})
    lock = json.loads(Path(run["lockbox"]).read_text())
    if hashlib.sha256(Path(run["panel"]).read_bytes()).hexdigest() != run["panel_sha256"]:
        raise ValueError("Panel changed after evaluation")
    cfg = lock["crops"]["Rice"]
    fit = panel[(~panel.district_id.isin(cfg["held_out_district_ids"])) & (panel.year < cfg["calibration_year"])]
    allowed = set(fit.crop + "|" + fit.season + "|" + fit.year.astype(str) + "|" + fit.district_id)
    if not set(predictions.row_key).issubset(allowed):
        raise ValueError("Prediction rows escaped the frozen development pool")
    if set(scores.seed) != set(run["district_repeats"]) or not scores.groupby("family").size().eq(5).all():
        raise ValueError("Expected all five declared repeats for every family")
    if set(scores.family) != set(LABELS):
        raise ValueError("Missing or unexpected model family")
    if not np.isfinite(scores[["mae", "rmse", "r2", "coverage_90", "width_90_q_ha"]]).all().all():
        raise ValueError("Nonfinite regression result")
    tuned = scores.family.str.startswith(("classical_", "quantum_"))
    if not scores.loc[tuned, "candidate_count"].eq(25).all():
        raise ValueError("Unequal candidate budgets")
    comparison = pd.read_csv(output / "paired_split_deltas.csv")
    quantum = summary[summary.family == "quantum_simulated_entangled"].iloc[0]
    classical = summary[summary.family.str.startswith("classical_")].iloc[0]
    year_only = summary[summary.family == "year_trend_baseline"].iloc[0]
    delta = quantum.rmse_mean - classical.rmse_mean
    lines = ["# Annual rice pilot: development results", "",
             "Exploratory development results only. Final geographic and future-year cohorts were not scored.", "",
             "## What was evaluated", "",
             "544 district-year records, 17 historical district units, agricultural years 1981–82 to 2012–13. "
             "Only the frozen development pool of 364 rows in 13 districts was used for these experiments. "
             "Each of five splits held out three development districts and used separate calibration districts.", "",
             "Inputs: four SoilGrids mapped topsoil estimates, NASA annual temperature/rainfall/humidity at "
             "documented reference points, and a year trend. Outcomes are reported district rice yields. "
             "This is retrospective annual estimation, not a farm-level forecast.", "",
             "## Comparison", "",
             "All tuned families received 25 candidates and the same grouped inner folds for each split. "
             "The mean and year-only baselines are untuned. Values below are means across five overlapping splits. "
             "The ± term is split standard deviation, not a confidence interval.", "",
             "| Model | MAE (q/ha) | RMSE ± SD (q/ha) | R² | 90% interval coverage | Interval width (q/ha) |",
             "|---|---:|---:|---:|---:|---:|"]
    for r in summary.itertuples():
        lines.append(f"| {LABELS[r.family]} | {r.mae_mean:.3f} | {r.rmse_mean:.3f} ± {r.rmse_sd_across_splits:.3f} | {r.r2_mean:.3f} | {r.coverage_90_mean:.1%} | {r.width_90_q_ha_mean:.3f} |")
    lines += ["", "## Interpretation", "",
              f"The classical family with the lowest mean development RMSE was {LABELS[classical.family]}. "
              f"The main simulated quantum kernel's mean RMSE difference relative to that family was {delta:+.3f} q/ha "
              "(positive means larger error). This is an exploratory ranking, not a final-test superiority claim.", "",
              f"The year-only baseline scored RMSE {year_only.rmse_mean:.3f} q/ha and mean R² {year_only.r2_mean:.3f}. "
              f"The lowest mean RMSE across all models and controls was {LABELS[summary.iloc[0].family]}. "
              "This comparison is essential: additional weather, mapped soil and model complexity have not yet established useful improvement over a simple time trend on these district holdouts.", "",
              "R² is not percentage accuracy. Nominal 90% intervals can miss their target under geographic shift. "
              "Each outer test has only three districts, so cluster-bootstrap bounds are unstable; "
              "overlapping repeats and multiple comparisons further limit significance claims.", "",
              "The model evaluates a four-qubit fidelity kernel exactly on a classical computer. "
              "These results do not demonstrate a quantum-computing advantage.", "",
              "## Verification", "",
              "- All 12 model/control variants completed all five district splits.",
              "- Every prediction row belongs to the frozen fit pool; no final reserved district or year appears.",
              "- Equal candidate budgets, finite metrics and panel checksum checked.",
              "- Predictions, per-split scores, tuning parameters/times and paired district-bootstrap differences are retained beside this report.", "",
              "## Before publication", "",
              "1. Evaluate weather-only/no-soil and year-trend sensitivity without opening the final test cohorts.",
              "2. Investigate reference-point representativeness and exclusions of three districts with unavailable soil estimates.",
              "3. Obtain independently sourced external yield observations and agronomic review where feasible.",
              "4. Complete the novelty review, finalize the analysis, and then run the reserved evaluation once.", "",
              "Static modern mapped soil is not a historical soil measurement. The sample is geographically small and historical. "
              "Strong publication claims and app deployment remain premature.", "",
              "Metadata clarification: the generic run-manifest limitation text mentions centroid sampling and absence of a technology trend. "
              "For this pilot, the actual inputs use source-listed reference points (not verified centroids) and explicitly include year_trend. "
              "The panel manifest and this report contain the study-specific definitions."]
    (output / "PILOT_RESULTS.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    labels = [LABELS[f] for f in summary.family]
    colors = ["#246849" if f == "quantum_simulated_entangled" else "#759484" if f.startswith("quantum_") else "#738295" for f in summary.family]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig, axes = plt.subplots(1, 2, figsize=(13, 7), gridspec_kw={"width_ratios": [1.2, 1]})
    y = np.arange(len(summary))
    axes[0].barh(y, summary.rmse_mean, xerr=summary.rmse_sd_across_splits, color=colors, capsize=3)
    axes[0].set_yticks(y, labels)
    axes[0].invert_yaxis()
    axes[0].set_xlabel("RMSE (q/ha), lower is better")
    axes[0].set_title("Prediction error")
    axes[1].scatter(summary.coverage_90_mean * 100, y, c=colors, s=55)
    axes[1].axvline(90, color="#c17836", linestyle="--", label="Nominal 90%")
    axes[1].set_yticks(y, [""]*len(y))
    axes[1].invert_yaxis()
    axes[1].set_xlim(0, 102)
    axes[1].set_xlabel("Observed interval coverage (%)")
    axes[1].set_title("Uncertainty calibration")
    axes[1].legend(loc="lower left")
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="x", alpha=.18)
        ax.set_axisbelow(True)
    fig.suptitle("Annual rice yield: development district holdouts", fontsize=16)
    fig.text(.5, .02, "Five overlapping splits; error bars show split SD. Final geographic/time tests remain unscored.", ha="center", fontsize=9)
    fig.tight_layout(rect=[0, .045, 1, .94])
    fig.savefig(output / "development_comparison.png", dpi=180)
    plt.close(fig)
    print(json.dumps({"classical_lowest_mean_rmse": classical.family,
                      "classical_rmse": float(classical.rmse_mean), "quantum_rmse": float(quantum.rmse_mean),
                      "quantum_r2": float(quantum.r2_mean), "prediction_rows_verified": len(predictions),
                      "paired_comparisons": len(comparison), "report": str(output / "PILOT_RESULTS.md")}, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results", type=Path, required=True)
    args = p.parse_args()
    report(args.results)
