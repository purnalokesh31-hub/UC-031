"""Serializable estimators; every fitted transform belongs to the estimator."""
import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.preprocessing import StandardScaler, KernelCenterer
from sklearn.kernel_ridge import KernelRidge
from sklearn.utils.validation import check_X_y, check_array, check_is_fitted

FEATURES = ['N', 'P', 'K', 'pH', 'moisture', 'temperature', 'humidity', 'rainfall']
CROPS = ['Rice', 'Wheat', 'Maize', 'Cotton', 'Sugarcane', 'Groundnut']


class ExactQuantumRegressor(RegressorMixin, BaseEstimator):
    """Four simulated qubits encode all eight features using RY and RZ gates.

    K(x,y)=|<psi(x)|psi(y)>|². Cache reference states, never measured shots.
    Encoding and target scaling are fitted separately within each CV fold.
    """
    def __init__(self, angle_scale=0.15, alpha=0.001):
        self.angle_scale = angle_scale
        self.alpha = alpha

    def _states(self, X):
        from qiskit import QuantumCircuit
        from qiskit.quantum_info import Statevector
        from qiskit.circuit import ParameterVector
        parameters = ParameterVector('x', 8)
        circuit = QuantumCircuit(4)
        # The offset keeps both rotations sensitive to features near zero.
        for q in range(4):
            circuit.ry(np.pi / 2 + parameters[q], q)
            circuit.rz(parameters[q + 4], q)
        for q in range(3):
            circuit.cx(q, q + 1)
        angles = self.scaler_.transform(X) * self.angle_scale
        return np.asarray([Statevector.from_instruction(circuit.assign_parameters(
            dict(zip(parameters, row)))).data for row in angles])

    def fit(self, X, y):
        X, y = check_X_y(X, y)
        if X.shape[1] != 8:
            raise ValueError('Quantum encoding requires all eight raw features')
        self.n_features_in_ = 8
        self.scaler_ = StandardScaler().fit(X)
        self.target_ = StandardScaler().fit(y[:, None])
        self.states_ = self._states(X)
        kernel = np.abs(self.states_ @ self.states_.conj().T) ** 2
        self.regressor_ = KernelRidge(alpha=self.alpha, kernel='precomputed').fit(
            kernel, self.target_.transform(y[:, None]).ravel())
        return self

    def predict(self, X):
        check_is_fitted(self, 'regressor_')
        X = check_array(X)
        if X.shape[1] != self.n_features_in_:
            raise ValueError('Expected eight raw features')
        kernel = np.abs(self._states(X) @ self.states_.conj().T) ** 2
        return self.target_.inverse_transform(self.regressor_.predict(kernel)[:, None]).ravel()


class QuantumKernelRegressor(ExactQuantumRegressor):
    """Batched exact four-qubit simulation with optional data re-uploading.

    A second encoding after the CNOT chain makes entanglement affect fidelity.
    With one layer this is the original RY/RZ circuit, evaluated without a
    Python/Qiskit circuit construction for each row. Kernel centering is fit
    only on training states. Keep the old class unchanged for saved releases.
    """
    def __init__(self, angle_scale=0.05, alpha=0.00001, layers=1, center_kernel=True):
        self.angle_scale = angle_scale
        self.alpha = alpha
        self.layers = layers
        self.center_kernel = center_kernel

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
            for q in range(3):
                permutation = basis ^ (((basis >> q) & 1) << (q + 1))
                states = states[:, permutation]
        return states

    def fit(self, X, y):
        X, y = check_X_y(X, y)
        if X.shape[1] != 8:
            raise ValueError('Quantum encoding requires all eight raw features')
        self.n_features_in_ = 8
        self.scaler_ = StandardScaler().fit(X)
        self.target_ = StandardScaler().fit(y[:, None])
        self.states_ = self._states(X)
        kernel = np.abs(self.states_ @ self.states_.conj().T) ** 2
        self.centerer_ = KernelCenterer().fit(kernel) if self.center_kernel else None
        if self.centerer_ is not None:
            kernel = self.centerer_.transform(kernel)
        self.regressor_ = KernelRidge(alpha=self.alpha, kernel='precomputed').fit(
            kernel, self.target_.transform(y[:, None]).ravel())
        return self

    def predict(self, X):
        check_is_fitted(self, 'regressor_')
        X = check_array(X)
        if X.shape[1] != self.n_features_in_:
            raise ValueError('Expected eight raw features')
        kernel = np.abs(self._states(X) @ self.states_.conj().T) ** 2
        if self.centerer_ is not None:
            kernel = self.centerer_.transform(kernel)
        return self.target_.inverse_transform(self.regressor_.predict(kernel)[:, None]).ravel()
