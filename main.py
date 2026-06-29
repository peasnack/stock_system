import argparse
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from config import CONTEXT_DIR, DECISION_DIR, HARD_DROP_PCT, LOG_DIR, REPORT_DIR, ensure_runtime_dirs
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
from src.ai.openai_client import call_openai_decision
from src.reports.formatter import format_decision_markdown
from src.risk.post_guard import apply_post_guard


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


def _artifact_stamp(run_at: datetime) -> str:
    return run_at.strftime("%Y-%m-%d_%H%M")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _public_error(error: Any, limit: int = 260) -> str:
    text = str(error)
    text = re.sub(r"https?://\S+", "[url]", text)
    text = re.sub(r"/api/\S+", "/api/[query]", text)
    text = " ".join(text.split())
    return text if len(text) <= limit else f"{text[:limit]}..."


def _collect_data_gaps(payload: dict[str, Any]) -> list[str]:
    if payload.get("status") != "OK":
        return [_public_error(payload.get("error", "DATA_ERROR"))]
    gaps: list[str] = []
    extended = payload.get("extended")
    if not extended:
        gaps.append("extended_data_missing")
        return gaps
    for code, item in (extended.get("stocks") or {}).items():
        if not item.get("news"):
            gaps.append(f"{code}_news_missing")
        if not item.get("research"):
            gaps.append(f"{code}_research_missing")
        if not item.get("history", {}).get("latest"):
            gaps.append(f"{code}_history_missing")
    return gaps


def _build_local_risk_precheck(payload: dict[str, Any], data_gaps: list[str]) -> dict[str, Any]:
    if payload.get("status") != "OK":
        return {
            "allow_buy": False,
            "allow_switch": False,
            "hard_stop_triggered": False,
            "core_logic_invalidated": False,
            "data_complete": False,
            "reasons": [str(payload.get("error", "DATA_ERROR"))],
        }

    market = payload.get("market") or {}
    risk = payload.get("risk") or {}
    data_complete = not data_gaps
    allow_buy = data_complete and market.get("state") != "WEAK" and bool(risk.get("allow_add", False))
    reasons: list[str] = []
    if not data_complete:
        reasons.append("存在数据缺口，禁止买入、加仓、换股")
    if market.get("state") == "WEAK":
        reasons.append("弱市场环境禁止买入或加仓")
    if not risk.get("allow_add", False):
        reasons.append("同因子风险禁止买入或加仓")

    return {
        "allow_buy": allow_buy,
        "allow_switch": False,
        "hard_stop_triggered": False,
        "core_logic_invalidated": False,
        "data_complete": data_complete,
        "hard_drop_pct": HARD_DROP_PCT,
        "reasons": reasons or ["本地预检未发现硬性禁止买入条件，但 MVP2 默认禁止换股"],
    }


def _market_context(payload: dict[str, Any], mode: str) -> dict[str, Any]:
    data_gaps = _collect_data_gaps(payload)
    context = {
        "mode": mode,
        "status": payload.get("status"),
        "run_at": payload.get("run_at"),
        "trade_date": payload.get("trade_date"),
        "market": payload.get("market"),
        "indices": payload.get("indices"),
        "stocks": payload.get("stocks"),
        "extended": payload.get("extended"),
        "risk": payload.get("risk"),
        "local_decisions": payload.get("decisions"),
        "data_gaps": data_gaps,
    }
    context["local_risk_precheck"] = _build_local_risk_precheck(payload, data_gaps)
    return context


def _system_state(payload: dict[str, Any]) -> str:
    if payload.get("status") != "OK":
        return "S4"
    risk_state = (payload.get("risk") or {}).get("state")
    market_state = (payload.get("market") or {}).get("state")
    if risk_state == "RISK_ON" or market_state == "WEAK":
        return "S3"
    if market_state == "STRONG":
        return "S1"
    return "S2"


def _local_decision_payload(payload: dict[str, Any], context: dict[str, Any], ai_error: str | None = None) -> dict[str, Any]:
    stocks = payload.get("stocks") or {}
    decisions = []
    for code, decision in (payload.get("decisions") or {}).items():
        stock = stocks.get(code, {})
        decisions.append(
            {
                "code": code,
                "name": stock.get("name", code),
                "action": decision.get("action", "NO_TRADE"),
                "hands": 0,
                "condition": "本地规则",
                "reason": "；".join(decision.get("reasons") or []),
            }
        )
    if not decisions:
        decisions = [
            {
                "code": "",
                "name": "全局",
                "action": "NO_TRADE",
                "hands": 0,
                "condition": "DATA_ERROR",
                "reason": _public_error(payload.get("error", "DATA_ERROR")),
            }
        ]

    precheck = context["local_risk_precheck"]
    conclusion = "AI_ERROR，按本地风控执行" if ai_error else "按本地规则执行"
    return {
        "system_state": _system_state(payload),
        "portfolio_conclusion": conclusion,
        "allow_buy": bool(precheck.get("allow_buy", False)),
        "allow_switch": bool(precheck.get("allow_switch", False)),
        "hard_stop_triggered": bool(precheck.get("hard_stop_triggered", False)),
        "same_factor_risk": (payload.get("risk") or {}).get("state") == "RISK_ON",
        "decisions": decisions,
        "data_gaps": context.get("data_gaps") or [],
        "wechat_summary": conclusion,
    }


def _save_ai_artifacts(
    *,
    run_at: datetime,
    context: dict[str, Any],
    ai_raw: dict[str, Any],
    guarded: dict[str, Any],
    report: str,
) -> dict[str, str]:
    stamp = _artifact_stamp(run_at)
    paths = {
        "context": CONTEXT_DIR / f"{stamp}_market_context.json",
        "ai_raw": DECISION_DIR / f"{stamp}_ai_raw.json",
        "guarded": DECISION_DIR / f"{stamp}_decision_guarded.json",
        "report": REPORT_DIR / f"{stamp}_report.md",
    }
    _write_json(paths["context"], context)
    _write_json(paths["ai_raw"], ai_raw)
    _write_json(paths["guarded"], guarded)
    _write_text(paths["report"], report)
    return {name: str(path) for name, path in paths.items()}


def _notify_or_print(report: str, *, notify: bool, dry_run: bool) -> bool:
    if dry_run or not notify:
        print(report)
        return True
    return send_wechat_message(report)


def run_analysis(mode: str = "late", use_ai: bool = False, notify: bool = True, dry_run: bool = False) -> dict[str, Any]:
    logger = logging.getLogger(__name__)
    init_db()
    logger.info("Stock analysis run started")
    run_at = datetime.now()

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
            "run_at": run_at.isoformat(timespec="seconds"),
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
        context = _market_context(payload, mode)
        if use_ai:
            ai_raw = call_openai_decision(context)
            ai_decision = (
                ai_raw["decision"]
                if ai_raw.get("status") == "OK" and isinstance(ai_raw.get("decision"), dict)
                else _local_decision_payload(payload, context, str(ai_raw.get("error", "AI_ERROR")))
            )
        else:
            ai_raw = {"status": "SKIPPED", "reason": "AI disabled"}
            ai_decision = _local_decision_payload(payload, context)
        guarded = apply_post_guard(ai_decision, context["local_risk_precheck"])
        decision_report = format_decision_markdown(guarded, context)
        artifact_paths = _save_ai_artifacts(
            run_at=run_at,
            context=context,
            ai_raw=ai_raw,
            guarded=guarded,
            report=decision_report,
        )
        payload["market_context"] = context
        payload["ai_raw"] = ai_raw
        payload["decision_guarded"] = guarded
        payload["decision_report"] = decision_report
        payload["artifact_paths"] = artifact_paths
        _notify_or_print(decision_report, notify=notify, dry_run=dry_run)
        logger.info("Stock analysis run completed")
        return payload

    except DataFetchError as exc:
        logger.exception("Data fetch failed")
        payload = {
            "status": "DATA_ERROR",
            "run_at": run_at.isoformat(timespec="seconds"),
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
        context = _market_context(payload, mode)
        ai_raw = {"status": "AI_ERROR", "error": "AI_ERROR: skipped because local data fetch failed"}
        guarded = apply_post_guard(
            _local_decision_payload(payload, context, "AI_ERROR: skipped because local data fetch failed"),
            context["local_risk_precheck"],
        )
        decision_report = format_decision_markdown(guarded, context)
        payload["market_context"] = context
        payload["ai_raw"] = ai_raw
        payload["decision_guarded"] = guarded
        payload["decision_report"] = decision_report
        payload["artifact_paths"] = _save_ai_artifacts(
            run_at=run_at,
            context=context,
            ai_raw=ai_raw,
            guarded=guarded,
            report=decision_report,
        )
        _notify_or_print(decision_report, notify=notify, dry_run=dry_run)
        return payload
    except Exception as exc:
        logger.exception("Unexpected analysis error")
        payload = {
            "status": "DATA_ERROR",
            "run_at": run_at.isoformat(timespec="seconds"),
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
        context = _market_context(payload, mode)
        ai_raw = {"status": "AI_ERROR", "error": "AI_ERROR: skipped because local analysis failed"}
        guarded = apply_post_guard(
            _local_decision_payload(payload, context, "AI_ERROR: skipped because local analysis failed"),
            context["local_risk_precheck"],
        )
        decision_report = format_decision_markdown(guarded, context)
        payload["market_context"] = context
        payload["ai_raw"] = ai_raw
        payload["decision_guarded"] = guarded
        payload["decision_report"] = decision_report
        payload["artifact_paths"] = _save_ai_artifacts(
            run_at=run_at,
            context=context,
            ai_raw=ai_raw,
            guarded=guarded,
            report=decision_report,
        )
        _notify_or_print(decision_report, notify=notify, dry_run=dry_run)
        return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="A-share investment decision system MVP")
    parser.add_argument("--once", action="store_true", help="run analysis once and exit")
    parser.add_argument("--run-now", action="store_true", help="run once before starting scheduler")
    parser.add_argument("--mode", choices=["late", "close", "noon"], default="late", help="analysis mode")
    parser.add_argument("--ai", action="store_true", help="call OpenAI decision module")
    parser.add_argument("--notify", action="store_true", help="send notification")
    parser.add_argument("--dry-run", action="store_true", help="print report without notification")
    args = parser.parse_args()

    setup_logging()
    ensure_runtime_dirs()
    init_db()

    if args.once or args.dry_run:
        payload = run_analysis(mode=args.mode, use_ai=args.ai, notify=args.notify or not args.dry_run, dry_run=args.dry_run)
        if not args.dry_run:
            print(payload.get("decision_report") or payload["report"])
        return

    if args.run_now:
        run_analysis(mode=args.mode, use_ai=args.ai, notify=args.notify or not args.dry_run, dry_run=args.dry_run)

    start_scheduler(lambda: run_analysis(mode=args.mode, use_ai=args.ai, notify=True, dry_run=False))


if __name__ == "__main__":
    main()
