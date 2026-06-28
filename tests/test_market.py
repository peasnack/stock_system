import unittest

from core.market import classify_market


class ClassifyMarketTest(unittest.TestCase):
    def test_all_indices_down_over_two_is_weak(self) -> None:
        result = classify_market(
            {
                "000001": {"pct_chg": -2.1},
                "399001": {"pct_chg": -3.0},
                "399006": {"pct_chg": -2.5},
            },
            total_amount=100.0,
            previous_total_amount=110.0,
        )

        self.assertEqual(result["state"], "WEAK")
        self.assertIn("三大指数全部下跌超过2%", result["reasons"])

    def test_all_indices_up_with_amount_growth_is_strong(self) -> None:
        result = classify_market(
            {
                "000001": {"pct_chg": 0.6},
                "399001": {"pct_chg": 0.8},
                "399006": {"pct_chg": 1.1},
            },
            total_amount=110.0,
            previous_total_amount=100.0,
        )

        self.assertEqual(result["state"], "STRONG")
        self.assertEqual(result["amount_change_pct"], 10.0)


if __name__ == "__main__":
    unittest.main()
