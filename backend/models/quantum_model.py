"""
quantum_model.py
Hybrid Quantum Support Vector Regressor (QSVR)

Architecture:
  • MinMaxScaler features → [0, π]   — valid rotation-angle range for ZZFeatureMap
  • MinMaxScaler targets  → [0, 1]   — SVR with precomputed kernel has limited output
                                        range; y-scaling is essential for convergence
  • ZZFeatureMap (4 qubits, reps=1, linear entanglement) encodes features
  • FidelityQuantumKernel evaluates inner products via StatevectorSampler
  • Classical SVR trains on the resulting quantum kernel matrix
  • Inverse-transform predictions back to original yield (qph) units

Critical note on y-scaling:
  With a precomputed quantum kernel, off-diagonal K values are typically 0.01–0.3.
  SVR output range ≈ n_SVs × C × K_avg. For n=120, C=10, K_avg≈0.1 → range ≈ 120.
  Crop yield spans ~10–600 qph → must scale y to [0,1] so SVR can reach all targets.

Why QSVR over QNN:
  - Avoids barren plateau / vanishing gradient problem
  - Deterministic kernel evaluation — no parameter optimization instability
  - Provably maps to feature Hilbert space via quantum fidelity
"""

import numpy as np
import joblib
from sklearn.svm import SVR
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, r2_score

try:
    from qiskit.circuit.library import ZZFeatureMap
    from qiskit_machine_learning.kernels import FidelityQuantumKernel
    # Qiskit ML 0.7 moved the fidelity primitive dependency to
    # qiskit-algorithms; keep the import compatible with the pinned stack.
    try:
        from qiskit_machine_learning.state_fidelities import ComputeUncompute
    except ImportError:
        from qiskit_algorithms.state_fidelities import ComputeUncompute
    try:
        from qiskit_aer.primitives import Sampler as AerSampler
    except ImportError:
        AerSampler = None
    from qiskit.primitives import Sampler
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    print("Warning: Qiskit not found -- QuantumSVR will use RBF kernel fallback")


class QuantumSVR:
    """
    Hybrid Quantum Support Vector Regressor using ZZFeatureMap kernel.
    Internally rescales features to [0, π] and targets to [0, 1].
    Falls back to an RBF kernel SVR if Qiskit is not installed.
    """

    def __init__(self, n_qubits: int = 4, reps: int = 1, C: float = 10.0, epsilon: float = 0.01):
        self.n_qubits = n_qubits
        self.reps     = reps
        self.C        = C
        self.epsilon  = epsilon
        self.model    = None
        self.kernel   = None
        self._use_quantum = QISKIT_AVAILABLE
        self.train_X  = None   # scaled train features — stored for test-time kernel eval
        self._x_scaler = None  # MinMaxScaler to [0, π] — fitted on X_train
        self._y_scaler = None  # MinMaxScaler to [0, 1]  — fitted on y_train
        self._kernel_matrix_train = None  # cached to avoid recomputing for train metrics
        self.metrics  = {}

    # ------------------------------------------------------------------ #
    def _build_kernel(self):
        if not self._use_quantum:
            return None
        feature_map = ZZFeatureMap(
            feature_dimension=self.n_qubits,
            reps=self.reps,
            entanglement="linear",   # reps=1+linear = shallow circuit, avoids kernel concentration
        )
        # qiskit-algorithms 0.3 expects the V1 BaseSampler interface.
        # Aer is materially faster than the reference primitive on Windows.
        sampler = (AerSampler(run_options={"shots": 1024})
                   if AerSampler is not None else Sampler())
        fidelity = ComputeUncompute(sampler=sampler)
        kernel   = FidelityQuantumKernel(feature_map=feature_map, fidelity=fidelity)
        return kernel

    def _scale_X(self, X: np.ndarray, fit: bool = False) -> np.ndarray:
        """Rescale features to [0, π] for ZZFeatureMap rotation angles."""
        if not self._use_quantum:
            return X
        if fit:
            self._x_scaler = MinMaxScaler(feature_range=(0, np.pi))
            return self._x_scaler.fit_transform(X)
        return self._x_scaler.transform(X)

    def _scale_y(self, y: np.ndarray, fit: bool = False) -> np.ndarray:
        """Rescale targets to [0, 1] so SVR output range matches yield range."""
        y2d = y.reshape(-1, 1)
        if fit:
            self._y_scaler = MinMaxScaler(feature_range=(0, 1))
            return self._y_scaler.fit_transform(y2d).ravel()
        return self._y_scaler.transform(y2d).ravel()

    def _inverse_scale_y(self, y_scaled: np.ndarray) -> np.ndarray:
        return self._y_scaler.inverse_transform(y_scaled.reshape(-1, 1)).ravel()

    # ------------------------------------------------------------------ #
    def fit(self, X_train: np.ndarray, y_train: np.ndarray):
        print(f"[QuantumSVR] Training on {X_train.shape[0]} samples × {X_train.shape[1]} features")

        if self._use_quantum:
            # ── Scale features to [0, π] and targets to [0, 1] ── #
            X_scaled = self._scale_X(X_train, fit=True)
            y_scaled = self._scale_y(y_train, fit=True)
            self.train_X = X_scaled

            print(f"[QuantumSVR] X range: [{X_scaled.min():.3f}, {X_scaled.max():.3f}]  "
                  f"y range: [{y_scaled.min():.3f}, {y_scaled.max():.3f}]")

            print("[QuantumSVR] Building ZZFeatureMap quantum kernel …")
            self.kernel = self._build_kernel()

            n = X_scaled.shape[0]
            total = n * (n + 1) // 2
            print(f"[QuantumSVR] Computing kernel matrix ({n}×{n} = {total} circuit pairs) …")
            self._kernel_matrix_train = self.kernel.evaluate(X_scaled)

            print(f"[QuantumSVR] Kernel stats: diag={np.diag(self._kernel_matrix_train).mean():.4f} "
                  f"off-diag mean={self._kernel_matrix_train[~np.eye(n, dtype=bool)].mean():.4f}")

            self.model = SVR(kernel="precomputed", C=self.C, epsilon=self.epsilon)
            self.model.fit(self._kernel_matrix_train, y_scaled)
            print("✅ [QuantumSVR] Quantum kernel SVR trained successfully")

            # Reuse cached kernel matrix — no extra circuit evaluations
            y_pred_scaled = self.model.predict(self._kernel_matrix_train)
            y_pred = self._inverse_scale_y(y_pred_scaled)
        else:
            # Graceful fallback
            self.train_X = X_train
            self.model = SVR(kernel="rbf", C=self.C, epsilon=self.epsilon, gamma="scale")
            self.model.fit(X_train, y_train)
            print("✅ [QuantumSVR] Fallback RBF SVR trained (Qiskit unavailable)")
            y_pred = self.model.predict(X_train)

        self.metrics = {
            "train_mse": float(mean_squared_error(y_train, y_pred)),
            "train_r2":  float(r2_score(y_train, y_pred)),
        }
        print(f"[QuantumSVR] Train R²={self.metrics['train_r2']:.4f} | "
              f"Train MSE={self.metrics['train_mse']:.2f}")
        return self

    # ------------------------------------------------------------------ #
    def predict(self, X_test: np.ndarray) -> np.ndarray:
        if self._use_quantum and self.kernel is not None:
            X_scaled = self._scale_X(X_test, fit=False)
            K_test = self.kernel.evaluate(X_scaled, self.train_X)
            y_scaled = self.model.predict(K_test)
            y_scaled = np.clip(y_scaled, 0.0, 1.0)   # prevent inverse-transform blow-up
            return self._inverse_scale_y(y_scaled)
        return self.model.predict(X_test)

    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> dict:
        y_pred = self.predict(X_test)
        return {
            "mse":         float(mean_squared_error(y_test, y_pred)),
            "r2":          float(r2_score(y_test, y_pred)),
            "predictions": y_pred.tolist(),
        }

    # ------------------------------------------------------------------ #
    def save(self, path: str = "saved_models/quantum_svr.pkl"):
        joblib.dump(self, path)
        print(f"[QuantumSVR] Saved → {path}")

    @staticmethod
    def load(path: str = "saved_models/quantum_svr.pkl") -> "QuantumSVR":
        return joblib.load(path)
