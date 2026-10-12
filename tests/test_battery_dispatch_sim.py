import unittest

import battery_dispatch_sim as app


class BatteryDispatchTests(unittest.TestCase):
    def setUp(self):
        self.loads = app.generate_load()
        self.rows = app.dispatch(self.loads)

    def test_deterministic_scenario_and_peak_is_reduced(self):
        self.assertEqual(self.loads, app.generate_load())
        report = app.evaluate(self.loads, self.rows)
        self.assertGreater(report["peak_reduction_kw"], 0)

    def test_soc_power_and_interval_balance_constraints(self):
        for row in self.rows:
            self.assertGreaterEqual(row["soc_after_kwh"], app.MIN_SOC_KWH - 1e-9)
            self.assertLessEqual(row["soc_after_kwh"], app.MAX_SOC_KWH + 1e-9)
            self.assertLessEqual(row["charge_kw"], app.MAX_POWER_KW + 1e-9)
            self.assertLessEqual(row["discharge_kw"], app.MAX_POWER_KW + 1e-9)
            self.assertAlmostEqual(row["soc_balance_residual_kwh"], 0.0, places=9)

    def test_energy_accounting_closes_and_invalid_soc_is_rejected(self):
        report = app.evaluate(self.loads, self.rows)
        self.assertAlmostEqual(report["energy_conservation_residual_kwh"], 0.0, places=8)
        with self.assertRaises(ValueError):
            app.dispatch(self.loads, initial_soc_kwh=30.0)


if __name__ == "__main__":
    unittest.main()
