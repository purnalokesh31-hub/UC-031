"""Prepare annual DLD staging records; deliberately not a model-ready panel.

Preserves source bytes, retains reported yields, logs all crop exclusions, and
keeps weather in source-year/month form until spatial/time alignment is reviewed.
"""
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

STATES = {"Andhra Pradesh", "Telangana"}
CROPS = {
    "RICE": "rice",
    "WHEAT": "wheat",
    "MAIZE": "maize",
    "COTTON": "cotton_lint_documented_in_apportioned_manual",
    "SUGARCANE": "raw_sugar_gur_documented_in_apportioned_manual",
    "GROUNDNUT": "groundnut",
}
WEATHER = {
    "Precipitation": ("precip_mm", "PERCIPITATION (Millimeters)"),
    "Temperature Maximum": ("tmax_c", "MAXIMUM (Centigrate)"),
    "Temperature Minimum": ("tmin_c", "MINIMUM (Centigrate)"),
    "Evapotranspiration": ("aet_mm", "ACTUAL (Millimeters)"),
}
MONTHS = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
          "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def crop_values(row, crop):
    names = [f"{crop} AREA (1000 ha)", f"{crop} PRODUCTION (1000 tons)", f"{crop} YIELD (Kg per ha)"]
    values = [number(row[name]) for name in names]
    reasons = []
    for label, value in zip(["area", "production", "yield"], values):
        if value is None:
            reasons.append(f"{label}_missing_or_nonfinite")
        elif value == -1:
            reasons.append(f"{label}_source_missing_code_minus_one")
        elif value < 0:
            reasons.append(f"{label}_invalid_negative")
        elif value == 0:
            reasons.append(f"{label}_zero")
    if reasons:
        return None, reasons
    area, production, reported_yield = values
    return {"area_ha": area * 1000, "production_tonnes": production * 1000,
            "reported_yield_kg_ha": reported_yield, "reported_yield_q_ha": reported_yield / 100,
            # Diagnostic only: never used to overwrite the reported target.
            "ratio_yield_kg_ha_diagnostic": production / area * 1000,
            "ratio_relative_difference": abs(production / area * 1000 - reported_yield) / reported_yield}, []


def write_csv(path, rows, fields):
    with path.open("x", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def unique(rows, fields, label):
    keys = [tuple(r[f] for f in fields) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError(f"Duplicate {label} keys")


def prepare(archive, raw_output, output):
    if raw_output.exists() or output.exists():
        raise FileExistsError("Use new output directories; original artifacts are preserved")
    raw_output.mkdir(parents=True)
    output.mkdir(parents=True)
    hashes = {}
    records, exclusions, weather_rows = [], [], []
    scoped_source_rows = {}
    with zipfile.ZipFile(archive) as z:
        def member(suffix):
            matches = [n for n in z.namelist() if n.endswith(suffix)]
            if len(matches) != 1:
                raise ValueError(f"Expected one archive member for {suffix}")
            name = matches[0]
            blob = z.read(name)
            relative = suffix.removeprefix("/raw/DLD/").removeprefix("/")
            destination = raw_output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(blob)
            hashes[relative] = {"archive_member": name, "sha256": hashlib.sha256(blob).hexdigest()}
            return blob

        for variant in ["Apportioned", "Unapportioned"]:
            rows = list(csv.DictReader(io.StringIO(member(f"/raw/DLD/{variant}/Crops_Area Production Yield.csv").decode("utf-8-sig"))))
            unique(rows, ["Dist Code", "Year"], variant)
            scoped = [r for r in rows if r["State Name"] in STATES]
            scoped_source_rows[variant] = len(scoped)
            for row in scoped:
                for crop, basis in CROPS.items():
                    identity = {"variant": variant, "source_district_id": row["Dist Code"],
                                "source_state": row["State Name"], "source_district": row["Dist Name"],
                                "source_year": int(row["Year"]), "crop": crop.title()}
                    values, reasons = crop_values(row, crop)
                    if reasons:
                        exclusions.append({**identity, "reasons": ";".join(reasons)})
                        continue
                    records.append({**identity, **values, "product_basis": basis,
                                    "time_grain": "annual", "target_origin": "source_reported_yield",
                                    "boundary_review_required": True,
                                    "agricultural_year_alignment_review_required": True})

        # Outer merge at monthly grain exposes missing sources instead of dropping them.
        monthly = {}
        for source, (variable, suffix) in WEATHER.items():
            rows = list(csv.DictReader(io.StringIO(member(f"/raw/DLD/Unapportioned/Environment_{source}.csv").decode("utf-8-sig"))))
            unique(rows, ["Dist Code", "Year"], source)
            for row in rows:
                if row["State Name"] not in STATES:
                    continue
                for month, label in enumerate(MONTHS, 1):
                    key = (row["Dist Code"], int(row["Year"]), month)
                    identity = {"source_district_id": key[0], "source_year": key[1], "month": month,
                                "source_state": row["State Name"], "source_district": row["Dist Name"]}
                    if key not in monthly:
                        monthly[key] = {**identity, **{v[0]: None for v in WEATHER.values()}}
                    if any(monthly[key][f] != v for f, v in identity.items()):
                        raise ValueError(f"Conflicting weather identifiers at {key}")
                    value = number(row[f"{label} {suffix}"])
                    # Negative temperatures are retained; do not globally replace -1.
                    monthly[key][variable] = value
        for key in sorted(monthly):
            row = monthly[key]
            flags = []
            for variable, _ in WEATHER.values():
                value = row[variable]
                if value is None:
                    flags.append(f"{variable}_missing_or_nonfinite")
                elif variable in {"precip_mm", "aet_mm"} and value < 0:
                    flags.append(f"{variable}_negative")
            if row["tmax_c"] is not None and row["tmin_c"] is not None and row["tmax_c"] < row["tmin_c"]:
                flags.append("tmax_below_tmin")
            weather_rows.append({**row, "quality_flags": ";".join(flags)})
        member("/raw/DLD/DLD-Apportioned-Data-Documentation.pdf")
        member("/raw/DLD/Apportionment.xlsx")
        member("/README.pdf")

    crop_fields = ["variant", "source_district_id", "source_state", "source_district", "source_year", "crop"]
    unique(records, ["variant", "source_district_id", "source_year", "crop"], "staged crop")
    write_csv(output / "annual_crop_records.csv", records, list(records[0]))
    write_csv(output / "crop_exclusions.csv", exclusions, crop_fields + ["reasons"])
    write_csv(output / "monthly_weather_records.csv", weather_rows, list(weather_rows[0]))
    counts = Counter((r["variant"], r["crop"]) for r in records)
    reason_counts = Counter(reason for r in exclusions for reason in r["reasons"].split(";"))
    with archive.open("rb") as f:
        archive_hash = hashlib.file_digest(f, "sha256").hexdigest()
    manifest = {
        "status": "staging_only_boundary_and_time_alignment_unresolved",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "archive_path": str(archive.resolve()), "archive_sha256": archive_hash,
        "preparation_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_catalogue": "https://reproducibility.worldbank.org/index.php/catalog/409",
        "raw_output": str(raw_output.resolve()), "sources": hashes,
        "scope": sorted(STATES), "scoped_source_rows": scoped_source_rows,
        "candidate_crop_rows": sum(scoped_source_rows.values()) * len(CROPS),
        "retained_crop_rows": len(records), "excluded_crop_rows": len(exclusions),
        "crop_rows": [{"variant": k[0], "crop": k[1], "rows": v} for k, v in sorted(counts.items())],
        "exclusion_reasons_nonexclusive": dict(reason_counts),
        "weather_rows": len(weather_rows), "weather_rows_flagged": sum(bool(r["quality_flags"]) for r in weather_rows),
        "ratio_discrepancy_over_5pct_rows_for_review": sum(r["ratio_relative_difference"] > .05 for r in records),
        "conversions": {"area": "1000 ha times 1000", "production": "1000 tons times 1000",
                        "yield": "source kg/ha divided by 100 to q/ha; never overwritten by the ratio"},
        "notes": [
            "Versions remain separate; apportioned and unapportioned records are not independent observations.",
            "No synthetic seasons, soil values, humidity, or daily temperature extremes have been invented.",
            "No weather-to-crop join or model evaluation is performed in this staging workflow.",
            "Source-year labels retained: do not infer calendar alignment from identical numeric years.",
            "Apportioned manual describes lint and gur targets; verify consistency in the newer unapportioned export.",
            "Negative temperatures retained; missing code -1 is applied only to crop fields.",
            "Production/area fields are audit metadata and must never be yield-model predictors.",
        ],
    }
    assert manifest["candidate_crop_rows"] == len(records) + len(exclusions)
    manifest["output_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob("*.csv")}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ["status", "candidate_crop_rows", "retained_crop_rows",
          "excluded_crop_rows", "weather_rows", "weather_rows_flagged", "ratio_discrepancy_over_5pct_rows_for_review"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--raw-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.archive, args.raw_output, args.output)
