"""Independent circuit and kernel checks on generated numerical fixtures only."""
import unittest

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from research.benchmark import QuantumKernelAblation, QuantumKernelRegressor


class QuantumNumericsTests(unittest.TestCase):
    def setUp(self):
        self.X = np.random.default_rng(314).normal(size=(12, 8))
        self.y = self.X[:, 0] + self.X[:, 1] ** 2

    def test_numpy_states_match_independent_qiskit_circuit(self):
        for layers in (1, 2):
            model = QuantumKernelRegressor(layers=layers, angle_scale=.4).fit(self.X, self.y)
            for i, angles in enumerate(model.scaler_.transform(self.X) * model.angle_scale):
                circuit = QuantumCircuit(4)
                for _ in range(layers):
                    for q in range(4):
                        circuit.ry(np.pi / 2 + angles[q], q)
                        circuit.rz(angles[q + 4], q)
                    for q in range(3):
                        circuit.cx(q, q + 1)
                np.testing.assert_allclose(model.states_[i], Statevector.from_instruction(circuit).data,
                                           rtol=1e-12, atol=1e-12)

    def test_fidelity_kernel_has_unit_diagonal_and_is_psd(self):
        model = QuantumKernelRegressor(layers=2, angle_scale=.4).fit(self.X, self.y)
        kernel = np.abs(model.states_ @ model.states_.conj().T) ** 2
        np.testing.assert_allclose(np.diag(kernel), 1, atol=1e-12)
        np.testing.assert_allclose(kernel, kernel.T, atol=1e-12)
        self.assertGreaterEqual(np.linalg.eigvalsh(kernel).min(), -1e-10)
        centered = model.centerer_.transform(kernel)
        np.testing.assert_allclose(centered.mean(axis=0), 0, atol=1e-12)
        self.assertGreaterEqual(np.linalg.eigvalsh(centered).min(), -1e-10)

    def test_final_common_entangler_cancels_from_one_layer_fidelity(self):
        with_cnot = QuantumKernelAblation(layers=1, angle_scale=.4, entangle=True).fit(self.X, self.y)
        without = QuantumKernelAblation(layers=1, angle_scale=.4, entangle=False).fit(self.X, self.y)
        def kernel(model):
            return np.abs(model.states_ @ model.states_.conj().T) ** 2
        np.testing.assert_allclose(kernel(with_cnot), kernel(without), rtol=1e-12, atol=1e-12)

    def test_prediction_batch_composition_does_not_change_centering(self):
        model = QuantumKernelRegressor(layers=2, angle_scale=.15).fit(self.X, self.y)
        rows = np.random.default_rng(315).normal(size=(5, 8))
        alone = model.predict(rows[:1])[0]
        batch = model.predict(rows)[0]
        self.assertAlmostEqual(alone, batch, places=8)


if __name__ == "__main__":
    unittest.main()
