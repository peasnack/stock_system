import argparse
import logging
from datetime import datetime
from typing import Any

from config import LOG_DIR, ensure_runtime_dirs
from config import EXTENDED_DATA_ENABLED
from core.extended_fetch import fetch_extended_data
from core.fetch import DataFetchError, get_market_data
from core.market import classify_market
from core.risk import detect_factor_risk
from core.stock import analyze_stocks
from core.strategy import make_decisions
from data.storage import get_previous_market_amount, init_db, save_market_amount, save_run
from notify.wechat import send_wechat_message
from scheduler.job import start_scheduler


def setup_logging() -> None:
    ensure_runtime_dirs()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_DIR / "stock_system.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def _amount_yi(amount: float | None) -> str:
    if amount is None:
        return "无历史数据"
    return f"{amount / 100000000:.2f}亿"


def _pct_change_text(value: float | None) -> str:
    if value is None:
        return "无历史数据"
    return f"{value}%"


def _money_yi(value: float | int | None) -> str:
    if value is None:
        return "无数据"
    return f"{float(value) / 100000000:.2f}亿"


def _native_yi(value: float | int | None) -> str:
    if value is None:
        return "无数据"
    return f"{float(value):.2f}亿"


def _short_text(value: Any, limit: int = 34) -> str:
    text = str(value) if value is not None else "无数据"
    return text if len(text) <= limit else f"{text[:limit]}..."


def _format_extended_lines(payload: dict[str, Any]) -> list[str]:
    extended = payload.get("extended")
    if not extended:
        return ["未启用扩展数据"]

    lines: list[str] = []
    north = extended.get("northbound_flow") or {}
    if north:
        lines.append(
            "北向资金: "
            f"{north.get('trade_date', '最新')}, "
            f"成交净买额={_native_yi(north.get('net_buy_amount'))}, 资金净流入={_native_yi(north.get('net_inflow'))}"
        )

    for code, item in extended.get("stocks", {}).items():
        stock = payload["stocks"][code]
        holding = item.get("holding") or {}
        fund_flow = item.get("fund_flow") or {}
        history = item.get("history") or {}
        financial = item.get("financial") or {}
        industry = item.get("industry") or {}
        industry_flow = item.get("industry_fund_flow") or {}
        lhb = item.get("lhb") or {}
        news = item.get("news") or []
        research = item.get("research") or []

        latest_news = news[0].get("新闻标题") if news else "无新闻"
        latest_research = research[0].get("报告名称") if research else "无研报"
        metrics = financial.get("metrics") or {}
        lines.append(
            f"{stock['name']}({code}) 扩展: "
            f"持仓{holding.get('quantity', 0)}股, 成本{holding.get('cost', 0)}, 盈亏{holding.get('profit_pct')}%; "
            f"主力净流入{_money_yi(fund_flow.get('主力净流入-净额'))}; "
            f"K线{history.get('trend')}, MA5={history.get('ma5')}, MA20={history.get('ma20')}; "
            f"财报{financial.get('latest_period')}, 营收={_money_yi(metrics.get('营业总收入'))}, 归母净利={_money_yi(metrics.get('归母净利润'))}"
        )
        lines.append(
            f"{stock['name']} 信息: "
            f"新闻={_short_text(latest_news)}; 研报={_short_text(latest_research)}; "
            f"龙虎榜最近={lhb.get('latest_date') or '无'}; "
            f"行业={industry.get('板块名称') or '无'}, 行业涨跌={industry.get('涨跌幅')}%, "
            f"行业主力净流入={_money_yi(industry_flow.get('今日主力净流入-净额'))}"
        )
    return lines


def format_report(payload: dict[str, Any]) -> str:
    if payload["status"] == "DATA_ERROR":
        return "\n".join(
            [
                "[市场状态]",
                "DATA_ERROR",
                "[指数数据]",
                "DATA_ERROR",
                "[个股数据]",
                "DATA_ERROR",
                "[风险状态]",
                "DATA_ERROR",
                "[交易建议]",
                "NO_TRADE",
                "[理由]",
                payload["error"],
            ]
        )

    indices = payload["indices"]
    stocks = payload["stocks"]
    decisions = payload["decisions"]
    market = payload["market"]
    risk = payload["risk"]

    index_lines = [
        f"{item['name']}({code}): {item['pct_chg']:.2f}%, 成交额{_amount_yi(item['amount'])}"
        for code, item in indices.items()
    ]
    stock_lines = [
        (
            f"{item['name']}({code}): 涨跌幅{item['pct_chg']:.2f}%, "
            f"成交额{_amount_yi(item['amount'])}, score={item['score']:.2f}, trend={item['trend']}"
        )
        for code, item in stocks.items()
    ]
    decision_lines = [
        f"{stocks[code]['name']}({code}): {decision['action']}"
        for code, decision in decisions.items()
    ]
    reason_lines = []
    reason_lines.append(f"交易日: {payload['trade_date']}")
    reason_lines.append("决策优先级: 个股跌幅超过硬止损线时优先降仓，其次判断市场和同因子风险")
    reason_lines.extend(market["reasons"])
    reason_lines.extend(risk["reasons"])
    for code, decision in decisions.items():
        score_detail = stocks[code].get("score_detail", {})
        score_text = ", ".join(f"{name}={score}" for name, score in score_detail.items())
        reason_lines.append(f"{stocks[code]['name']}: {'; '.join(decision['reasons'])}; 评分明细: {score_text}")

    extended_lines = _format_extended_lines(payload)

    return "\n".join(
        [
            "[市场状态]",
            market["state"],
            f"交易日: {payload['trade_date']}",
            f"两市成交额: {_amount_yi(market['total_amount'])}, 较前次: {_pct_change_text(market['amount_change_pct'])}",
            "[指数数据]",
            *index_lines,
            "[个股数据]",
            *stock_lines,
            "[风险状态]",
            risk["state"],
            "[交易建议]",
            *decision_lines,
            "[扩展数据]",
            *extended_lines,
            "[理由]",
            *reason_lines,
        ]
    )


def run_analysis() -> dict[str, Any]:
    logger = logging.getLogger(__name__)
    init_db()
    logger.info("Stock analysis run started")

    try:
        market_data = get_market_data()
        extended = fetch_extended_data(market_data.stocks, market_data.trade_date) if EXTENDED_DATA_ENABLED else None
        previous_amount = get_previous_market_amount(market_data.trade_date)
        market = classify_market(market_data.indices, market_data.total_amount, previous_amount)
        stocks = analyze_stocks(
            market_data.stocks,
            market_avg_pct=float(market["avg_pct_chg"]),
            market_state=str(market["state"]),
        )
        if extended:
            for code, item in extended["stocks"].items():
                stocks[code]["holding"] = item["holding"]
        risk = detect_factor_risk(stocks, market_data.indices)
        decisions = make_decisions(stocks, str(market["state"]), str(risk["state"]))

        payload = {
            "status": "OK",
            "run_at": datetime.now().isoformat(timespec="seconds"),
            "trade_date": market_data.trade_date,
            "market": market,
            "indices": market_data.indices,
            "stocks": stocks,
            "extended": extended,
            "risk": risk,
            "decisions": decisions,
        }
        report = format_report(payload)
        payload["report"] = report

        save_market_amount(market_data.trade_date, market_data.total_amount)
        save_run(
            status="OK",
            market_state=str(market["state"]),
            risk_state=str(risk["state"]),
            total_amount=market_data.total_amount,
            payload=payload,
        )
        send_wechat_message(report)
        logger.info("Stock analysis run completed")
        return payload

    except DataFetchError as exc:
        logger.exception("Data fetch failed")
        payload = {
            "status": "DATA_ERROR",
            "run_at": datetime.now().isoformat(timespec="seconds"),
            "error": str(exc),
        }
        report = format_report(payload)
        payload["report"] = report
        save_run(
            status="DATA_ERROR",
            market_state=None,
            risk_state=None,
            total_amount=None,
            payload=payload,
        )
        send_wechat_message(report)
        return payload
    except Exception as exc:
        logger.exception("Unexpected analysis error")
        payload = {
            "status": "DATA_ERROR",
            "run_at": datetime.now().isoformat(timespec="seconds"),
            "error": f"DATA_ERROR: unexpected error: {exc}",
        }
        report = format_report(payload)
        payload["report"] = report
        save_run(
            status="DATA_ERROR",
            market_state=None,
            risk_state=None,
            total_amount=None,
            payload=payload,
        )
        send_wechat_message(report)
        return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="A-share investment decision system MVP")
    parser.add_argument("--once", action="store_true", help="run analysis once and exit")
    parser.add_argument("--run-now", action="store_true", help="run once before starting scheduler")
    args = parser.parse_args()

    setup_logging()
    ensure_runtime_dirs()
    init_db()

    if args.once:
        payload = run_analysis()
        print(payload["report"])
        return

    if args.run_now:
        run_analysis()

    start_scheduler(run_analysis)


if __name__ == "__main__":
    main()
