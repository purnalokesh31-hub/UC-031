"""
classical_model.py
Classical SVR baseline using RBF kernel for side-by-side comparison with QSVR.
"""

import numpy as np
import joblib
from sklearn.svm import SVR
from sklearn.metrics import mean_squared_error, r2_score


class ClassicalSVR:
    """
    Classical Support Vector Regressor (RBF kernel) — baseline model.
    Trained on the same PCA-reduced features as QuantumSVR for fair comparison.
    """

    def __init__(self, C: float = 10.0, epsilon: float = 0.1, gamma: str = "scale"):
        self.C       = C
        self.epsilon = epsilon
        self.gamma   = gamma
        self.model   = SVR(kernel="rbf", C=C, epsilon=epsilon, gamma=gamma)
        self.metrics = {}

    # ------------------------------------------------------------------ #
    def fit(self, X_train: np.ndarray, y_train: np.ndarray):
        print(f"[ClassicalSVR] Training on {X_train.shape[0]} samples …")
        self.model.fit(X_train, y_train)
        y_pred = self.model.predict(X_train)
        self.metrics = {
            "train_mse": float(mean_squared_error(y_train, y_pred)),
            "train_r2":  float(r2_score(y_train, y_pred)),
        }
        print(f"[ClassicalSVR] ✅ Trained | Train MSE={self.metrics['train_mse']:.4f} | R²={self.metrics['train_r2']:.4f}")
        return self

    def predict(self, X_test: np.ndarray) -> np.ndarray:
        return self.model.predict(X_test)

    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> dict:
        y_pred = self.model.predict(X_test)
        return {
            "mse":        float(mean_squared_error(y_test, y_pred)),
            "r2":         float(r2_score(y_test, y_pred)),
            "predictions": y_pred.tolist(),
        }

    # ------------------------------------------------------------------ #
    def save(self, path: str = "saved_models/classical_svr.pkl"):
        joblib.dump(self, path)
        print(f"[ClassicalSVR] Saved → {path}")

    @staticmethod
    def load(path: str = "saved_models/classical_svr.pkl") -> "ClassicalSVR":
        return joblib.load(path)
