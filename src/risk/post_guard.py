import copy
from typing import Any


SAFE_ACTIONS_WHEN_DATA_INCOMPLETE = {"NO_TRADE", "HOLD", "WARNING"}
BUY_ACTIONS = {"BUY", "ADD", "INCREASE"}
SWITCH_ACTIONS = {"SWITCH", "ROTATE", "换股"}


def _guard_decision(decision: dict[str, Any], precheck: dict[str, Any]) -> dict[str, Any]:
    guarded = dict(decision)
    action = str(guarded.get("action", "NO_TRADE")).upper()
    notes: list[str] = []

    if not precheck.get("data_complete", False) and action not in SAFE_ACTIONS_WHEN_DATA_INCOMPLETE:
        action = "NO_TRADE"
        notes.append("数据不完整，仅允许 NO_TRADE/HOLD/WARNING")

    if not precheck.get("allow_buy", False) and action in BUY_ACTIONS:
        action = "NO_TRADE"
        notes.append("本地风控禁止买入或加仓")

    if not precheck.get("allow_switch", False) and action in SWITCH_ACTIONS:
        action = "NO_TRADE"
        notes.append("本地风控禁止换股")

    if (
        action == "SELL_ALL"
        and not precheck.get("hard_stop_triggered", False)
        and not precheck.get("core_logic_invalidated", False)
    ):
        action = "REDUCE_WATCH"
        notes.append("未触发本地硬止损或核心逻辑失效，不允许清仓")

    guarded["action"] = action
    if notes:
        original_reason = str(guarded.get("reason") or "")
        guarded["reason"] = "；".join([part for part in [original_reason, *notes] if part])
        guarded["guard_notes"] = notes
    return guarded


def apply_post_guard(ai_result: dict[str, Any], local_risk_precheck: dict[str, Any]) -> dict[str, Any]:
    original = copy.deepcopy(ai_result)
    guarded = copy.deepcopy(ai_result)
    decisions = guarded.get("decisions")
    if not isinstance(decisions, list):
        decisions = []
    guarded["decisions"] = [
        _guard_decision(decision, local_risk_precheck)
        for decision in decisions
        if isinstance(decision, dict)
    ]

    if not local_risk_precheck.get("allow_buy", False):
        guarded["allow_buy"] = False
    if not local_risk_precheck.get("allow_switch", False):
        guarded["allow_switch"] = False
    if not local_risk_precheck.get("hard_stop_triggered", False):
        guarded["hard_stop_triggered"] = False

    guard_notes = list(guarded.get("guard_notes") or [])
    if original != guarded:
        guard_notes.append("AI 输出已按本地二次风控修正")
    guarded["guard_notes"] = guard_notes

    return {
        "status": "OK",
        "ai_original": original,
        "decision": guarded,
        "local_risk_precheck": local_risk_precheck,
    }
