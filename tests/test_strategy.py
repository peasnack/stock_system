import unittest

from core.strategy import decide_for_stock


class DecideForStockTest(unittest.TestCase):
    def test_hard_drop_has_highest_priority(self) -> None:
        decision = decide_for_stock(
            {"pct_chg": -5.1, "score": 90, "holding": {"quantity": 100}},
            "STRONG",
            "RISK_OFF",
        )

        self.assertEqual(decision["action"], "REDUCE")
        self.assertIn("个股跌幅超过5%，优先降仓", decision["reasons"])

    def test_hard_drop_without_position_does_not_reduce(self) -> None:
        decision = decide_for_stock(
            {"pct_chg": -5.1, "score": 90, "holding": {"quantity": 0}},
            "STRONG",
            "RISK_OFF",
        )

        self.assertEqual(decision["action"], "NO_TRADE")

    def test_weak_market_blocks_trading(self) -> None:
        decision = decide_for_stock({"pct_chg": 1.0, "score": 90}, "WEAK", "RISK_OFF")

        self.assertEqual(decision["action"], "NO_TRADE")

    def test_strong_market_and_score_can_buy(self) -> None:
        decision = decide_for_stock({"pct_chg": 1.0, "score": 75}, "STRONG", "RISK_OFF")

        self.assertEqual(decision["action"], "BUY")


if __name__ == "__main__":
    unittest.main()
