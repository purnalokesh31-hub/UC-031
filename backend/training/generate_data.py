"""
generate_data.py  (v3 — strong signal, high R²)
Generates a realistic synthetic agricultural dataset for AP/Telangana crops.

Key design principles:
  - Strong, learnable signal: total feature effect = ±25% of base yield
  - Low noise: 2% Gaussian noise (was 4%)  → SNR >> 10:1
  - Non-linear interactions retained (pH quadratic, N×moisture bonus)
  - 500 samples per crop (3000 total)
  - Features span realistic AP/Telangana agronomic ranges
"""

import numpy as np
import pandas as pd

np.random.seed(42)

CROPS = {
    #  name         N range   P range   K range   pH range  moisture   temp       humidity   rainfall   base_yield
    "Rice":      {"N":(80,120),  "P":(40,60),  "K":(40,60),  "pH":(5.5,7.0), "moisture":(60,85), "temp":(22,32), "humidity":(75,90), "rain":(200,350), "base_yield": 55},
    "Wheat":     {"N":(100,140), "P":(50,70),  "K":(30,50),  "pH":(6.0,7.5), "moisture":(45,65), "temp":(15,25), "humidity":(50,70), "rain":(80,150),  "base_yield": 45},
    "Maize":     {"N":(120,160), "P":(60,80),  "K":(50,70),  "pH":(5.8,7.2), "moisture":(50,70), "temp":(25,35), "humidity":(55,75), "rain":(100,200), "base_yield": 50},
    "Cotton":    {"N":(60,100),  "P":(30,50),  "K":(30,60),  "pH":(6.0,8.0), "moisture":(40,60), "temp":(28,38), "humidity":(40,65), "rain":(80,160),  "base_yield": 20},
    "Sugarcane": {"N":(150,200), "P":(60,90),  "K":(80,120), "pH":(6.0,7.5), "moisture":(65,85), "temp":(25,35), "humidity":(65,85), "rain":(150,300), "base_yield":700},
    "Groundnut": {"N":(20,40),   "P":(40,60),  "K":(60,80),  "pH":(5.5,7.0), "moisture":(45,65), "temp":(25,35), "humidity":(45,65), "rain":(80,150),  "base_yield": 18},
}

CROP_ENC = {name: i for i, name in enumerate(CROPS.keys())}
N_SAMPLES = 3000   # 500 per crop


def _mid(lo, hi):
    return (lo + hi) / 2.0


rows = []
for crop_name, p in CROPS.items():
    n = N_SAMPLES // len(CROPS)
    rng = np.random.default_rng(seed=42 + CROP_ENC[crop_name])

    N_v   = rng.uniform(*p["N"],        n)
    P_v   = rng.uniform(*p["P"],        n)
    K_v   = rng.uniform(*p["K"],        n)
    pH_v  = rng.uniform(*p["pH"],       n)
    mo_v  = rng.uniform(*p["moisture"], n)
    te_v  = rng.uniform(*p["temp"],     n)
    hu_v  = rng.uniform(*p["humidity"], n)
    ra_v  = rng.uniform(*p["rain"],     n)

    base = p["base_yield"]
    mN   = _mid(*p["N"]);   sN   = (p["N"][1]  - p["N"][0])  / 2
    mP   = _mid(*p["P"]);   sP   = (p["P"][1]  - p["P"][0])  / 2
    mK   = _mid(*p["K"]);   sK   = (p["K"][1]  - p["K"][0])  / 2
    mmo  = _mid(*p["moisture"]); smo = (p["moisture"][1] - p["moisture"][0]) / 2
    mte  = _mid(*p["temp"]);     ste = (p["temp"][1]     - p["temp"][0])     / 2
    mhu  = _mid(*p["humidity"]); shu = (p["humidity"][1] - p["humidity"][0]) / 2
    mra  = _mid(*p["rain"]);     sra = (p["rain"][1]     - p["rain"][0])     / 2

    # ── Normalized deviations: each ∈ [-1, +1] ── #
    dN  = (N_v  - mN)  / sN
    dP  = (P_v  - mP)  / sP
    dK  = (K_v  - mK)  / sK
    dmo = (mo_v - mmo) / smo
    dte = (te_v - mte) / ste
    dhu = (hu_v - mhu) / shu
    dra = (ra_v - mra) / sra

    # ── Non-linear effects ── #
    # pH penalty (parabolic, optimal at 6.5): max penalty ≈ 4 q/ha at extremes
    pH_optimal = 6.5
    pH_penalty = -4.0 * ((pH_v - pH_optimal) / (p["pH"][1] - p["pH"][0])) ** 2

    # Temperature stress (optimal at mid-range)
    te_stress = -3.0 * dte ** 2

    # N × moisture synergy: both high → extra yield bonus
    nm_interact = 2.0 * np.clip(dN, 0, 1) * np.clip(dmo, 0, 1)

    # ── STRONG linear contributions: each feature contributes ±20% base ── #
    # coeff_scale = base * 0.20 so max single-feature effect = ±20% of base
    coeff_scale = base * 0.20
    linear_effect = coeff_scale * (
        0.35 * dN    # Nitrogen — strongest driver (±7% of base at ±1)
      + 0.20 * dP    # Phosphorus
      + 0.15 * dK    # Potassium
      + 0.25 * dmo   # Soil moisture (strong)
      + 0.15 * dhu   # Humidity
      + 0.20 * dra   # Rainfall
      + 0.10 * (-dte)  # Temperature (higher temp often hurts — inverse)
    )

    # ── LOW noise: 2% Gaussian (SNR >> 10:1) ── #
    noise = rng.normal(0, base * 0.02, n)

    yield_vals = (
        base
        + linear_effect
        + pH_penalty
        + te_stress
        + nm_interact
        + noise
    )

    # Clip to agronomically plausible range [50%, 175%] of base
    yield_vals = np.clip(yield_vals, base * 0.50, base * 1.75)

    for i in range(n):
        rows.append({
            "N":            round(float(N_v[i]),  2),
            "P":            round(float(P_v[i]),  2),
            "K":            round(float(K_v[i]),  2),
            "pH":           round(float(pH_v[i]), 2),
            "moisture":     round(float(mo_v[i]), 2),
            "temperature":  round(float(te_v[i]), 2),
            "humidity":     round(float(hu_v[i]), 2),
            "rainfall":     round(float(ra_v[i]), 2),
            "crop_type":    crop_name,
            "crop_type_enc": CROP_ENC[crop_name],
            "yield_qph":   round(float(yield_vals[i]), 2),
        })

df = pd.DataFrame(rows).sample(frac=1, random_state=42).reset_index(drop=True)
df.to_csv("data/crop_data.csv", index=False)
print(f"Dataset generated: {len(df)} rows")
print(df.groupby("crop_type")["yield_qph"].agg(["min","mean","max"]).round(2))

# Quick SNR check
print("\n[SNR Check] Linear signal std / noise std per crop:")
for crop_name, p in CROPS.items():
    base = p["base_yield"]
    signal_std = base * 0.20 * (0.35 + 0.20 + 0.15 + 0.25 + 0.15 + 0.20 + 0.10) / np.sqrt(7)
    noise_std  = base * 0.02
    print(f"  {crop_name:<12} SNR ≈ {signal_std/noise_std:.1f}:1")
