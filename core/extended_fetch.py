import logging
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import akshare as ak
import pandas as pd

from config import (
    HISTORY_DAYS,
    NEWS_LIMIT,
    PORTFOLIO,
    RESEARCH_LIMIT,
    TARGET_STOCKS,
)
from core.fetch import DataFetchError
from core.network import akshare_network_env

logger = logging.getLogger(__name__)


def _clean_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _row_to_dict(row: pd.Series) -> dict[str, Any]:
    return {str(key): _clean_value(value) for key, value in row.items()}


def _head_records(df: pd.DataFrame, limit: int) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    return [_row_to_dict(row) for _, row in df.head(limit).iterrows()]


def _latest_record(df: pd.DataFrame) -> dict[str, Any] | None:
    if df is None or df.empty:
        return None
    return _row_to_dict(df.iloc[-1])


def _market_for_code(code: str) -> str:
    if code.startswith("6"):
        return "sh"
    if code.startswith(("0", "3")):
        return "sz"
    return "bj"


def _compact_financials(df: pd.DataFrame) -> dict[str, Any]:
    if df is None or df.empty:
        return {"latest_period": None, "metrics": {}}
    period_cols = [col for col in df.columns if str(col).isdigit()]
    if not period_cols:
        return {"latest_period": None, "metrics": {}}

    latest_period = str(max(period_cols))
    metric_names = ["营业总收入", "归母净利润", "扣非净利润", "经营现金流量净额", "净资产收益率", "每股收益"]
    metrics: dict[str, Any] = {}
    for metric_name in metric_names:
        matched = df[df["指标"].astype(str).str.contains(metric_name, na=False)]
        if matched.empty:
            continue
        metrics[metric_name] = _clean_value(matched.iloc[0][latest_period])
    return {"latest_period": latest_period, "metrics": metrics}


def _compact_history(df: pd.DataFrame) -> dict[str, Any]:
    if df is None or df.empty:
        return {"latest": None, "ma5": None, "ma20": None, "trend": "NO_DATA"}
    closes = pd.to_numeric(df["收盘"], errors="coerce").dropna()
    latest = _row_to_dict(df.iloc[-1])
    ma5 = None if len(closes) < 5 else round(float(closes.tail(5).mean()), 2)
    ma20 = None if len(closes) < 20 else round(float(closes.tail(20).mean()), 2)
    trend = "NO_DATA"
    if ma5 is not None and ma20 is not None:
        trend = "ABOVE_MA20" if ma5 >= ma20 else "BELOW_MA20"
    return {"latest": latest, "ma5": ma5, "ma20": ma20, "trend": trend}


def _compact_northbound_flow(df: pd.DataFrame) -> dict[str, Any] | None:
    if df is None or df.empty:
        return None
    northbound = df[df["资金方向"].astype(str) == "北向"] if "资金方向" in df.columns else df
    if northbound.empty:
        northbound = df
    return {
        "trade_date": _clean_value(northbound.iloc[-1].get("交易日")),
        "net_buy_amount": round(float(pd.to_numeric(northbound.get("成交净买额"), errors="coerce").fillna(0).sum()), 4)
        if "成交净买额" in northbound.columns
        else None,
        "net_inflow": round(float(pd.to_numeric(northbound.get("资金净流入"), errors="coerce").fillna(0).sum()), 4)
        if "资金净流入" in northbound.columns
        else None,
        "rows": _head_records(northbound, 4),
    }


def _portfolio_for_stock(code: str, price: float) -> dict[str, Any]:
    positions = PORTFOLIO.get("positions", {})
    position = positions.get(code, {})
    quantity = float(position.get("quantity") or 0)
    cost = float(position.get("cost") or 0)
    market_value = round(quantity * price, 2)
    profit_pct = None
    if quantity > 0 and cost > 0:
        profit_pct = round((price - cost) / cost * 100, 2)
    return {
        "quantity": quantity,
        "cost": cost,
        "market_value": market_value,
        "profit_pct": profit_pct,
    }


def _fetch_lhb(code: str) -> dict[str, Any]:
    dates = ak.stock_lhb_stock_detail_date_em(symbol=code)
    if dates is None or dates.empty:
        return {"latest_date": None, "buy": [], "sell": []}

    latest_date = str(dates.iloc[0]["交易日"]).replace("-", "")
    buy = ak.stock_lhb_stock_detail_em(symbol=code, date=latest_date, flag="买入")
    sell = ak.stock_lhb_stock_detail_em(symbol=code, date=latest_date, flag="卖出")
    return {
        "latest_date": latest_date,
        "buy": _head_records(buy, 5),
        "sell": _head_records(sell, 5),
    }


def _industry_snapshot(industry_rank: pd.DataFrame, industry: str | None) -> dict[str, Any] | None:
    if not industry or industry_rank is None or industry_rank.empty:
        return None
    matched = industry_rank[industry_rank["板块名称"].astype(str) == industry]
    if matched.empty:
        return None
    return _row_to_dict(matched.iloc[0])


def _industry_fund_snapshot(industry_fund_rank: pd.DataFrame, industry: str | None) -> dict[str, Any] | None:
    if not industry or industry_fund_rank is None or industry_fund_rank.empty:
        return None
    matched = industry_fund_rank[industry_fund_rank["名称"].astype(str) == industry]
    if matched.empty:
        return None
    return _row_to_dict(matched.iloc[0])


def fetch_extended_data(stocks: dict[str, dict[str, Any]], trade_date: str) -> dict[str, Any]:
    logger.info("Fetching extended market and stock data")
    end_date = trade_date.replace("-", "")
    start_date = (datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=HISTORY_DAYS * 2)).strftime("%Y%m%d")

    try:
        with akshare_network_env():
            northbound_flow = ak.stock_hsgt_fund_flow_summary_em()
            industry_rank = ak.stock_board_industry_name_em()
            industry_fund_rank = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流")
    except Exception as exc:
        raise DataFetchError(f"DATA_ERROR: extended market data fetch failed: {exc}") from exc

    result: dict[str, Any] = {
        "northbound_flow": _compact_northbound_flow(northbound_flow),
        "industry_rank_top": _head_records(industry_rank, 5),
        "industry_fund_flow_top": _head_records(industry_fund_rank, 5),
        "portfolio": {
            "cash": float(PORTFOLIO.get("cash") or 0),
            "positions": {},
        },
        "stocks": {},
    }

    for code, stock in stocks.items():
        meta = TARGET_STOCKS.get(code, {})
        industry = meta.get("industry")
        try:
            with akshare_network_env():
                financial = ak.stock_financial_abstract(symbol=code)
                news = ak.stock_news_em(symbol=code)
                research = ak.stock_research_report_em(symbol=code)
                northbound_holding = ak.stock_hsgt_individual_em(symbol=code)
                fund_flow = ak.stock_individual_fund_flow(stock=code, market=_market_for_code(code))
                history = ak.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq",
                )
                lhb = _fetch_lhb(code)
        except Exception as exc:
            raise DataFetchError(f"DATA_ERROR: extended stock data fetch failed for {code}: {exc}") from exc

        holding = _portfolio_for_stock(code, float(stock["price"]))
        result["portfolio"]["positions"][code] = holding
        result["stocks"][code] = {
            "financial": _compact_financials(financial),
            "news": _head_records(news, NEWS_LIMIT),
            "research": _head_records(research, RESEARCH_LIMIT),
            "northbound_holding": _latest_record(northbound_holding),
            "lhb": lhb,
            "fund_flow": _latest_record(fund_flow),
            "industry": _industry_snapshot(industry_rank, industry),
            "industry_fund_flow": _industry_fund_snapshot(industry_fund_rank, industry),
            "history": _compact_history(history),
            "holding": holding,
        }

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sample_stocks = {"601138": {"price": 60.0}, "002475": {"price": 40.0}}
    print(fetch_extended_data(sample_stocks, datetime.now().date().isoformat()))
