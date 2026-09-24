# -*- coding: utf-8 -*-
"""
train_per_crop.py  (v2 — all bugs fixed)

Fixes vs v1:
  1. Per-crop StandardScaler + PCA(4), avoiding cross-crop PCA contamination
     while keeping the feature count aligned with the four-qubit kernel.
  2. Better SVR hyperparameters:
     Classical: C=50, epsilon=0.05, gamma='scale'
     Quantum:   C=5.0, epsilon=0.05, reps=2 (deeper entanglement)
  3. Larger training sets: 120 samples per crop for QSVR.
  4. Saved per-crop preprocessor alongside per-crop model so inference
     uses the correct scaler.

Usage:
    cd backend
    python training/train_per_crop.py
"""

import sys, os, time, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("PYTHONUTF8", "1")

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline
import joblib

from models.quantum_model   import QuantumSVR
from models.classical_model import ClassicalSVR

# ── Config ─────────────────────────────────────────────────────────── #
DATA_PATH    = "data/crop_data.csv"
SAVE_DIR     = "saved_models"
RANDOM_STATE = 42
TEST_SIZE    = 0.20
QUANTUM_TRAIN = 150   # kernel pairs = 150*151/2 = 11325 — ~3 min per crop
QUANTUM_TEST  =  60

CROPS = ["Rice", "Wheat", "Maize", "Cotton", "Sugarcane", "Groundnut"]
FEATURE_COLS = ["N","P","K","pH","moisture","temperature","humidity","rainfall"]


# ── Per-crop preprocessor: StandardScaler → PCA(4) ─────────────────── #
class CropScaler:
    """Keep classical and four-qubit quantum features dimensionally aligned."""
    def __init__(self, n_components=4):
        self.scaler = StandardScaler()
        self.n_components = n_components
        self.pca = PCA(n_components=n_components, random_state=RANDOM_STATE)

    def fit_transform(self, X):
        return self.pca.fit_transform(self.scaler.fit_transform(X))

    def transform(self, X):
        X_scaled = self.scaler.transform(X)
        # Existing v2 scaler files predate PCA; keep them loadable so the
        # service can run while models are being retrained.
        if not hasattr(self, "pca"):
            return X_scaled
        return self.pca.transform(X_scaled)

    def save(self, path):
        joblib.dump(self, path)
        print(f"  Scaler saved -> {path}")

    @staticmethod
    def load(path):
        return joblib.load(path)


def main():
    # Compatibility entry point: publish one complete, validated release.
    from training.train_validated import run
    return run()


if __name__ == "__main__":
    main()
