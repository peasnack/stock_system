from typing import Any


def _money(value: Any) -> str:
    if value is None:
        return "无数据"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def _position_lines(context: dict[str, Any]) -> list[str]:
    extended = context.get("extended") or {}
    portfolio = extended.get("portfolio") or context.get("portfolio") or {}
    positions = portfolio.get("positions") or {}
    stocks = context.get("stocks") or {}
    if not positions:
        return ["- 无持仓配置"]
    lines = []
    for code, holding in positions.items():
        name = stocks.get(code, {}).get("name", code)
        lines.append(
            f"- {name}({code}): {holding.get('quantity', 0)}股, "
            f"成本{holding.get('cost', 0)}, 盈亏{holding.get('profit_pct', '无数据')}%"
        )
    return lines


def _decision_lines(decision: dict[str, Any]) -> list[str]:
    items = decision.get("decisions") or []
    if not items:
        return ["- 无逐股建议"]
    lines = []
    for item in items:
        lines.append(
            f"- {item.get('name', item.get('code', '未知'))}({item.get('code', '')}): "
            f"{item.get('action', 'NO_TRADE')}, {item.get('condition', '')} {item.get('reason', '')}".strip()
        )
    return lines


def format_decision_markdown(decision_payload: dict[str, Any], market_context: dict[str, Any]) -> str:
    decision = decision_payload.get("decision") or {}
    precheck = decision_payload.get("local_risk_precheck") or market_context.get("local_risk_precheck") or {}
    market = market_context.get("market") or {}
    risk = market_context.get("risk") or {}
    data_gaps = decision.get("data_gaps") or market_context.get("data_gaps") or []
    guard_notes = decision.get("guard_notes") or decision_payload.get("guard_notes") or []

    data_gap_lines = [f"- {gap}" for gap in data_gaps] if data_gaps else ["- 无"]

    lines = [
        "## A股投资决策",
        f"- 运行模式: {market_context.get('mode', 'late')}",
        f"- 交易日: {market_context.get('trade_date', '无数据')}",
        f"- 市场状态: {market.get('state', 'DATA_ERROR')}",
        f"- 系统状态: {decision.get('system_state', 'LOCAL_RULE')}",
        f"- 风险状态: {risk.get('state', 'DATA_ERROR')}",
        f"- 两市成交额: {_money(market.get('total_amount'))}",
        "",
        "### 持仓与盈亏",
        *_position_lines(market_context),
        "",
        "### 每只股票建议",
        *_decision_lines(decision),
        "",
        "### 禁止事项",
        f"- 允许买入/加仓: {bool(decision.get('allow_buy', precheck.get('allow_buy', False)))}",
        f"- 允许换股: {bool(decision.get('allow_switch', precheck.get('allow_switch', False)))}",
        f"- 自动下单: False",
        "",
        "### 数据缺口",
        *data_gap_lines,
        "",
        "### 最终结论",
        decision.get("wechat_summary")
        or decision.get("portfolio_conclusion")
        or "AI_ERROR，按本地风控执行",
    ]
    if guard_notes:
        lines.extend(["", "### 二次风控", *(f"- {note}" for note in guard_notes)])
    return "\n".join(str(line) for line in lines)
