import unittest
from unittest.mock import patch

import pandas as pd

from core.extended_fetch import fetch_extended_data


class FetchExtendedDataTest(unittest.TestCase):
    def test_fetches_extended_stock_context(self) -> None:
        stocks = {"601138": {"price": 10.0}}

        with (
            patch("core.extended_fetch.ak.stock_hsgt_fund_flow_summary_em", return_value=pd.DataFrame([{"交易日": "2026-06-26", "沪股通": 1.0, "深股通": 2.0}])),
            patch("core.extended_fetch.ak.stock_board_industry_name_em", return_value=pd.DataFrame([{"板块名称": "消费电子", "涨跌幅": 1.2}])),
            patch("core.extended_fetch.ak.stock_sector_fund_flow_rank", return_value=pd.DataFrame([{"名称": "消费电子", "今日主力净流入-净额": 3.0}])),
            patch("core.extended_fetch.ak.stock_financial_abstract", return_value=pd.DataFrame([{"指标": "营业总收入", "20260331": 100.0}, {"指标": "归母净利润", "20260331": 10.0}])),
            patch("core.extended_fetch.ak.stock_news_em", return_value=pd.DataFrame([{"新闻标题": "测试新闻"}])),
            patch("core.extended_fetch.ak.stock_research_report_em", return_value=pd.DataFrame([{"报告名称": "测试研报"}])),
            patch("core.extended_fetch.ak.stock_hsgt_individual_em", return_value=pd.DataFrame([{"持股日期": "2026-06-26", "今日增持股数": 1.0}])),
            patch("core.extended_fetch.ak.stock_individual_fund_flow", return_value=pd.DataFrame([{"日期": "2026-06-26", "主力净流入-净额": 5.0}])),
            patch("core.extended_fetch.ak.stock_zh_a_hist", return_value=pd.DataFrame([{"日期": f"2026-06-{day:02d}", "收盘": float(day)} for day in range(1, 22)])),
            patch("core.extended_fetch.ak.stock_lhb_stock_detail_date_em", return_value=pd.DataFrame()),
        ):
            result = fetch_extended_data(stocks, "2026-06-26")

        stock = result["stocks"]["601138"]
        self.assertEqual(stock["financial"]["latest_period"], "20260331")
        self.assertEqual(stock["news"][0]["新闻标题"], "测试新闻")
        self.assertEqual(stock["research"][0]["报告名称"], "测试研报")
        self.assertEqual(stock["fund_flow"]["主力净流入-净额"], 5.0)
        self.assertEqual(stock["history"]["trend"], "ABOVE_MA20")
        self.assertIn("holding", stock)


if __name__ == "__main__":
    unittest.main()
