import unittest
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import ParameterGrid

from research import benchmark
from research.prepare_rice_pilot import annual_weather, parse_soil, FEATURES


class RicePilotTests(unittest.TestCase):
    def weather(self, year):
        dates = pd.date_range(f"{year}-01-01", f"{year+1}-12-31")
        values = {k: {d.strftime("%Y%m%d"): value for d in dates}
                  for k, value in {"T2M": 20, "T2M_MAX": 30, "PRECTOTCORR": 1, "RH2M": 60}.items()}
        return {"header": {"time_standard": "UTC", "fill_value": -999},
                "parameters": {k: {"units": u} for k, u in {"T2M": "C", "T2M_MAX": "C", "PRECTOTCORR": "mm/day", "RH2M": "%"}.items()},
                "properties": {"parameter": values}}

    def test_agricultural_year_and_leap_day(self):
        result = annual_weather(self.weather(2011), 2011)
        self.assertEqual(result["weather_days"], 366)
        self.assertEqual(result["weather_start"], "2011-06-01")
        self.assertEqual(result["weather_end"], "2012-05-31")
        self.assertEqual(result["annual_precip_mm"], 366)

    def test_missing_day_is_not_silently_summed(self):
        payload = self.weather(2010)
        payload["properties"]["parameter"]["PRECTOTCORR"]["20100602"] = -999
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            annual_weather(payload, 2010)

    def test_every_tuned_family_has_25_configurations_and_clones(self):
        for name, (estimator, grid) in benchmark.estimators(17, FEATURES).items():
            if estimator is None:
                continue
            self.assertEqual(len(ParameterGrid(grid)), 1 if name == "year_trend_baseline" else 25)
            clone(estimator).set_params(**next(iter(ParameterGrid(grid))))

    def test_quantum_ablation_matches_main_when_entangled(self):
        X = np.random.default_rng(11).normal(size=(24, 8))
        y = X[:, 0] + X[:, 3] ** 2
        main = benchmark.QuantumKernelRegressor(layers=2).fit(X, y)
        ablated = benchmark.QuantumKernelAblation(layers=2, entangle=True).fit(X, y)
        np.testing.assert_allclose(main.predict(X), ablated.predict(X), rtol=1e-6, atol=1e-6)


if __name__ == "__main__":
    unittest.main()
