import unittest
from unittest.mock import patch

import pandas as pd

from core.fetch import fetch_index_spot, resolve_trade_date


class FetchIndexSpotTest(unittest.TestCase):
    def test_falls_back_when_primary_index_source_misses_required_indices(self) -> None:
        primary = pd.DataFrame(
            [
                {"代码": "000001", "名称": "上证指数"},
            ]
        )
        fallback = pd.DataFrame(
            [
                {"代码": "000001", "名称": "上证指数"},
                {"代码": "399001", "名称": "深证成指"},
                {"代码": "399006", "名称": "创业板指"},
            ]
        )

        with (
            patch("core.fetch.ak.stock_zh_index_spot_sina", return_value=primary),
            patch("core.fetch.ak.stock_zh_index_spot_em", return_value=fallback),
        ):
            result = fetch_index_spot()

        self.assertEqual(len(result), 3)


class ResolveTradeDateTest(unittest.TestCase):
    def test_uses_latest_trade_date_from_calendar_when_frames_have_no_date(self) -> None:
        calendar = pd.DataFrame(
            {
                "trade_date": [
                    "2026-06-25",
                    "2026-06-26",
                    "2026-06-29",
                ]
            }
        )

        with patch("core.fetch.ak.tool_trade_date_hist_sina", return_value=calendar):
            result = resolve_trade_date(pd.DataFrame({"代码": ["601138"]}), pd.DataFrame({"代码": ["000001"]}))

        self.assertEqual(result, "2026-06-26")


if __name__ == "__main__":
    unittest.main()
