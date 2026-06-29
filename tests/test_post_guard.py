import unittest

from src.risk.post_guard import apply_post_guard


class PostGuardTest(unittest.TestCase):
    def test_blocks_buy_when_local_precheck_disallows_buy(self) -> None:
        result = apply_post_guard(
            {
                "allow_buy": True,
                "allow_switch": True,
                "hard_stop_triggered": False,
                "decisions": [{"code": "601138", "action": "BUY", "reason": "AI wants buy"}],
            },
            {
                "allow_buy": False,
                "allow_switch": False,
                "hard_stop_triggered": False,
                "core_logic_invalidated": False,
                "data_complete": True,
            },
        )

        self.assertFalse(result["decision"]["allow_buy"])
        self.assertEqual(result["decision"]["decisions"][0]["action"], "NO_TRADE")

    def test_blocks_sell_all_without_hard_stop_or_logic_invalidation(self) -> None:
        result = apply_post_guard(
            {
                "allow_buy": False,
                "allow_switch": False,
                "hard_stop_triggered": False,
                "decisions": [{"code": "601138", "action": "SELL_ALL", "reason": "AI wants sell all"}],
            },
            {
                "allow_buy": False,
                "allow_switch": False,
                "hard_stop_triggered": False,
                "core_logic_invalidated": False,
                "data_complete": True,
            },
        )

        self.assertEqual(result["decision"]["decisions"][0]["action"], "REDUCE_WATCH")

    def test_data_incomplete_only_allows_safe_actions(self) -> None:
        result = apply_post_guard(
            {
                "decisions": [
                    {"code": "601138", "action": "REDUCE", "reason": "AI wants reduce"},
                    {"code": "002475", "action": "WARNING", "reason": "watch"},
                ],
            },
            {
                "allow_buy": False,
                "allow_switch": False,
                "hard_stop_triggered": False,
                "core_logic_invalidated": False,
                "data_complete": False,
            },
        )

        self.assertEqual(result["decision"]["decisions"][0]["action"], "NO_TRADE")
        self.assertEqual(result["decision"]["decisions"][1]["action"], "WARNING")


if __name__ == "__main__":
    unittest.main()
