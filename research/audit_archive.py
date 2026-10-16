"""Inventory user-supplied DLD source files without fitting models or changing data."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

CROPS = ["RICE", "WHEAT", "MAIZE", "COTTON", "SUGARCANE", "GROUNDNUT"]
STATES = {"Andhra Pradesh", "Telangana"}


def number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


def digest_file(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def audit(archive: Path, output: Path):
    output.mkdir(parents=True, exist_ok=False)
    inventory, tables = {}, {}
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            if "/raw/DLD/" not in name or not name.endswith(".csv"):
                continue
            if not any(token in name for token in ["Crops_", "Environment_"]):
                continue
            raw = z.read(name)
            rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
            label = name.split("/raw/DLD/")[1]
            tables[label] = rows
            columns = list(rows[0])
            years = [int(r["Year"]) for r in rows]
            keys = [(r["Dist Code"], r["Year"]) for r in rows]
            values = [number(r[c]) for r in rows for c in columns[5:]]
            scope = [r for r in rows if r["State Name"] in STATES]
            inventory[label] = {
                "archive_member": name, "member_sha256": hashlib.sha256(raw).hexdigest(),
                "rows": len(rows), "columns": columns, "year_range": [min(years), max(years)],
                "districts": len({r["Dist Code"] for r in rows}),
                "duplicate_district_years": len(keys) - len(set(keys)),
                "missing_or_nonfinite_numeric_cells": sum(v is None for v in values),
                "negative_numeric_cells": sum(v is not None and v < 0 for v in values),
                "negative_values_note": "Negative temperature is physically valid; negative crop area/production/yield needs exclusion and documentation.",
                "ap_ts_rows": len(scope), "ap_ts_districts": len({r["Dist Code"] for r in scope}),
            }
    weather = {label: {(r["Dist Code"], r["Year"]): r for r in rows}
               for label, rows in tables.items() if "Environment_" in label}
    crop_audits = {}
    for label, rows in tables.items():
        if "Crops_" not in label:
            continue
        crop_audits[label] = {}
        for scope_name, scoped in [("all", rows), ("ap_ts", [r for r in rows if r["State Name"] in STATES])]:
            items = {}
            for crop in CROPS:
                cols = [f"{crop} AREA (1000 ha)", f"{crop} PRODUCTION (1000 tons)", f"{crop} YIELD (Kg per ha)"]
                valid = [r for r in scoped if all(number(r[c]) is not None and number(r[c]) > 0 for c in cols)]
                joined = [r for r in valid if all((r["Dist Code"], r["Year"]) in w for w in weather.values())]
                names_match = sum(all(
                    w[(r["Dist Code"], r["Year"])]["Dist Name"] == r["Dist Name"] and
                    w[(r["Dist Code"], r["Year"])]["State Name"] == r["State Name"]
                    for w in weather.values()) for r in joined)
                items[crop] = {"positive_area_production_yield_rows": len(valid),
                               "excluded_nonpositive_or_missing_rows": len(scoped)-len(valid),
                               "districts": len({r["Dist Code"] for r in valid}),
                               "rows_by_year": dict(sorted(Counter(r["Year"] for r in valid).items())),
                               "matching_keys_in_all_four_weather_files": len(joined),
                               "matching_weather_keys_and_names": names_match}
            crop_audits[label][scope_name] = items
    report = {
        "status": "source_inventory_only_not_a_training_panel",
        "audited_utc": datetime.now(timezone.utc).isoformat(),
        "archive_path": str(archive.resolve()), "archive_sha256": digest_file(archive),
        "catalogue_url": "https://reproducibility.worldbank.org/index.php/catalog/409",
        "source": "User-supplied World Bank reproducibility archive containing ICRISAT-TCI DLD data",
        "files": inventory, "crop_eligibility": crop_audits,
        "limitations": [
            "No seasons provided for the six selected crops. Do not manufacture season labels from annual records.",
            "Matching district IDs and names does not establish matching historical boundaries.",
            "Weather monthly dates must be aligned to the documented agricultural-year convention.",
            "Negative crop entries (including -1) require documented missing-value interpretation.",
            "No soil measurements or independent external test set identified by this CSV inventory.",
            "Do not use same-year production and area as predictors of the corresponding yield.",
            "No model fitting, tuning, or evaluation performed.",
        ],
    }
    (output / "source_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["# Source data audit", "", "No models were trained or evaluated in this audit.", "",
             "| Dataset | Rows | Districts | Years |", "|---|---:|---:|---|"]
    for label, info in inventory.items():
        lines.append(f"| {label} | {info['rows']:,} | {info['districts']} | {info['year_range'][0]}–{info['year_range'][1]} |")
    lines += ["", "## Andhra Pradesh and Telangana: unapportioned crop records", "",
              "Counts require positive area, production and reported yield; they are provisional eligibility counts.", "",
              "| Crop | Eligible rows | Districts | Matching keys in four weather files |", "|---|---:|---:|---:|"]
    for crop, info in crop_audits["Unapportioned/Crops_Area Production Yield.csv"]["ap_ts"].items():
        lines.append(f"| {crop.title()} | {info['positive_area_production_yield_rows']} | {info['districts']} | {info['matching_keys_in_all_four_weather_files']} |")
    lines += ["", "## Required investigation", ""] + ["- " + item for item in report["limitations"]]
    lines += ["", "The apportioned crop table and unapportioned weather table must not be joined merely because codes match. Review the archive's apportionment workbook and documentation first.", "",
              "Archive and member SHA-256 checksums, schemas and per-crop year counts are recorded in source_audit.json. Original files remain unchanged."]
    (output / "SOURCE_AUDIT.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps({"output": str(output.resolve()), "files_audited": len(inventory)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit(args.archive, args.output)
