"""Leakage-aware crop-yield benchmark for a prepared district-season panel.

Defaults to repeated district holdouts within frozen development rows only.
Reserved spatial and temporal cohorts require the separate reserved stage.
Results are only pristine if outcomes have not been inspected before and the
protocol/configuration was frozen in advance.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.kernel_ridge import KernelRidge
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, median_absolute_error, r2_score
from sklearn.model_selection import GridSearchCV, GroupKFold, GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "backend"))
from models.validated_yield import QuantumKernelRegressor  # noqa: E402

FEATURES = ["soil_nitrogen", "soil_ph", "soil_soc", "soil_clay",
            "season_mean_temp_c", "season_p95_max_temp_c",
            "season_precip_mm", "season_mean_rh_pct"]
REQUIRED = ["district_id", "year", "crop", "season", "yield_q_ha", *FEATURES]
SEEDS = [17, 29, 41, 53, 67]
N_CANDIDATES = 25
METRICS = ["mae", "median_ae", "rmse", "r2", "mape_pct", "within_5pct", "coverage_90", "width_90_q_ha"]


class QuantumKernelAblation(QuantumKernelRegressor):
    """Same exact 4-qubit map with a switch to remove the CNOT entanglers."""
    def __init__(self, angle_scale=0.05, alpha=1e-5, layers=2,
                 center_kernel=True, entangle=True):
        super().__init__(angle_scale=angle_scale, alpha=alpha,
                         layers=layers, center_kernel=center_kernel)
        self.entangle = entangle

    def _states(self, X):
        angles = self.scaler_.transform(X) * self.angle_scale
        states = np.zeros((len(X), 16), dtype=complex)
        states[:, 0] = 1
        basis = np.arange(16)
        for _ in range(self.layers):
            for q in range(4):
                low = basis[(basis & (1 << q)) == 0]
                high = low | (1 << q)
                theta = (np.pi / 2 + angles[:, q])[:, None]
                phase = np.exp(0.5j * angles[:, q + 4])[:, None]
                a, b = states[:, low].copy(), states[:, high].copy()
                states[:, low] = (np.cos(theta / 2) * a - np.sin(theta / 2) * b) / phase
                states[:, high] = (np.sin(theta / 2) * a + np.cos(theta / 2) * b) * phase
            if self.entangle:
                for q in range(3):
                    permutation = basis ^ (((basis >> q) & 1) << (q + 1))
                    states = states[:, permutation]
        return states


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classical_grid(seed: int) -> list[dict]:
    """Exactly 25 tuned configurations, five from each classical family."""
    grid = []
    grid += [{"model": [Ridge()], "model__alpha": [a]} for a in [0.01, 0.1, 1, 10, 100]]
    grid += [{"model": [SVR(kernel="rbf")], "model__C": [c],
              "model__gamma": [g], "model__epsilon": [e]}
             for c, g, e in [(0.3, "scale", 0.1), (1, "scale", 0.1),
                             (10, "scale", 0.1), (30, 0.03, 0.2), (100, 0.01, 0.2)]]
    for cls, params in [
        (RandomForestRegressor, [(100, 1), (250, 1), (300, 2), (500, 2), (300, 4)]),
        (ExtraTreesRegressor, [(100, 1), (250, 1), (300, 2), (500, 2), (300, 4)]),
    ]:
        grid += [{"model": [cls(n_estimators=n, random_state=seed, n_jobs=1)],
                  "model__min_samples_leaf": [leaf]}
                 for n, leaf in params]
    grid += [{"model": [HistGradientBoostingRegressor(random_state=seed, max_iter=150)],
              "model__max_leaf_nodes": [nodes], "model__l2_regularization": [reg]}
             for nodes, reg in [(7, 0), (7, 1), (15, 0), (15, 1), (31, 5)]]
    assert len(grid) == N_CANDIDATES
    return grid


def quantum_grid() -> list[dict]:
    # 5 x 5 = 25 configurations; two-layer encoding and centered kernel fixed.
    return [{"angle_scale": [angle], "alpha": [alpha], "layers": [2],
             "center_kernel": [True]}
            for angle, alpha in itertools.product(
                [0.01, 0.03, 0.05, 0.15, 0.4],
                [1e-8, 1e-6, 1e-5, 1e-3, 1e-1])]


def quantum_ablation_grid(layers: int, center: bool, entangle: bool) -> list[dict]:
    return [{"angle_scale": [angle], "alpha": [alpha], "layers": [layers],
             "center_kernel": [center], "entangle": [entangle]}
            for angle, alpha in itertools.product(
                [0.01, 0.03, 0.05, 0.15, 0.4],
                [1e-8, 1e-6, 1e-5, 1e-3, 1e-1])]


def classical_rbf_grid() -> list[dict]:
    # Classical kernel comparator with the same 25-candidate tuning budget.
    return [{"alpha": [alpha], "gamma": [gamma]}
            for alpha, gamma in itertools.product(
                [1e-5, 1e-3, 1e-1, 1.0, 10.0],
                [0.001, 0.01, 0.1, 1.0, 10.0])]


def estimators(seed: int, features=None) -> dict:
    def scaled(model, grid):
        pipeline = Pipeline([("scale", StandardScaler()), ("model", model)])
        estimator = TransformedTargetRegressor(regressor=pipeline, transformer=StandardScaler())
        return estimator, [{f"regressor__model__{key}": values for key, values in setting.items()}
                           for setting in grid]

    candidates = {
        "mean_baseline": (None, None),
        "classical_ridge": scaled(Ridge(), [{"alpha": [a]} for a in np.logspace(-5, 5, 25)]),
        "classical_svr": scaled(SVR(kernel="rbf"), [
            {"C": [c], "gamma": [g], "epsilon": [0.1]}
            for c, g in itertools.product([0.1, 1, 10, 100, 1000], [0.001, 0.01, 0.1, 1, 10])]),
        "classical_random_forest": scaled(RandomForestRegressor(n_estimators=200, random_state=seed, n_jobs=1), [
            {"min_samples_leaf": [leaf], "max_features": [fraction]}
            for leaf, fraction in itertools.product([1, 2, 4, 8, 16], [0.25, 0.5, 0.75, 1.0, "sqrt"])]),
        "classical_extra_trees": scaled(ExtraTreesRegressor(n_estimators=200, random_state=seed, n_jobs=1), [
            {"min_samples_leaf": [leaf], "max_features": [fraction]}
            for leaf, fraction in itertools.product([1, 2, 4, 8, 16], [0.25, 0.5, 0.75, 1.0, "sqrt"])]),
        "classical_hist_gradient_boosting": scaled(HistGradientBoostingRegressor(
            random_state=seed, max_iter=200, early_stopping=False), [
                {"max_leaf_nodes": [leaves], "l2_regularization": [reg]}
                for leaves, reg in itertools.product([3, 7, 15, 31, 63], [0, 0.1, 1, 10, 100])]),
        "quantum_simulated_entangled": (QuantumKernelRegressor(), quantum_grid()),
        "classical_rbf_kernel_control": scaled(KernelRidge(kernel="rbf"), classical_rbf_grid()),
        "quantum_no_entanglement": (QuantumKernelAblation(entangle=False),
                                     quantum_ablation_grid(2, True, False)),
        "quantum_one_layer": (QuantumKernelAblation(layers=1),
                              quantum_ablation_grid(1, True, True)),
        "quantum_uncentered_kernel": (QuantumKernelAblation(center_kernel=False),
                                       quantum_ablation_grid(2, False, True)),
    }
    for name, (_, grid) in candidates.items():
        if grid is not None and len(grid) != N_CANDIDATES:
            raise ValueError(f"{name}: unequal tuning candidate count")
    if features is not None and "year_trend" in features:
        candidates["year_trend_baseline"] = (Pipeline([
            ("year", ColumnTransformer([("year", "passthrough", [features.index("year_trend")])])),
            ("model", LinearRegression())]), [{}])
    return candidates


def conformal_radius(y: np.ndarray, pred: np.ndarray, level: float = 0.90) -> float:
    if len(y) == 0 or not 0 < level < 1:
        raise ValueError("Conformal calibration requires observations and a level between 0 and 1")
    residuals = np.abs(y - pred)
    rank = int(np.ceil((len(residuals) + 1) * level))
    if rank > len(residuals):
        raise ValueError("Too few calibration observations for a finite interval at this level")
    return float(np.partition(residuals, rank - 1)[rank - 1])


def score(y: np.ndarray, pred: np.ndarray, radius: float) -> dict:
    ae = np.abs(y - pred)
    return {
        "mae": float(mean_absolute_error(y, pred)),
        "median_ae": float(median_absolute_error(y, pred)),
        "rmse": float(np.sqrt(mean_squared_error(y, pred))),
        "r2": float(r2_score(y, pred)) if len(y) > 1 else None,
        "mape_pct": float(np.mean(ae / np.maximum(np.abs(y), 1e-8)) * 100),
        "within_5pct": float(np.mean(ae / np.maximum(np.abs(y), 1e-8) <= 0.05)),
        "coverage_90": float(np.mean(ae <= radius)),
        "width_90_q_ha": float(2 * radius),
    }


def cluster_bootstrap_ci(y: np.ndarray, pred: np.ndarray, groups: np.ndarray,
                         radius: float, seed: int, replicates: int = 1000) -> dict:
    """Percentile intervals resampling districts as clusters, not individual rows."""
    rng = np.random.default_rng(seed)
    unique = np.unique(groups)
    by_group = {g: np.flatnonzero(groups == g) for g in unique}
    sampled_scores = {name: [] for name in ["mae", "rmse", "r2", "coverage_90"]}
    for _ in range(replicates):
        picked = rng.choice(unique, size=len(unique), replace=True)
        idx = np.concatenate([by_group[g] for g in picked])
        metric = score(y[idx], pred[idx], radius)
        for name in sampled_scores:
            sampled_scores[name].append(metric[name])
    intervals = {}
    for name, values in sampled_scores.items():
        low, high = np.quantile(values, [0.025, 0.975])
        intervals[f"{name}_ci95_low"] = float(low)
        intervals[f"{name}_ci95_high"] = float(high)
    intervals["bootstrap_unit"] = "district"
    intervals["bootstrap_replicates"] = int(replicates)
    return intervals


def tune(model, grid, X, y, groups):
    unique = np.unique(groups)
    folds = min(5, len(unique))
    if folds < 3:
        raise ValueError("Need at least three training districts for grouped tuning")
    cv = GroupKFold(n_splits=folds)
    search = GridSearchCV(model, grid, scoring="neg_root_mean_squared_error",
                          cv=cv, n_jobs=1, refit=True, error_score="raise")
    started = time.perf_counter()
    search.fit(X, y, groups=groups)
    search.best_estimator_.research_tuning_report_ = {
        "fit_seconds": time.perf_counter() - started, "inner_folds": folds,
        "best_params": search.best_params_,
        "candidates": [{"params": p, "mean_cv_rmse": float(-mean), "sd_cv_rmse": float(sd)}
                       for p, mean, sd in zip(search.cv_results_["params"],
                                             search.cv_results_["mean_test_score"],
                                             search.cv_results_["std_test_score"])],
    }
    return search.best_estimator_, float(-search.best_score_), len(grid)


def district_holdouts(data: pd.DataFrame, crop: str, features=None, seeds=None) -> tuple[list[dict], list[dict]]:
    """Repeated grouped outer evaluation; all tuning is grouped inside each split."""
    features = FEATURES if features is None else features
    seeds = SEEDS if seeds is None else seeds
    X = data[features].to_numpy(float)
    y = data.yield_q_ha.to_numpy(float)
    groups = data.district_id.astype(str).to_numpy()
    if len(np.unique(groups)) < 12:
        raise ValueError(f"{crop}: need >=12 districts for repeated outer/calibration/grouped-CV splits")
    result, predictions = [], []
    for seed in seeds:
        outer = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)
        fit_cal_idx, test_idx = next(outer.split(X, y, groups))
        X_fitcal, y_fitcal, g_fitcal = X[fit_cal_idx], y[fit_cal_idx], groups[fit_cal_idx]
        inner = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed + 1000)
        fit_idx, cal_idx = next(inner.split(X_fitcal, y_fitcal, g_fitcal))
        X_fit, y_fit, g_fit = X_fitcal[fit_idx], y_fitcal[fit_idx], g_fitcal[fit_idx]
        X_cal, y_cal = X_fitcal[cal_idx], y_fitcal[cal_idx]
        if len(np.unique(g_fit)) < 3 or not len(X_cal):
            raise ValueError(f"{crop}: insufficient district groups after calibration split")
        for name, (estimator, grid) in estimators(seed, features).items():
            print(f"  development seed={seed} model={name}", flush=True)
            if estimator is None:
                pred_cal = np.full(len(y_cal), float(y_fit.mean()))
                pred_test = np.full(len(test_idx), float(y_fit.mean()))
                selected, cv_rmse, candidates = "training_mean", None, 1
            else:
                selected, cv_rmse, candidates = tune(estimator, grid, X_fit, y_fit, g_fit)
                pred_cal = selected.predict(X_cal)
                pred_test = selected.predict(X[test_idx])
            radius = conformal_radius(y_cal, pred_cal)
            metrics = score(y[test_idx], pred_test, radius)
            result.append({"crop": crop, "evaluation": "repeated_district_holdout",
                           "seed": seed, "family": name, "n_train": int(len(y_fit)),
                           "n_calibration": int(len(y_cal)), "n_test": int(len(test_idx)),
                           "n_test_districts": int(len(np.unique(groups[test_idx]))),
                           "tuning_report": json.dumps(getattr(selected, "research_tuning_report_", {}), default=str),
                           "cv_rmse": cv_rmse, "candidate_count": candidates, **metrics})
            for idx, actual, prediction in zip(test_idx, y[test_idx], pred_test):
                predictions.append({"crop": crop, "evaluation": "repeated_district_holdout",
                                    "seed": seed, "family": name,
                                    "district_id": groups[idx], "year": int(data.iloc[idx].year),
                                    "season": str(data.iloc[idx].season),
                                    "row_key": f"{crop}|{data.iloc[idx].season}|{data.iloc[idx].year}|{groups[idx]}",
                                    "actual_q_ha": float(actual), "predicted_q_ha": float(prediction),
                                    "interval_radius_q_ha": radius})
    return result, predictions


def frozen_role_masks(data: pd.DataFrame, crop: str, config: dict) -> dict:
    """Verify every frozen assignment before exposing any development rows."""
    test_years = [int(y) for y in config["test_years"]]
    if len(test_years) < 1:
        raise ValueError(f"{crop}: frozen test-year assignment is empty")
    held_districts = [str(d) for d in config["held_out_district_ids"]]
    development_districts = set(data.district_id.astype(str).unique()) - set(held_districts)
    test_start = min(test_years)
    calibration_year = int(config["calibration_year"])
    role_masks = {
        "fit": data.district_id.astype(str).isin(development_districts) & (data.year.astype(int) < calibration_year),
        "calibration": data.district_id.astype(str).isin(development_districts) & (data.year.astype(int) == calibration_year),
        "reserved_unseen_districts": data.district_id.astype(str).isin(held_districts) & (data.year.astype(int) < test_start),
        "future_years_known_districts": data.district_id.astype(str).isin(development_districts) & data.year.astype(int).isin(test_years),
        "joint_unseen_district_and_future_years": data.district_id.astype(str).isin(held_districts) & data.year.astype(int).isin(test_years),
    }
    keys = (data.crop.astype(str) + "|" + data.season.astype(str) + "|" +
            data.year.astype(str) + "|" + data.district_id.astype(str))
    for role, mask in role_masks.items():
        actual = "\n".join(sorted(keys[mask].tolist())).encode("utf-8")
        digest = hashlib.sha256(actual).hexdigest()
        expected = config["roles"][role]
        if len(keys[mask]) != int(expected["n_rows"]) or digest != expected["row_keys_sha256"]:
            raise ValueError(f"{crop}: {role} rows no longer match frozen lockbox key hash")
    membership = np.stack([mask.to_numpy() for mask in role_masks.values()]).sum(axis=0)
    if not np.all(membership == 1):
        raise ValueError(f"{crop}: frozen roles must partition every row exactly once")
    return role_masks


def development_rows(data: pd.DataFrame, crop: str, config: dict) -> pd.DataFrame:
    masks = frozen_role_masks(data, crop, config)
    return data.loc[masks["fit"]].copy().reset_index(drop=True)


def reserved_lockboxes(data: pd.DataFrame, crop: str, config: dict, features=None) -> tuple[list[dict], list[dict]]:
    """Evaluate reserved cohorts only in the explicitly selected reserved stage."""
    role_masks = frozen_role_masks(data, crop, config)
    features = FEATURES if features is None else features
    test_years = [int(y) for y in config["test_years"]]
    held_districts = [str(d) for d in config["held_out_district_ids"]]
    calibration_year = int(config["calibration_year"])
    fit = data[role_masks["fit"]].copy()
    cal = data[role_masks["calibration"]].copy()
    tests = [(role, data[mask].copy()) for role, mask in role_masks.items()
             if role not in ("fit", "calibration")]
    if fit.district_id.nunique() < 5 or cal.empty or any(frame.empty for _, frame in tests):
        raise ValueError(f"{crop}: frozen protocol has insufficient role data")
    X_fit, y_fit = fit[features].to_numpy(float), fit.yield_q_ha.to_numpy(float)
    X_cal, y_cal = cal[features].to_numpy(float), cal.yield_q_ha.to_numpy(float)
    result, predictions = [], []
    for name, (estimator, grid) in estimators(20260924, features).items():
        if estimator is None:
            pred_cal = np.full(len(y_cal), float(y_fit.mean()))
            selected, cv_rmse, candidates = "training_mean", None, 1
        else:
            selected, cv_rmse, candidates = tune(
                estimator, grid, X_fit, y_fit, fit.district_id.astype(str).to_numpy())
            pred_cal = selected.predict(X_cal)
        radius = conformal_radius(y_cal, pred_cal)
        for test_name, test in tests:
            X_test, y_test = test[features].to_numpy(float), test.yield_q_ha.to_numpy(float)
            pred_test = np.full(len(y_test), float(y_fit.mean())) if estimator is None else selected.predict(X_test)
            metrics = score(y_test, pred_test, radius)
            bootstrap_seed = int(hashlib.sha256(f"{crop}:{name}:{test_name}".encode()).hexdigest()[:8], 16)
            metrics.update(cluster_bootstrap_ci(
                y_test, pred_test, test.district_id.astype(str).to_numpy(), radius,
                seed=bootstrap_seed))
            result.append({"crop": crop, "evaluation": test_name, "family": name,
                           "test_years": test_years if "future" in test_name else "pre_temporal_holdout",
                           "held_out_districts": held_districts,
                           "calibration_year": int(calibration_year), "n_train": int(len(y_fit)),
                           "n_calibration": int(len(y_cal)), "n_test": int(len(y_test)),
                           "n_test_districts": int(test.district_id.nunique()),
                           "tuning_report": json.dumps(getattr(selected, "research_tuning_report_", {}), default=str),
                           "cv_rmse": cv_rmse, "candidate_count": candidates, **metrics})
            for rid, actual, prediction in zip(test.index, y_test, pred_test):
                predictions.append({"crop": crop, "evaluation": test_name,
                                    "family": name, "row_index": int(rid),
                                    "district_id": str(test.loc[rid, "district_id"]),
                                    "year": int(test.loc[rid, "year"]),
                                    "season": str(test.loc[rid, "season"]),
                                    "row_key": f"{crop}|{test.loc[rid, 'season']}|{test.loc[rid, 'year']}|{test.loc[rid, 'district_id']}",
                                    "actual_q_ha": float(actual), "predicted_q_ha": float(prediction),
                                    "interval_radius_q_ha": radius})
    return result, predictions


def summarize(repeated: pd.DataFrame) -> list[dict]:
    rows = []
    for (crop, family), group in repeated.groupby(["crop", "family"]):
        row = {"crop": crop, "family": family, "split_count": int(len(group))}
        for metric in METRICS:
            row[f"{metric}_mean"] = float(group[metric].mean())
            row[f"{metric}_sd_across_splits"] = float(group[metric].std(ddof=1))
        rows.append(row)
    return rows


def paired_deltas(predictions: pd.DataFrame, replicates: int = 1000) -> tuple[pd.DataFrame, pd.DataFrame]:
    comparisons = [("quantum_simulated_entangled", family) for family in sorted(predictions.family.unique())
                   if family.startswith("classical_") or family == "year_trend_baseline"] + [
        ("quantum_no_entanglement", "quantum_simulated_entangled"),
        ("quantum_one_layer", "quantum_simulated_entangled"),
        ("quantum_uncentered_kernel", "quantum_simulated_entangled"),
    ]
    split_rows = []
    group_cols = ["crop", "evaluation", "seed"] if "seed" in predictions else ["crop", "evaluation"]
    for keys, chunk in predictions.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        identity = dict(zip(group_cols, keys))
        for left_family, right_family in comparisons:
            left = chunk[chunk.family == left_family]
            right = chunk[chunk.family == right_family]
            joined = left.merge(right, on=["row_key", "district_id", "year", "season"],
                                suffixes=("_q", "_c"), validate="one_to_one")
            if joined.empty:
                continue
            if len(joined) != len(left) or len(joined) != len(right):
                raise ValueError("Paired comparisons require identical complete row sets")
            if not np.array_equal(joined.actual_q_ha_q, joined.actual_q_ha_c):
                raise ValueError("Paired comparisons disagree on the actual target")
            actual = joined.actual_q_ha_q.to_numpy(float)
            pred_left = joined.predicted_q_ha_q.to_numpy(float)
            pred_right = joined.predicted_q_ha_c.to_numpy(float)
            groups = joined.district_id.astype(str).to_numpy()
            ae_left, ae_right = np.abs(actual - pred_left), np.abs(actual - pred_right)
            mae_delta = float(ae_left.mean() - ae_right.mean())
            rmse_delta = float(np.sqrt(np.mean((actual - pred_left) ** 2)) -
                               np.sqrt(np.mean((actual - pred_right) ** 2)))
            rng_seed = int(hashlib.sha256(
                f"{identity}:{left_family}:{right_family}".encode()).hexdigest()[:8], 16)
            rng = np.random.default_rng(rng_seed)
            unique = np.unique(groups)
            group_idx = {group: np.flatnonzero(groups == group) for group in unique}
            boot_mae, boot_rmse = [], []
            for _ in range(replicates):
                sample_groups = rng.choice(unique, size=len(unique), replace=True)
                sample = np.concatenate([group_idx[group] for group in sample_groups])
                boot_mae.append(float(ae_left[sample].mean() - ae_right[sample].mean()))
                lrmse = np.sqrt(np.mean((actual[sample] - pred_left[sample]) ** 2))
                rrmse = np.sqrt(np.mean((actual[sample] - pred_right[sample]) ** 2))
                boot_rmse.append(float(lrmse - rrmse))
            mlo, mhi = np.quantile(boot_mae, [0.025, 0.975])
            rlo, rhi = np.quantile(boot_rmse, [0.025, 0.975])
            split_rows.append({**identity, "comparison": f"{left_family} minus {right_family}",
                               "n_paired_rows": int(len(joined)), "n_districts": int(len(unique)),
                               "mae_delta_q_ha": mae_delta, "mae_delta_ci95_low": float(mlo),
                               "mae_delta_ci95_high": float(mhi), "rmse_delta_q_ha": rmse_delta,
                               "rmse_delta_ci95_low": float(rlo), "rmse_delta_ci95_high": float(rhi),
                               "bootstrap_unit": "district", "bootstrap_replicates": replicates})
    splits = pd.DataFrame(split_rows)
    if splits.empty:
        return splits, splits
    summaries = []
    for keys, group in splits.groupby(["crop", "evaluation", "comparison"], dropna=False):
        crop, evaluation, comparison = keys
        summaries.append({"crop": crop, "evaluation": evaluation, "comparison": comparison,
                          "split_count": int(len(group)),
                          "mae_delta_mean_q_ha": float(group.mae_delta_q_ha.mean()),
                          "mae_delta_sd_across_splits": float(group.mae_delta_q_ha.std(ddof=1)),
                          "rmse_delta_mean_q_ha": float(group.rmse_delta_q_ha.mean()),
                          "rmse_delta_sd_across_splits": float(group.rmse_delta_q_ha.std(ddof=1))})
    return splits, pd.DataFrame(summaries)


def run(panel_path: Path, lockbox_path: Path, output: Path, n_test_years: int = 3,
        stage: str = "development", seeds=None) -> Path:
    seeds = SEEDS if seeds is None else seeds
    if stage not in {"development", "reserved"}:
        raise ValueError("Stage must be development or reserved")
    panel_path = panel_path.resolve()
    lockbox_path = lockbox_path.resolve()
    if not lockbox_path.exists():
        raise FileNotFoundError("Freeze and review the protocol lockbox before scoring")
    source_manifest_path = panel_path.parent / "manifest.json"
    if not source_manifest_path.exists():
        raise FileNotFoundError("Prepared panel manifest is required; synthetic app data are not accepted")
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    if source_manifest.get("status") != "prepared_real_source_inputs_not_yet_independently_validated":
        raise ValueError("Panel provenance status is not the real-source preparation workflow")
    features = source_manifest.get("features", FEATURES)
    if len(features) != 8 or len(set(features)) != 8:
        raise ValueError("This exact four-qubit encoding requires eight distinct declared features")
    forbidden = {"yield_q_ha", "reported_yield_q_ha", "production_tonnes", "area_ha", "ratio_yield_kg_ha_diagnostic"}
    if forbidden.intersection(features):
        raise ValueError("Target or yield-defining inputs cannot be predictors")
    data = pd.read_csv(panel_path, dtype={"district_id": str})
    missing = {"district_id", "year", "crop", "season", "yield_q_ha", *features} - set(data.columns)
    if missing:
        raise ValueError(f"Panel missing columns: {sorted(missing)}")
    if data[["district_id", "crop", "season", "year"]].isna().any().any():
        raise ValueError("Split identifiers must not be missing")
    years = pd.to_numeric(data.year, errors="raise")
    if not np.isfinite(years).all() or (years != np.floor(years)).any():
        raise ValueError("Year values must be finite integers")
    data["year"] = years.astype(int)
    if data.duplicated(["district_id", "year", "crop", "season"]).any():
        raise ValueError("Duplicate district-year-crop-season rows; fix the boundary/season join first")
    values = data[features + ["yield_q_ha"]].to_numpy(float)
    if not np.isfinite(values).all() or (data.yield_q_ha <= 0).any():
        raise ValueError("Panel contains missing/nonfinite features or nonpositive yield")
    if source_manifest.get("panel_sha256") != sha256(panel_path):
        raise ValueError("Prepared panel hash differs from its provenance manifest")
    lockbox = json.loads(lockbox_path.read_text(encoding="utf-8"))
    if lockbox.get("panel_sha256") != sha256(panel_path):
        raise ValueError("Panel hash differs from the frozen split manifest")
    if set(lockbox.get("crops", {})) != set(data.crop.astype(str).unique()):
        raise ValueError("Frozen crop assignments differ from panel crops")
    if stage == "reserved":
        expected_code = lockbox.get("evaluation_code_sha256", {})
        for path in [Path(__file__), ROOT.parent / "backend/models/validated_yield.py"]:
            if expected_code.get(path.name) != sha256(path):
                raise ValueError("Reserved evaluation requires code hashes frozen with the protocol")
    for crop, assignment in lockbox.get("crops", {}).items():
        if len(assignment.get("test_years", [])) != n_test_years:
            raise ValueError(f"{crop}: frozen temporal window differs from --test-years")
    output.mkdir(parents=True, exist_ok=False)
    if stage == "reserved":
        # Exclusive receipt prevents accidental rescoring into a different output directory.
        receipt = lockbox_path.with_name(lockbox_path.name + ".reserved_started.json")
        with receipt.open("x", encoding="utf-8") as handle:
            json.dump({"started_utc": datetime.now(timezone.utc).isoformat(),
                       "output": str(output.resolve()), "lockbox_sha256": sha256(lockbox_path)}, handle)
    all_scores, all_predictions, errors, lockboxes = [], [], [], {}
    for crop in sorted(data.crop.astype(str).unique()):
        sub = data[data.crop.astype(str) == crop].reset_index(drop=True)
        print(f"{crop}: rows={len(sub)}, districts={sub.district_id.nunique()}, years={sub.year.nunique()}", flush=True)
        stages = [("district", district_holdouts)] if stage == "development" else [("reserved_lockboxes", None)]
        for evaluation_stage, fn in stages:
            try:
                if fn:
                    scores, preds = fn(development_rows(sub, crop, lockbox["crops"][crop]), crop, features, seeds)
                else:
                    if crop not in lockbox.get("crops", {}):
                        raise ValueError(f"{crop}: no frozen split assignment")
                    scores, preds = reserved_lockboxes(sub, crop, lockbox["crops"][crop], features)
                    lockboxes[crop] = lockbox["crops"][crop]["held_out_district_ids"]
                all_scores.extend(scores)
                all_predictions.extend(preds)
            except Exception as exc:
                if evaluation_stage == "reserved_lockboxes":
                    raise
                errors.append({"crop": crop, "stage": evaluation_stage, "error": str(exc)})
                print(f"  {evaluation_stage} skipped: {exc}", flush=True)
    if not all_scores:
        raise RuntimeError("No evaluations completed; inspect diagnostics and source panel")
    scores = pd.DataFrame(all_scores)
    tuning_records = [{"crop": r["crop"], "family": r["family"], "evaluation": r["evaluation"],
                       "seed": r.get("seed"), "search": json.loads(r.get("tuning_report", "{}"))}
                      for r in all_scores]
    (output / "tuning_results.json").write_text(json.dumps(tuning_records, indent=2), encoding="utf-8")
    scores = scores.drop(columns=["tuning_report"], errors="ignore")
    scores.to_csv(output / "split_metrics.csv", index=False)
    pd.DataFrame(summarize(scores[scores.evaluation == "repeated_district_holdout"])).to_csv(
        output / "district_summary.csv", index=False)
    pd.DataFrame(all_predictions).to_csv(output / "predictions.csv", index=False)
    split_deltas, delta_summary = paired_deltas(pd.DataFrame(all_predictions))
    split_deltas.to_csv(output / "paired_split_deltas.csv", index=False)
    delta_summary.to_csv(output / "paired_delta_summary.csv", index=False)
    report = {
        "status": "exploratory_candidate_run_not_publication_result",
        "evaluation_stage": stage,
        "reserved_outcomes_scored": stage == "reserved",
        "evaluation_code_sha256": {p.name: sha256(p) for p in
                                    [Path(__file__), ROOT.parent / "backend/models/validated_yield.py"]},
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "panel": str(panel_path), "panel_sha256": sha256(panel_path),
        "source_manifest": str(source_manifest_path),
        "raw_source_sha256": source_manifest.get("raw_sha256", {}),
        "source_metadata_sha256": source_manifest.get("source_metadata_sha256"),
        "source_cache_sha256": source_manifest.get("source_cache_sha256", {}),
        "yield_derivation": source_manifest.get("yield_derivation"),
        "lockbox": str(lockbox_path), "lockbox_sha256": sha256(lockbox_path),
        "python": sys.version, "scikit_learn": sklearn.__version__,
        "features": features, "yield_unit": "quintals_per_hectare",
        "n_classical_tuning_candidates": N_CANDIDATES,
        "n_quantum_tuning_candidates": N_CANDIDATES,
        "quantum_description": "Exact four-qubit fidelity kernel simulated on a classical statevector; no hardware quantum advantage claim",
        "district_repeats": seeds,
        "temporal_test_year_count": n_test_years,
        "reserved_districts_by_crop": lockboxes,
        "errors_or_skipped_crops": errors,
        "limitations": source_manifest.get("limitations", []) + ["District aggregate ecological prediction", "Full-season weather means post-season estimation",
                        "NASA POWER centroid weather is a gridded proxy", "SoilGrids values are static model estimates",
                        "No farm-level management, irrigation, cultivar, or technology trend variables",
                        "Derived production-to-area outcomes may differ from source-reported yield rates",
                        "Temporal lockbox is only pristine if not previously inspected",
                        "Repeated district holdouts overlap and are not independent samples"],
    }
    (output / "run_manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"completed_rows": len(scores), "errors": errors,
                      "output": str(output.resolve())}, indent=2), flush=True)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--lockbox", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--test-years", type=int, default=3)
    parser.add_argument("--stage", choices=["development", "reserved"], default="development",
                        help="Development uses frozen fit rows only. Reserved consumes the final evaluation once.")
    parser.add_argument("--seeds", type=int, nargs="+", default=SEEDS,
                        help="Development split seeds; subsets are pilot checks, not the full repeated study")
    args = parser.parse_args()
    run(args.panel, args.lockbox, args.output, args.test_years, args.stage, args.seeds)
