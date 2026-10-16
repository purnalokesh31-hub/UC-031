"""Exploratory real-harvest benchmark for CropGuard's rice input subset.

This deliberately does not alter the deployed synthetic-data model. The source
survey does not contain the app's full eight inputs, so this evaluates only the
small, definition-matched subset and keeps the app's missing variables out.
"""

from __future__ import annotations

import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "external" / "cimmyt_rice_2026" / "NUE_survey_dataset_v2.csv"
OUT = ROOT / "results" / "cimmyt_rice_input_only_20261006"
OUT.mkdir(parents=True, exist_ok=True)

FEATURES = ["N_kg_ha", "P2O5_ha", "K2O_ha", "SoilGrids_phh2o"]
FEATURES_WITH_RAIN = FEATURES + ["total_precip"]
TARGET = "yield_kg_ha"
GROUP = "Dataset"


def build_models(seed: int):
    return {
        "training_median": DummyRegressor(strategy="median"),
        "ridge": make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=10.0)),
        "random_forest": make_pipeline(
            SimpleImputer(strategy="median"),
            RandomForestRegressor(
                n_estimators=120, min_samples_leaf=12, max_features=0.9,
                random_state=seed, n_jobs=-1,
            ),
        ),
        "extra_trees": make_pipeline(
            SimpleImputer(strategy="median"),
            ExtraTreesRegressor(
                n_estimators=120, min_samples_leaf=12, max_features=0.9,
                random_state=seed, n_jobs=-1,
            ),
        ),
        "hist_gradient_boosting": make_pipeline(
            SimpleImputer(strategy="median"),
            HistGradientBoostingRegressor(
                max_iter=120, learning_rate=0.06, max_leaf_nodes=15,
                min_samples_leaf=35, l2_regularization=1.0,
                random_state=seed,
            ),
        ),
    }


def metrics(y, pred):
    return {
        "n": int(len(y)),
        "mae_q_ha": float(mean_absolute_error(y, pred) / 100.0),
        "rmse_q_ha": float(mean_squared_error(y, pred) ** 0.5 / 100.0),
        "r2": float(r2_score(y, pred)),
        "mae_kg_ha": float(mean_absolute_error(y, pred)),
        "rmse_kg_ha": float(mean_squared_error(y, pred) ** 0.5),
        "p90_abs_error_q_ha": float(np.quantile(np.abs(y - pred), 0.90) / 100.0),
    }


def main():
    raw = pd.read_csv(DATA, low_memory=False)
    initial_n = len(raw)
    reasons = {}

    def retain(mask, label):
        nonlocal raw
        mask = mask.fillna(False) if hasattr(mask, "fillna") else np.asarray(mask, dtype=bool)
        before = len(raw)
        raw = raw.loc[mask].copy()
        reasons[label] = {"removed": int(before - len(raw)), "remaining": int(len(raw))}

    # Replicate the paper's published harvest/plot validity filters where the
    # deposited harmonized file exposes the corresponding fields. We do not
    # attempt the region-polygon check because the paper's boundaries/code are
    # not in this data package; this limitation is disclosed in the report.
    retain(raw["SEASON"].eq("Kharif"), "monsoon_kharif")
    retain(raw["EST_binary"].eq("Transplanted"), "transplanted")
    for col in [TARGET, "N_kg_ha", "P2O5_ha", "K2O_ha", "SoilGrids_phh2o"]:
        raw[col] = pd.to_numeric(raw[col], errors="coerce")
    retain(np.isfinite(raw[TARGET]) & raw[TARGET].between(500, 10_000), "yield_0_5_to_10_t_ha")
    retain(np.isfinite(raw["N_kg_ha"]) & raw["N_kg_ha"].between(0.000001, 400), "nitrogen_0_to_400_kg_ha")
    for col, low, high, label in [
        ("Nursery_duration", 0, 100, "nursery_duration_0_to_100_days"),
        ("Field_duration", 60, 300, "field_duration_60_to_300_days"),
        ("Crop_duration", 90, 340, "crop_duration_90_to_340_days"),
    ]:
        vals = pd.to_numeric(raw[col], errors="coerce")
        retain(vals.isna() | vals.between(low, high), label)

    # Valid chemistry/rate ranges and finite rows; no target-derived columns,
    # harvest outcomes, post-harvest variables, IDs, region or year are used.
    for col in ["P2O5_ha", "K2O_ha"]:
        retain(np.isfinite(raw[col]) & raw[col].between(0, 500), f"{col}_finite_0_to_500")
    retain(np.isfinite(raw["SoilGrids_phh2o"]) & raw["SoilGrids_phh2o"].between(3, 10), "soil_ph_3_to_10")

    frames = {"four_input_fields": FEATURES, "four_inputs_plus_annual_precip": FEATURES_WITH_RAIN}
    predictions = []
    summaries = []
    per_groups = []

    for variant, feature_cols in frames.items():
        frame = raw.dropna(subset=feature_cols + [TARGET, GROUP]).copy()
        frame = frame[np.isfinite(frame[feature_cols + [TARGET]].to_numpy()).all(axis=1)]
        groups = sorted(frame[GROUP].astype(str).unique())
        for model_name in build_models(1407):
            model = build_models(1407)[model_name]
            model_oof = []
            for group in groups:
                train = frame[GROUP].astype(str).ne(group)
                test = ~train
                model.fit(frame.loc[train, feature_cols], frame.loc[train, TARGET])
                pred = model.predict(frame.loc[test, feature_cols])
                held = frame.loc[test, ["Merged_ID", "Region", "Dataset", "year", TARGET]].copy()
                held["variant"] = variant
                held["model"] = model_name
                held["prediction_kg_ha"] = pred
                held["error_kg_ha"] = pred - held[TARGET].to_numpy()
                predictions.append(held)
                model_oof.append(held)
            pred_frame = pd.concat(model_oof, ignore_index=True)
            summary = {"variant": variant, "model": model_name, "features": feature_cols,
                       "survey_datasets": len(groups), "complete_case_n": int(len(frame)),
                       **metrics(pred_frame[TARGET].to_numpy(), pred_frame["prediction_kg_ha"].to_numpy())}
            summaries.append(summary)
            for group, sub in pred_frame.groupby("Dataset", sort=True):
                per_groups.append({"variant": variant, "model": model_name,
                                   "Dataset": group, "Region": sub["Region"].iloc[0],
                                   **metrics(sub[TARGET].to_numpy(), sub["prediction_kg_ha"].to_numpy())})

    pred_all = pd.concat(predictions, ignore_index=True)
    # Prespecified ensemble of the four non-constant model families. Since it
    # is formed from out-of-fold predictions for each held-out survey, its
    # benchmark metrics remain genuinely held out as well.
    ensemble = (pred_all[~pred_all["model"].eq("training_median")]
                .groupby(["variant", "Merged_ID", "Region", "Dataset", "year", TARGET], dropna=False)
                .agg(prediction_kg_ha=("prediction_kg_ha", "mean"))
                .reset_index())
    ensemble["variant_model"] = ensemble["variant"]
    ensemble["model"] = "fixed_mean_ensemble"
    ensemble["error_kg_ha"] = ensemble["prediction_kg_ha"] - ensemble[TARGET]
    pred_all = pd.concat([pred_all, ensemble], ignore_index=True, sort=False)
    summary_df = pd.DataFrame(summaries).sort_values(["variant", "mae_q_ha"])
    for variant, sub in ensemble.groupby("variant"):
        summaries.append({"variant": variant, "model": "fixed_mean_ensemble",
                          "features": frames[variant],
                          "survey_datasets": int(sub["Dataset"].nunique()),
                          "complete_case_n": int(len(sub)),
                          **metrics(sub[TARGET].to_numpy(), sub["prediction_kg_ha"].to_numpy())})
    summary_df = pd.DataFrame(summaries).sort_values(["variant", "mae_q_ha"])
    group_df = pd.DataFrame(per_groups).sort_values(["variant", "model", "Dataset"])
    ensemble_groups = []
    for (variant, group), sub in ensemble.groupby(["variant", "Dataset"], sort=True):
        ensemble_groups.append({"variant": variant, "model": "fixed_mean_ensemble",
                                "Dataset": group, "Region": sub["Region"].iloc[0],
                                **metrics(sub[TARGET].to_numpy(), sub["prediction_kg_ha"].to_numpy())})
    group_df = pd.concat([group_df, pd.DataFrame(ensemble_groups)], ignore_index=True)
    region_predictions = []
    region_summaries = []
    for variant, feature_cols in frames.items():
        frame = raw.dropna(subset=feature_cols + [TARGET, "Region"]).copy()
        frame = frame[np.isfinite(frame[feature_cols + [TARGET]].to_numpy()).all(axis=1)]
        for model_name in build_models(1407):
            for region in sorted(frame["Region"].astype(str).unique()):
                train = frame["Region"].astype(str).ne(region)
                test = ~train
                model = build_models(1407)[model_name]
                model.fit(frame.loc[train, feature_cols], frame.loc[train, TARGET])
                pred = model.predict(frame.loc[test, feature_cols])
                held = frame.loc[test, ["Merged_ID", "Region", "Dataset", "year", TARGET]].copy()
                held["variant"] = variant
                held["model"] = model_name
                held["prediction_kg_ha"] = pred
                held["error_kg_ha"] = pred - held[TARGET].to_numpy()
                region_predictions.append(held)
        out = pd.concat([row for row in region_predictions if row["variant"].iloc[0] == variant], ignore_index=True)
        region_summaries.append({"variant": variant, "model": "each_fixed_recipe",
                                 "features": feature_cols, "held_out_regions": int(out["Region"].nunique()),
                                 "complete_case_n": int(len(out) // len(build_models(1407))),
                                 **metrics(out[TARGET].to_numpy(), out["prediction_kg_ha"].to_numpy())})
        ensemble_region = (out[~out["model"].eq("training_median")]
                           .groupby(["Merged_ID", "Region", "Dataset", "year", TARGET], dropna=False)
                           .agg(prediction_kg_ha=("prediction_kg_ha", "mean"))
                           .reset_index())
        region_summaries.append({"variant": variant, "model": "fixed_mean_ensemble",
                                 "features": feature_cols, "held_out_regions": int(ensemble_region["Region"].nunique()),
                                 "complete_case_n": int(len(ensemble_region)),
                                 **metrics(ensemble_region[TARGET].to_numpy(), ensemble_region["prediction_kg_ha"].to_numpy())})
        for region, sub in ensemble_region.groupby("Region", sort=True):
            region_summaries.append({"variant": variant, "model": "fixed_mean_ensemble_by_region",
                                     "features": feature_cols, "held_out_region": region,
                                     "complete_case_n": int(len(sub)),
                                     **metrics(sub[TARGET].to_numpy(), sub["prediction_kg_ha"].to_numpy())})
    pred_all.to_csv(OUT / "grouped_holdout_predictions.csv.gz", index=False, compression="gzip")
    summary_df.to_csv(OUT / "grouped_holdout_metrics.csv", index=False)
    group_df.to_csv(OUT / "per_survey_dataset_metrics.csv", index=False)
    region_predictions_df = pd.concat(region_predictions, ignore_index=True)
    region_predictions_df.to_csv(OUT / "region_holdout_predictions.csv.gz", index=False, compression="gzip")
    region_metrics_df = pd.DataFrame(region_summaries)
    region_metrics_df.to_csv(OUT / "region_holdout_metrics.csv", index=False)

    # The current demo's rice inputs are 100 / 50 / 50 kg/ha, pH 6.3.
    # P/K are evaluated as common fertilizer-label P2O5/K2O rates and as
    # elemental P/K converted to oxide rates. Both are explicitly conditional.
    input_scenarios = {
        "P_K_values_are_fertilizer_grade_P2O5_K2O": {
            "N_kg_ha": 100.0, "P2O5_ha": 50.0, "K2O_ha": 50.0,
            "SoilGrids_phh2o": 6.3,
        },
        "P_K_values_are_elemental_P_K_converted_to_oxides": {
            "N_kg_ha": 100.0, "P2O5_ha": 50.0 * 2.291, "K2O_ha": 50.0 * 1.205,
            "SoilGrids_phh2o": 6.3,
        },
    }
    # A pooled fit here is only for an exploratory, partial-input display. It
    # does not turn this cross-validated research benchmark into a deployed
    # field model, particularly because the UI's weather fields are unmatched.
    inference = []
    for scenario_name, values in input_scenarios.items():
        query = pd.DataFrame([values], columns=FEATURES)
        family_estimates = []
        for model_name in ["ridge", "random_forest", "extra_trees", "hist_gradient_boosting"]:
            final = build_models(1407)[model_name]
            final.fit(raw[FEATURES], raw[TARGET])
            family_estimates.append(float(final.predict(query)[0]))
        estimate_kg_ha = float(np.mean(family_estimates))
        benchmark = summary_df.query("variant == 'four_input_fields' and model == 'fixed_mean_ensemble'").iloc[0]
        inference.append({
            "scenario": scenario_name, "model": "fixed_mean_ensemble", "estimate_kg_ha": estimate_kg_ha,
            "estimate_q_ha": estimate_kg_ha / 100.0,
            "constituent_model_estimates_q_ha": [float(value / 100.0) for value in family_estimates],
            "validation_mae_q_ha": float(benchmark["mae_q_ha"]),
            "validation_rmse_q_ha": float(benchmark["rmse_q_ha"]),
            "validation_p90_abs_error_q_ha": float(benchmark["p90_abs_error_q_ha"]),
            "n_training_rows": int(len(raw)),
            "input_fields_used": FEATURES,
            "input_fields_ignored_due_to_source_mismatch": ["moisture", "temperature", "humidity", "rainfall"],
        })

    report = {
        "source": {
            "citation": "Coggins et al. (2024), Farmer field survey dataset underpinning Data-driven strategies to improve nitrogen use efficiency of rice farming in South Asia, CIMMYT Dataverse, version 3.1; CC0 1.0.",
            "doi_or_persistent_id": "https://hdl.handle.net/11529/10549105",
            "file": DATA.name,
            "raw_rows": int(initial_n),
            "raw_columns": int(pd.read_csv(DATA, nrows=0).shape[1]),
            "md5": "c7223de8068f16284f3768408f1730a0",
            "target_note": "Yield is farmer-reported for most fields; the paper documents crop-cut measurement for about 40% of Bangladesh floodplain yield records and about 25% of Punjab/Haryana records. The harmonized file has no row-level measurement-method flag, so this benchmark cannot isolate crop-cut-only targets.",
        },
        "filter_counts": {"raw_n": int(initial_n), "stages": reasons, "final_n": int(len(raw))},
        "feature_mapping": {
            "N_kg_ha": "Applied nitrogen rate; definition matches fertilizer-input nitrogen in kg/ha.",
            "P2O5_ha": "Applied mineral phosphorus expressed as P2O5 kg/ha; app's generic P unit is ambiguous.",
            "K2O_ha": "Applied mineral potassium expressed as K2O kg/ha; app's generic K unit is ambiguous.",
            "SoilGrids_phh2o": "SoilGrids topsoil pH(H2O), 0-5 cm; not a field/lab measurement of the actual plot.",
            "total_precip": "CHIRPS precipitation total for the calendar year of the crop; not interchangeable with the app's unqualified 0-500 mm rainfall input.",
            "not_present": ["soil moisture", "temperature", "relative humidity"],
        },
        "protocol": {
            "target": "yield_kg_ha, translated to q/ha for metrics",
            "validation": "Leave one underlying survey Dataset out, in turn. The identifier and all location/year/crop outcome features are excluded from predictors.",
            "model_selection": "Untuned, fixed-configuration exploratory comparison; no model selected for deployment. Candidate recipes share the same grouped outer holdouts.",
            "target_quality": "Published paper's available crop/season/target/input/duration exclusion filters were applied. Coordinate-within-region polygon exclusion was not recreated because the public package lacks the polygons/code.",
            "uncertainty": "p90 absolute grouped-holdout error is a descriptive error scale, not a calibrated prediction interval.",
            "random_seed": 1407,
            "software": {"python": platform.python_version(), "pandas": pd.__version__,
                         "numpy": np.__version__, "scikit_learn": sklearn.__version__},
        },
        "model_metrics": summary_df.to_dict(orient="records"),
        "region_holdout_metrics": region_metrics_df.to_dict(orient="records"),
        "input_estimates": inference,
    }
    (OUT / "benchmark_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("filtered_rows", len(raw))
    print("feature_complete_cases", {name: int(raw.dropna(subset=features + [TARGET, GROUP]).shape[0]) for name, features in frames.items()})
    print("model_metrics")
    print(summary_df[["variant", "model", "complete_case_n", "mae_q_ha", "rmse_q_ha", "r2", "p90_abs_error_q_ha"]].round(3).to_string(index=False))
    print("input_estimates")
    print(json.dumps(inference, indent=2))
    print("region_holdout_metrics")
    print(region_metrics_df[["variant", "model", "held_out_regions", "held_out_region", "complete_case_n", "mae_q_ha", "rmse_q_ha", "r2"]].round(3).to_string(index=False))
    print("outputs", OUT)


if __name__ == "__main__":
    main()
