"""Checks of source normalization, not predictive model evaluation."""
import unittest

from research.prepare_dld_staging import crop_values, unique


class DldStagingTests(unittest.TestCase):
    def row(self, area=2, production=6, yield_value=3100):
        return {"RICE AREA (1000 ha)": str(area), "RICE PRODUCTION (1000 tons)": str(production),
                "RICE YIELD (Kg per ha)": str(yield_value)}

    def test_units_and_reported_target_are_preserved(self):
        data, reasons = crop_values(self.row(), "RICE")
        self.assertFalse(reasons)
        self.assertEqual(data["area_ha"], 2000)
        self.assertEqual(data["production_tonnes"], 6000)
        self.assertEqual(data["reported_yield_q_ha"], 31)
        self.assertEqual(data["ratio_yield_kg_ha_diagnostic"], 3000)

    def test_missing_zero_and_other_negative_are_distinct(self):
        data, reasons = crop_values(self.row(area=-1, production=0, yield_value=-500), "RICE")
        self.assertIsNone(data)
        self.assertEqual(reasons, ["area_source_missing_code_minus_one", "production_zero", "yield_invalid_negative"])

    def test_nonfinite_yield_is_rejected(self):
        data, reasons = crop_values(self.row(yield_value="NaN"), "RICE")
        self.assertIsNone(data)
        self.assertEqual(reasons, ["yield_missing_or_nonfinite"])

    def test_duplicate_keys_fail(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            unique([{"id": "01"}, {"id": "01"}], ["id"], "fixture")


if __name__ == "__main__":
    unittest.main()
