import logging
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import akshare as ak
import pandas as pd

from config import INDEX_CODES, TARGET_STOCKS

logger = logging.getLogger(__name__)


class DataFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class MarketData:
    trade_date: str
    indices: dict[str, dict[str, Any]]
    stocks: dict[str, dict[str, Any]]
    total_amount: float


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str:
    for col in candidates:
        if col in df.columns:
            return col
    raise DataFetchError(f"DATA_ERROR: missing required columns {candidates}, actual={list(df.columns)}")


def _to_float(value: Any, default: float | None = None) -> float:
    if pd.isna(value):
        if default is None:
            raise DataFetchError("DATA_ERROR: numeric field is NaN")
        return default
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        if default is None:
            raise DataFetchError(f"DATA_ERROR: cannot parse numeric value {value!r}") from exc
        return default


def _code_key(value: Any) -> str:
    digits = re.sub(r"\D", "", str(value))
    if len(digits) < 6:
        return digits.zfill(6)
    return digits[-6:]


def _code_series(series: pd.Series) -> pd.Series:
    return series.astype(str).map(_code_key)


def _normalize_spot_row(row: pd.Series, code_col: str, name_col: str) -> dict[str, Any]:
    return {
        "code": _code_key(row[code_col]),
        "name": str(row[name_col]),
        "price": _to_float(row[_find_col(row.to_frame().T, ["最新价", "最新", "收盘"])]),
        "pct_chg": _to_float(row[_find_col(row.to_frame().T, ["涨跌幅", "涨幅"])]),
        "amount": _to_float(row[_find_col(row.to_frame().T, ["成交额"])]),
        "high": _to_float(row[_find_col(row.to_frame().T, ["最高"])]),
        "low": _to_float(row[_find_col(row.to_frame().T, ["最低"])]),
        "open": _to_float(row[_find_col(row.to_frame().T, ["今开", "开盘"])]),
        "prev_close": _to_float(row[_find_col(row.to_frame().T, ["昨收"])]),
    }


def fetch_stock_spot() -> pd.DataFrame:
    logger.info("Fetching A-share spot data by akshare.stock_zh_a_spot_em")
    try:
        df = ak.stock_zh_a_spot_em()
    except Exception as exc:
        raise DataFetchError(f"DATA_ERROR: stock_zh_a_spot_em failed: {exc}") from exc
    if df is None or df.empty:
        raise DataFetchError("DATA_ERROR: stock_zh_a_spot_em returned empty data")
    return df


def fetch_index_spot() -> pd.DataFrame:
    logger.info("Fetching index data by akshare.stock_zh_index_spot_sina")
    try:
        df = ak.stock_zh_index_spot_sina()
    except Exception as exc:
        logger.warning("stock_zh_index_spot_sina failed, falling back to stock_zh_index_spot_em: %s", exc)
        try:
            df = ak.stock_zh_index_spot_em()
        except Exception as fallback_exc:
            raise DataFetchError(
                f"DATA_ERROR: stock_zh_index_spot_sina and stock_zh_index_spot_em failed: "
                f"{exc}; {fallback_exc}"
            ) from fallback_exc
    if df is None or df.empty:
        raise DataFetchError("DATA_ERROR: index spot api returned empty data")
    return df


def get_market_data() -> MarketData:
    stock_df = fetch_stock_spot()
    index_df = fetch_index_spot()

    stock_code_col = _find_col(stock_df, ["代码"])
    stock_name_col = _find_col(stock_df, ["名称"])
    index_code_col = _find_col(index_df, ["代码"])
    index_name_col = _find_col(index_df, ["名称"])
    stock_amount_col = _find_col(stock_df, ["成交额"])

    indices: dict[str, dict[str, Any]] = {}
    for code, name in INDEX_CODES.items():
        matched = index_df[_code_series(index_df[index_code_col]) == code]
        if matched.empty:
            raise DataFetchError(f"DATA_ERROR: missing index {name}({code})")
        indices[code] = _normalize_spot_row(matched.iloc[0], index_code_col, index_name_col)

    stocks: dict[str, dict[str, Any]] = {}
    for code, meta in TARGET_STOCKS.items():
        matched = stock_df[_code_series(stock_df[stock_code_col]) == code]
        if matched.empty:
            raise DataFetchError(f"DATA_ERROR: missing stock {meta['name']}({code})")
        item = _normalize_spot_row(matched.iloc[0], stock_code_col, stock_name_col)
        item["factor"] = meta["factor"]
        stocks[code] = item

    tradable = stock_df[_code_series(stock_df[stock_code_col]).str.match(r"^(0|3|6)")]
    total_amount = float(pd.to_numeric(tradable[stock_amount_col], errors="coerce").fillna(0).sum())
    if total_amount <= 0:
        raise DataFetchError("DATA_ERROR: invalid total market amount")

    return MarketData(
        trade_date=date.today().isoformat(),
        indices=indices,
        stocks=stocks,
        total_amount=total_amount,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    data = get_market_data()
    print(data)
