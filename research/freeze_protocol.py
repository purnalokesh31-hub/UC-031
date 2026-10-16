"""Freeze label-blind district/time split keys before scoring any model."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_keys(values) -> str:
    packed = "\n".join(sorted(map(str, values))).encode("utf-8")
    return hashlib.sha256(packed).hexdigest()


def row_key(frame: pd.DataFrame) -> pd.Series:
    return (frame.crop.astype(str) + "|" + frame.season.astype(str) + "|" +
            frame.year.astype(str) + "|" + frame.district_id.astype(str))


def freeze(panel_path: Path, output: Path, n_test_years: int = 3) -> Path:
    if output.exists():
        raise FileExistsError("Preserve the existing frozen protocol; refusing to overwrite it")
    if n_test_years < 1:
        raise ValueError("At least one test year is required")
    panel_path = panel_path.resolve()
    data = pd.read_csv(panel_path, dtype={"district_id": str})
    required = {"district_id", "year", "crop", "season", "yield_q_ha"}
    if required - set(data.columns):
        raise ValueError(f"Panel missing split-key fields: {sorted(required - set(data.columns))}")
    if data[["district_id", "year", "crop", "season"]].isna().any().any():
        raise ValueError("Cannot freeze missing split identifiers")
    numeric_year = pd.to_numeric(data.year, errors="raise")
    if (numeric_year % 1 != 0).any():
        raise ValueError("Year values must be finite integers")
    if data.duplicated(["district_id", "year", "crop", "season"]).any():
        raise ValueError("Cannot freeze duplicate row keys")
    data["year"] = data.year.astype(int)
    data["_row_key"] = row_key(data)
    if data._row_key.duplicated().any():
        raise ValueError("Constructed row keys are not unique")
    crops = {}
    for crop in sorted(data.crop.astype(str).unique()):
        sub = data[data.crop.astype(str) == crop].copy()
        years = sorted(sub.year.unique().tolist())
        if len(years) < n_test_years + 4:
            raise ValueError(f"{crop}: not enough crop years to freeze spatial and temporal tests")
        district_ids = sorted(sub.district_id.astype(str).unique(),
                              key=lambda value: hashlib.sha256(value.encode()).hexdigest())
        n_holdout = max(1, int(len(district_ids) * 0.2 + 0.999999))
        if len(district_ids) - n_holdout < 5 or n_holdout < 3:
            raise ValueError(f"{crop}: need at least 15 districts to reserve a 20% district test")
        held = district_ids[:n_holdout]
        dev = set(district_ids[n_holdout:])
        test_years = years[-n_test_years:]
        cal_year = max(y for y in years if y not in test_years)
        cutoff = min(test_years)
        roles = {
            "fit": sub.district_id.astype(str).isin(dev) & (sub.year < cal_year),
            "calibration": sub.district_id.astype(str).isin(dev) & (sub.year == cal_year),
            "reserved_unseen_districts": sub.district_id.astype(str).isin(held) & (sub.year < cutoff),
            "future_years_known_districts": sub.district_id.astype(str).isin(dev) & sub.year.isin(test_years),
            "joint_unseen_district_and_future_years": sub.district_id.astype(str).isin(held) & sub.year.isin(test_years),
        }
        assigned = pd.Series(False, index=sub.index)
        counts = {}
        for role, mask in roles.items():
            if (assigned & mask).any():
                raise ValueError(f"{crop}: split roles overlap")
            assigned |= mask
            keys = sub.loc[mask, "_row_key"].tolist()
            counts[role] = {"n_rows": len(keys), "n_districts": int(sub.loc[mask, "district_id"].nunique()),
                            "row_keys_sha256": digest_keys(keys)}
        if not assigned.all():
            raise ValueError(f"{crop}: some rows are not assigned to a frozen split role")
        if any(counts[role]["n_rows"] == 0 for role in roles):
            raise ValueError(f"{crop}: at least one frozen role has no rows")
        crops[crop] = {"held_out_district_ids": held, "development_district_count": len(dev),
                       "test_years": test_years, "calibration_year": int(cal_year),
                       "roles": counts}
    manifest = {
        "protocol_version": "1.1",
        "status": "split_frozen_before_benchmark_scoring",
        "frozen_utc": datetime.now(timezone.utc).isoformat(),
        "panel_path_at_freeze": str(panel_path), "panel_sha256": sha256_file(panel_path),
        "evaluation_code_sha256": {p.name: sha256_file(p) for p in [
            Path(__file__).with_name("benchmark.py"),
            Path(__file__).resolve().parent.parent / "backend/models/validated_yield.py"]},
        "row_key_definition": "crop|season|year|district_id",
        "district_selection": "20% of canonical district IDs sorted by SHA-256 ID hash; outcome-blind",
        "temporal_selection": f"latest {n_test_years} complete years per crop among development districts",
        "crops": crops,
        "warning": "Same-source spatial/temporal holdouts; not an independent-source validation dataset.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    print(json.dumps({"manifest": str(output.resolve()), "panel_sha256": manifest["panel_sha256"],
                      "crops": {c: {"test_years": v["test_years"],
                                    "held_out_district_count": len(v["held_out_district_ids"]),
                                    "roles": v["roles"]} for c, v in crops.items()}}, indent=2))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--test-years", type=int, default=3)
    args = parser.parse_args()
    freeze(args.panel, args.output, args.test_years)
