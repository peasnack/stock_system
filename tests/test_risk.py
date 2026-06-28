import unittest

from core.risk import detect_factor_risk


class DetectFactorRiskTest(unittest.TestCase):
    def test_same_factor_drop_with_index_down_triggers_risk(self) -> None:
        result = detect_factor_risk(
            {"a": {"pct_chg": -5.1}, "b": {"pct_chg": -6.0}},
            {"000001": {"pct_chg": -0.2}},
        )

        self.assertEqual(result["state"], "RISK_ON")
        self.assertFalse(result["allow_add"])

    def test_no_risk_when_index_is_not_down(self) -> None:
        result = detect_factor_risk(
            {"a": {"pct_chg": -5.1}, "b": {"pct_chg": -6.0}},
            {"000001": {"pct_chg": 0.1}},
        )

        self.assertEqual(result["state"], "RISK_OFF")
        self.assertTrue(result["allow_add"])


if __name__ == "__main__":
    unittest.main()
