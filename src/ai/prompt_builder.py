import json
from typing import Any


SYSTEM_PROMPT = """你是A股投资决策分析助手，只能给本地系统提供分析建议。
必须遵守：
1. 不允许越过本地硬风控，本地风控禁止的买入、加仓、换股必须禁止。
2. 数据缺口时禁止买入、加仓、换股。
3. 硬止损只按价格判断，不能把情绪、新闻或单日涨跌幅直接当作硬止损。
4. 单日跌幅>5%只能是 WARNING 或 REDUCE_WATCH，不能直接当硬止损。
5. 不允许建议自动下单，不允许接券商交易接口。
6. 必须返回严格 JSON，不要输出 Markdown、解释性前后缀或代码块。
"""


JSON_CONTRACT = {
    "system_state": "S1/S2/S3/S4",
    "portfolio_conclusion": "...",
    "allow_buy": False,
    "allow_switch": False,
    "hard_stop_triggered": False,
    "same_factor_risk": True,
    "decisions": [
        {
            "code": "601138",
            "name": "工业富联",
            "action": "HOLD/NO_TRADE/WARNING/REDUCE_WATCH/REDUCE/SELL_ALL",
            "hands": 0,
            "condition": "...",
            "reason": "...",
        }
    ],
    "data_gaps": [],
    "wechat_summary": "...",
}


def build_messages(market_context: dict[str, Any]) -> tuple[str, str]:
    user_prompt = "\n".join(
        [
            "请基于以下 market_context 进行 Prompt 5.1 投资分析。",
            "返回 JSON 必须完全符合这个字段结构，字段名不可缺失：",
            json.dumps(JSON_CONTRACT, ensure_ascii=False, indent=2),
            "market_context:",
            json.dumps(market_context, ensure_ascii=False, default=str),
        ]
    )
    return SYSTEM_PROMPT, user_prompt
