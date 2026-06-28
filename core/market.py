import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import MARKET_AMOUNT_CHANGE_THRESHOLD


def classify_market(
    indices: dict[str, dict],
    total_amount: float,
    previous_total_amount: float | None,
) -> dict:
    pct_changes = [float(item["pct_chg"]) for item in indices.values()]
    avg_pct = sum(pct_changes) / len(pct_changes)
    all_down_over_2 = all(pct < -2.0 for pct in pct_changes)
    all_up = all(pct > 0 for pct in pct_changes)
    any_down = any(pct < 0 for pct in pct_changes)

    amount_change_pct = None
    amount_down = False
    amount_up = False
    if previous_total_amount and previous_total_amount > 0:
        amount_change_pct = (total_amount - previous_total_amount) / previous_total_amount
        amount_down = amount_change_pct <= MARKET_AMOUNT_CHANGE_THRESHOLD
        amount_up = amount_change_pct > 0.03

    reasons: list[str] = []
    if all_down_over_2:
        state = "WEAK"
        reasons.append("三大指数全部下跌超过2%")
    elif amount_down and any_down:
        state = "WEAK"
        reasons.append("两市成交额下降且指数下跌")
    elif all_up and amount_up:
        state = "STRONG"
        reasons.append("三大指数上涨且成交额放量")
    elif avg_pct > 0.5 and (amount_up or previous_total_amount is None):
        state = "STRONG"
        reasons.append("指数整体上涨，市场偏强")
    else:
        state = "NEUTRAL"
        reasons.append("指数小幅波动或成交未显著放量")

    return {
        "state": state,
        "avg_pct_chg": round(avg_pct, 3),
        "total_amount": total_amount,
        "previous_total_amount": previous_total_amount,
        "amount_change_pct": None if amount_change_pct is None else round(amount_change_pct * 100, 2),
        "reasons": reasons,
    }


if __name__ == "__main__":
    sample = {
        "000001": {"pct_chg": 1.0},
        "399001": {"pct_chg": 1.2},
        "399006": {"pct_chg": 1.8},
    }
    print(classify_market(sample, 100.0, 90.0))
