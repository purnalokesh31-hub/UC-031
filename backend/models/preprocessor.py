"""
preprocessor.py
StandardScaler + PCA pipeline that reduces 9 features → 4 principal components
matching the 4-qubit quantum circuit width.
"""

import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

FEATURE_COLS = ["N", "P", "K", "pH", "moisture", "temperature", "humidity", "rainfall", "crop_type_enc"]
TARGET_COL   = "yield_qph"
N_COMPONENTS = 4   # Must match qubit count in ZZFeatureMap


class CropPreprocessor:
    def __init__(self, n_components: int = N_COMPONENTS):
        self.n_components = n_components
        self.scaler = StandardScaler()
        self.pca    = PCA(n_components=n_components, random_state=42)
        self.fitted = False

    # ------------------------------------------------------------------ #
    def fit(self, df: pd.DataFrame):
        X = df[FEATURE_COLS].values
        y = df[TARGET_COL].values
        X_scaled = self.scaler.fit_transform(X)
        self.pca.fit(X_scaled)
        self.fitted = True
        evr = self.pca.explained_variance_ratio_
        print(f"PCA explained variance: {evr.round(3)}  |  Total: {evr.sum():.3f}")
        return self

    def transform(self, df: pd.DataFrame):
        assert self.fitted, "Call fit() before transform()"
        X = df[FEATURE_COLS].values
        X_scaled = self.scaler.transform(X)
        return self.pca.transform(X_scaled)

    def fit_transform(self, df: pd.DataFrame):
        self.fit(df)
        return self.transform(df)

    def transform_raw(self, raw: dict):
        """Transform a single prediction request dict → 4-component array."""
        row = {col: [raw.get(col, 0)] for col in FEATURE_COLS}
        df  = pd.DataFrame(row)
        return self.transform(df)

    # ------------------------------------------------------------------ #
    def save(self, path: str = "saved_models/preprocessor.pkl"):
        joblib.dump(self, path)
        print(f"Preprocessor saved -> {path}")

    @staticmethod
    def load(path: str = "saved_models/preprocessor.pkl") -> "CropPreprocessor":
        return joblib.load(path)
