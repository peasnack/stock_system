import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import HARD_DROP_PCT


def detect_factor_risk(stocks: dict[str, dict], indices: dict[str, dict]) -> dict:
    stock_drops = [float(item["pct_chg"]) for item in stocks.values()]
    index_down = any(float(item["pct_chg"]) < 0 for item in indices.values())
    same_factor_drop = len(stock_drops) >= 2 and all(pct <= HARD_DROP_PCT for pct in stock_drops)

    if same_factor_drop and index_down:
        return {
            "state": "RISK_ON",
            "allow_add": False,
            "reasons": ["两只目标股同跌超过5%，且指数下跌，同因子风险释放"],
        }

    return {
        "state": "RISK_OFF",
        "allow_add": True,
        "reasons": ["未触发同因子风险"],
    }


if __name__ == "__main__":
    print(
        detect_factor_risk(
            {"a": {"pct_chg": -5.5}, "b": {"pct_chg": -6.0}},
            {"i": {"pct_chg": -1.0}},
        )
    )
