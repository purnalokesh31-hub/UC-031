"""Descriptive development-error audit; no fitting, tuning or reserved-data access."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def diagnose(folder):
    manifest = json.loads((folder / "run_manifest.json").read_text())
    if manifest["reserved_outcomes_scored"] or manifest["evaluation_stage"] != "development":
        raise ValueError("Requires development-only experiment")
    features = pd.read_csv(folder / "development_features.csv").set_index("row_key")
    predictions = pd.read_csv(folder / "predictions.csv")
    predictions["district_id"] = predictions.row_key.str.rsplit("|", n=1).str[-1]
    if not set(predictions.row_key) <= set(features.index):
        raise ValueError("Predictions include nondevelopment rows")
    tuning = json.loads((folder / "tuning_results.json").read_text())
    splits = json.loads((folder / "splits.json").read_text())
    rows, ranges = [], []
    for split in splits:
        train = features.loc[split["train"]]
        test = features.loc[split["test"]]
        lo, hi = train.min(), train.max()
        outside = test.lt(lo) | test.gt(hi)
        for feature in features.columns:
            ranges.append({"seed": split["seed"], "feature": feature,
                           "training_min": lo[feature], "training_max": hi[feature],
                           "test_min": test[feature].min(), "test_max": test[feature].max(),
                           "test_fraction_outside_training_minmax": outside[feature].mean()})
        for (family, district), group in predictions[predictions.seed == split["seed"]].groupby(["family", "district_id"]):
            error = group.predicted_q_ha - group.actual_q_ha
            rows.append({"seed": split["seed"], "family": family, "district_id": district,
                         "rows": len(group), "mae_q_ha": error.abs().mean(),
                         "rmse_q_ha": np.sqrt(np.mean(error ** 2)), "bias_q_ha": error.mean(),
                         "interval_coverage": (error.abs() <= group.interval_radius_q_ha).mean(),
                         "fraction_any_input_outside_training_minmax": outside.loc[group.row_key].any(axis=1).mean()})
    errors = pd.DataFrame(rows)
    shifts = pd.DataFrame(ranges)
    errors.to_csv(folder / "district_error_diagnostics.csv", index=False)
    shifts.to_csv(folder / "feature_range_diagnostics.csv", index=False)
    quantum = errors[errors.family == "quantum_simulated_entangled"].sort_values("rmse_q_ha", ascending=False)
    worst = quantum.iloc[0]
    chosen = next(r for r in tuning if r["seed"] == int(worst.seed) and r["family"] == worst.family)
    lines = ["# Weather-contrast failure investigation", "",
             "Post-hoc descriptive analysis of development predictions only. No new fitting or final-test access. Training min/max checks are a coarse shift indicator; they are neither a density model nor evidence of causation.", "",
             "## Largest quantum district errors", "",
             "| Split seed | District | RMSE q/ha | Bias q/ha | 90% coverage | Rows outside any training input range |",
             "|---|---|---:|---:|---:|---:|"]
    for r in quantum.head(5).itertuples():
        lines.append(f"| {r.seed} | {r.district_id} | {r.rmse_q_ha:.3f} | {r.bias_q_ha:+.3f} | {r.interval_coverage:.1%} | {r.fraction_any_input_outside_training_minmax:.1%} |")
    lines += ["", "## What this suggests investigating", "",
              f"The largest district error occurs at seed {int(worst.seed)}, {worst.district_id}. Its quantum fit used `{chosen['best_params']}` selected inside grouped training CV. Very weak regularization is one possible contributor to instability; this observational association does not establish the cause.", "",
              "A future, separately declared development experiment could compare a regularization floor or a more conservative inner-CV selection rule for both quantum and classical kernel models. Keep the current results, candidate accounting and unchanged outer assignments. Do not choose a threshold by minimizing these outer test errors or open reserved outcomes to settle it.", "",
              "Also investigate weather support and omitted irrigation/management. Better numerical stability alone would not validate the district point inputs, add independent evidence, or establish agronomic usefulness.", "",
              "All district/family errors and every feature's training/test min/max are retained in the two diagnostic CSV files. District identifiers follow the frozen historical DLD panel; they are not current administrative units."]
    (folder / "FAILURE_DIAGNOSIS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(quantum.head(5).to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    diagnose(parser.parse_args().results)
