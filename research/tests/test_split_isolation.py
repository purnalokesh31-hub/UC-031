"""Structural tests using fabricated fixtures only; these are not research scores."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from research import benchmark, freeze_protocol


class SplitIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.panel = self.root / "panel.csv"
        self.lock = self.root / "lock.json"
        self.data = pd.DataFrame([
            {"district_id": f"{district:03}", "year": year, "crop": "Fixture",
             "season": "annual", "yield_q_ha": 1.0,
             **{f: 1.0 for f in benchmark.FEATURES}}
            for district in range(20) for year in range(2000, 2010)])
        self.data.to_csv(self.panel, index=False)
        with contextlib.redirect_stdout(io.StringIO()):
            freeze_protocol.freeze(self.panel, self.lock)
        self.config = json.loads(self.lock.read_text())["crops"]["Fixture"]

    def test_development_excludes_every_reserved_role(self):
        dev = benchmark.development_rows(self.data, "Fixture", self.config)
        self.assertFalse(set(dev.district_id) & set(self.config["held_out_district_ids"]))
        self.assertTrue((dev.year < self.config["calibration_year"]).all())
        self.assertEqual(len(dev), self.config["roles"]["fit"]["n_rows"])
        self.assertTrue(dev.district_id.str.len().eq(3).all())

    def test_changed_assignment_rejected(self):
        bad = self.data.copy()
        bad.loc[0, "season"] = "changed"
        with self.assertRaisesRegex(ValueError, "hash"):
            benchmark.development_rows(bad, "Fixture", self.config)

    def test_freeze_refuses_overwrite(self):
        with self.assertRaises(FileExistsError):
            freeze_protocol.freeze(self.panel, self.lock)

    def test_small_calibration_rejected(self):
        with self.assertRaisesRegex(ValueError, "Too few"):
            benchmark.conformal_radius(np.ones(3), np.zeros(3))
        self.assertEqual(benchmark.conformal_radius(np.ones(9), np.zeros(9)), 1)

    def test_default_run_never_calls_reserved_evaluation(self):
        # This manifest is an artificial fixture for control-flow testing only.
        (self.root / "manifest.json").write_text(json.dumps({
            "status": "prepared_real_source_inputs_not_yet_independently_validated",
            "panel_sha256": benchmark.sha256(self.panel)}))
        with patch.object(benchmark, "district_holdouts", return_value=([], [])) as dev, \
                patch.object(benchmark, "reserved_lockboxes") as reserved, \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "No evaluations"):
                benchmark.run(self.panel, self.lock, self.root / "out")
        reserved.assert_not_called()
        supplied = dev.call_args.args[0]
        self.assertEqual(len(supplied), self.config["roles"]["fit"]["n_rows"])
        self.assertFalse(set(supplied.district_id) & set(self.config["held_out_district_ids"]))
        self.assertFalse(self.lock.with_name("lock.json.reserved_started.json").exists())

    def test_reserved_requires_unchanged_frozen_code(self):
        (self.root / "manifest.json").write_text(json.dumps({
            "status": "prepared_real_source_inputs_not_yet_independently_validated",
            "panel_sha256": benchmark.sha256(self.panel)}))
        manifest = json.loads(self.lock.read_text())
        manifest["evaluation_code_sha256"]["benchmark.py"] = "changed"
        self.lock.write_text(json.dumps(manifest))
        with patch.object(benchmark, "reserved_lockboxes") as reserved:
            with self.assertRaisesRegex(ValueError, "code hashes"):
                benchmark.run(self.panel, self.lock, self.root / "final", stage="reserved")
        reserved.assert_not_called()

    def test_failed_reserved_attempt_prevents_automatic_rescoring(self):
        (self.root / "manifest.json").write_text(json.dumps({
            "status": "prepared_real_source_inputs_not_yet_independently_validated",
            "panel_sha256": benchmark.sha256(self.panel)}))
        with patch.object(benchmark, "reserved_lockboxes", side_effect=RuntimeError("fixture failure")) as reserved, \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "fixture failure"):
                benchmark.run(self.panel, self.lock, self.root / "final1", stage="reserved")
            with self.assertRaises(FileExistsError):
                benchmark.run(self.panel, self.lock, self.root / "final2", stage="reserved")
        self.assertEqual(reserved.call_count, 1)


if __name__ == "__main__":
    unittest.main()
