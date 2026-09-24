# -*- coding: utf-8 -*-
"""
train_per_crop_resume.py
Resume training from Wheat onward (Rice already done with v3 data).
Identical logic to train_per_crop.py but skips Rice.
"""

import sys, os, time, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("PYTHONUTF8", "1")

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import joblib

from models.quantum_model   import QuantumSVR
from models.classical_model import ClassicalSVR

DATA_PATH    = "data/crop_data.csv"
SAVE_DIR     = "saved_models"
RANDOM_STATE = 42
TEST_SIZE    = 0.20
QUANTUM_TRAIN = 150
QUANTUM_TEST  = 60

# Skip Rice — already trained with v3 data
CROPS = ["Wheat", "Maize", "Cotton", "Sugarcane", "Groundnut"]
FEATURE_COLS = ["N","P","K","pH","moisture","temperature","humidity","rainfall"]


class CropScaler:
    def __init__(self, n_components=4):
        self.scaler = StandardScaler()
        self.n_components = n_components
        self.pca = PCA(n_components=n_components, random_state=RANDOM_STATE)

    def fit_transform(self, X):
        return self.pca.fit_transform(self.scaler.fit_transform(X))

    def transform(self, X):
        X_scaled = self.scaler.transform(X)
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
