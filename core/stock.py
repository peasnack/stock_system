import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import STOCK_STRONG_SCORE


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _score_pct_chg(pct_chg: float) -> float:
    return _clamp((pct_chg + 6.0) / 12.0 * 100.0)


def _score_amount(amount: float, peer_amounts: list[float]) -> float:
    if not peer_amounts or max(peer_amounts) <= 0:
        return 50.0
    return _clamp(amount / max(peer_amounts) * 100.0)


def _score_relative_strength(stock_pct: float, market_avg_pct: float) -> float:
    diff = stock_pct - market_avg_pct
    return _clamp(50.0 + diff * 10.0)


def _score_intraday(stock: dict) -> float:
    high = float(stock["high"])
    low = float(stock["low"])
    price = float(stock["price"])
    open_price = float(stock["open"])
    if high <= low:
        position_score = 50.0
    else:
        position_score = (price - low) / (high - low) * 100.0
    direction_bonus = 10.0 if price >= open_price else -10.0
    return _clamp(position_score + direction_bonus)


def _score_factor(factor: str, market_state: str) -> float:
    base_by_factor = {
        "科技": 70.0,
        "消费电子": 65.0,
    }
    base = base_by_factor.get(factor, 55.0)
    if market_state == "STRONG":
        return _clamp(base + 10.0)
    if market_state == "WEAK":
        return _clamp(base - 20.0)
    return base


def analyze_stocks(
    stocks: dict[str, dict],
    market_avg_pct: float,
    market_state: str,
) -> dict[str, dict]:
    peer_amounts = [float(stock["amount"]) for stock in stocks.values()]
    result: dict[str, dict] = {}

    for code, stock in stocks.items():
        pct_score = _score_pct_chg(float(stock["pct_chg"]))
        amount_score = _score_amount(float(stock["amount"]), peer_amounts)
        relative_score = _score_relative_strength(float(stock["pct_chg"]), market_avg_pct)
        intraday_score = _score_intraday(stock)
        factor_score = _score_factor(str(stock["factor"]), market_state)

        score = (
            pct_score * 0.30
            + amount_score * 0.20
            + relative_score * 0.20
            + intraday_score * 0.20
            + factor_score * 0.10
        )
        trend = "强" if score >= STOCK_STRONG_SCORE else "弱"
        result[code] = {
            **stock,
            "score": round(score, 2),
            "trend": trend,
            "score_detail": {
                "pct_chg": round(pct_score, 2),
                "amount": round(amount_score, 2),
                "relative": round(relative_score, 2),
                "intraday": round(intraday_score, 2),
                "factor": round(factor_score, 2),
            },
        }

    return result


if __name__ == "__main__":
    sample = {
        "601138": {"name": "工业富联", "pct_chg": 2.0, "amount": 100, "high": 10.5, "low": 9.5, "price": 10.3, "open": 9.8, "factor": "科技"},
        "002475": {"name": "立讯精密", "pct_chg": -1.0, "amount": 80, "high": 20.5, "low": 19.5, "price": 19.8, "open": 20.0, "factor": "消费电子"},
    }
    print(analyze_stocks(sample, 0.5, "NEUTRAL"))
