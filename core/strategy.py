import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import HARD_DROP_PCT, STOCK_STRONG_SCORE, STOCK_WEAK_SCORE


def _holding(stock: dict) -> dict:
    return dict(stock.get("holding") or {})


def decide_for_stock(stock: dict, market_state: str, risk_state: str) -> dict:
    reasons: list[str] = []
    pct_chg = float(stock["pct_chg"])
    score = float(stock["score"])
    holding = _holding(stock)
    quantity = float(holding.get("quantity") or 0)

    if pct_chg <= HARD_DROP_PCT:
        if quantity <= 0:
            reasons.append("个股跌幅超过5%，但当前无持仓，不执行降仓")
            return {"action": "NO_TRADE", "reasons": reasons}
        reasons.append("个股跌幅超过5%，优先降仓")
        return {"action": "REDUCE", "reasons": reasons}

    if market_state == "WEAK":
        reasons.append("弱市场环境，不允许交易或加仓")
        return {"action": "NO_TRADE", "reasons": reasons}

    if risk_state == "RISK_ON":
        reasons.append("同因子风险释放，禁止买入")
        if score < STOCK_WEAK_SCORE:
            if quantity <= 0:
                reasons.append("个股评分低于50，但当前无持仓，不执行降仓")
                return {"action": "NO_TRADE", "reasons": reasons}
            reasons.append("个股评分低于50，建议降仓")
            return {"action": "REDUCE", "reasons": reasons}
        return {"action": "HOLD", "reasons": reasons}

    if score >= STOCK_STRONG_SCORE and market_state == "STRONG":
        reasons.append("强市场且个股评分强")
        return {"action": "BUY", "reasons": reasons}

    if score < STOCK_WEAK_SCORE:
        reasons.append("个股评分低于50，趋势偏弱")
        action = "REDUCE" if pct_chg < 0 and quantity > 0 else "HOLD"
        return {"action": action, "reasons": reasons}

    reasons.append("市场或个股未形成明确买卖信号")
    return {"action": "HOLD", "reasons": reasons}


def make_decisions(stocks: dict[str, dict], market_state: str, risk_state: str) -> dict[str, dict]:
    return {code: decide_for_stock(stock, market_state, risk_state) for code, stock in stocks.items()}


if __name__ == "__main__":
    print(decide_for_stock({"pct_chg": 1.2, "score": 75}, "STRONG", "RISK_OFF"))
