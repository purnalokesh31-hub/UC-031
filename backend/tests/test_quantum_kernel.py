"""Check the batched simulator against independent Qiskit circuits."""
import sys
import unittest
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models.validated_yield import ExactQuantumRegressor, QuantumKernelRegressor


class QuantumKernelTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(17)
        self.X = rng.normal(size=(24, 8))
        self.y = self.X[:, 0] + self.X[:, 3] ** 2

    def test_states_match_qiskit_for_both_encodings(self):
        for layers in (1, 2):
            model = QuantumKernelRegressor(layers=layers, angle_scale=.4).fit(self.X, self.y)
            reference = []
            for row in model.scaler_.transform(self.X[:5]) * model.angle_scale:
                circuit = QuantumCircuit(4)
                for _ in range(layers):
                    for q in range(4):
                        circuit.ry(np.pi / 2 + row[q], q)
                        circuit.rz(row[q + 4], q)
                    for q in range(3):
                        circuit.cx(q, q + 1)
                reference.append(Statevector.from_instruction(circuit).data)
            np.testing.assert_allclose(model._states(self.X[:5]), reference, atol=1e-12)

    def test_original_predictions_are_preserved_without_centering(self):
        old = ExactQuantumRegressor(angle_scale=.15, alpha=.001).fit(self.X, self.y)
        new = QuantumKernelRegressor(angle_scale=.15, alpha=.001, center_kernel=False).fit(self.X, self.y)
        np.testing.assert_allclose(old.predict(self.X), new.predict(self.X), atol=1e-8)

    def test_prediction_batch_does_not_change_centering_or_scaling(self):
        model = QuantumKernelRegressor(layers=2).fit(self.X, self.y)
        before = model.centerer_.K_fit_rows_.copy()
        single = model.predict(self.X[:1])
        batch = model.predict(np.vstack([self.X[:1], np.full((3, 8), 100)]))
        np.testing.assert_allclose(single, batch[:1], atol=1e-8)
        np.testing.assert_array_equal(before, model.centerer_.K_fit_rows_)


if __name__ == '__main__':
    unittest.main()
