import json
import os
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
DB_PATH = BASE_DIR / "data" / "stock_system.db"
APP_CONFIG_PATH = BASE_DIR / "app_config.json"
CONTEXT_DIR = BASE_DIR / "data" / "context"
DECISION_DIR = BASE_DIR / "data" / "decision"
REPORT_DIR = BASE_DIR / "data" / "reports"

DEFAULT_CONFIG: dict[str, Any] = {
    "timezone": "Asia/Shanghai",
    "job": {
        "hour": 14,
        "minute": 50,
    },
    "target_stocks": {
        "601138": {
            "name": "工业富联",
            "factor": "科技",
            "industry": "消费电子",
        },
        "002475": {
            "name": "立讯精密",
            "factor": "消费电子",
            "industry": "消费电子",
        },
    },
    "index_codes": {
        "000001": "上证指数",
        "399001": "深证成指",
        "399006": "创业板指",
    },
    "thresholds": {
        "market_amount_change": -0.05,
        "stock_strong_score": 70,
        "stock_weak_score": 50,
        "hard_drop_pct": -5.0,
    },
    "notification": {
        "enabled": False,
        "channel": "mock",
        "webhook_url": "",
        "timeout_seconds": 10,
        "linux_wechat_target": "文件传输助手",
    },
    "portfolio": {
        "cash": 0,
        "positions": {
            "601138": {
                "quantity": 0,
                "cost": 0,
            },
            "002475": {
                "quantity": 0,
                "cost": 0,
            },
        },
    },
    "extended_data": {
        "enabled": True,
        "history_days": 30,
        "news_limit": 3,
        "research_limit": 3,
    },
    "ai": {
        "model": "gpt-4o-mini",
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_json_config() -> dict[str, Any]:
    if not APP_CONFIG_PATH.exists():
        return {}
    with APP_CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        data = json.load(config_file)
    if not isinstance(data, dict):
        raise ValueError(f"{APP_CONFIG_PATH} must contain a JSON object")
    return data


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


APP_CONFIG = _deep_merge(DEFAULT_CONFIG, _load_json_config())

TIMEZONE = str(APP_CONFIG["timezone"])
JOB_HOUR = int(APP_CONFIG["job"]["hour"])
JOB_MINUTE = int(APP_CONFIG["job"]["minute"])

TARGET_STOCKS = APP_CONFIG["target_stocks"]
INDEX_CODES = APP_CONFIG["index_codes"]

MARKET_AMOUNT_CHANGE_THRESHOLD = float(APP_CONFIG["thresholds"]["market_amount_change"])
STOCK_STRONG_SCORE = float(APP_CONFIG["thresholds"]["stock_strong_score"])
STOCK_WEAK_SCORE = float(APP_CONFIG["thresholds"]["stock_weak_score"])
HARD_DROP_PCT = float(APP_CONFIG["thresholds"]["hard_drop_pct"])

NOTIFY_ENABLED = _env_bool("NOTIFY_ENABLED", bool(APP_CONFIG["notification"]["enabled"]))
NOTIFY_CHANNEL = os.getenv("NOTIFY_CHANNEL", str(APP_CONFIG["notification"]["channel"]))
WECHAT_WEBHOOK_URL = os.getenv("WECHAT_WEBHOOK_URL", str(APP_CONFIG["notification"]["webhook_url"]))
NOTIFY_TIMEOUT_SECONDS = int(APP_CONFIG["notification"]["timeout_seconds"])
LINUX_WECHAT_TARGET = os.getenv(
    "LINUX_WECHAT_TARGET",
    str(APP_CONFIG["notification"]["linux_wechat_target"]),
)
PORTFOLIO = APP_CONFIG["portfolio"]
EXTENDED_DATA_ENABLED = _env_bool("EXTENDED_DATA_ENABLED", bool(APP_CONFIG["extended_data"]["enabled"]))
HISTORY_DAYS = int(APP_CONFIG["extended_data"]["history_days"])
NEWS_LIMIT = int(APP_CONFIG["extended_data"]["news_limit"])
RESEARCH_LIMIT = int(APP_CONFIG["extended_data"]["research_limit"])
OPENAI_MODEL = os.getenv("OPENAI_MODEL", str(APP_CONFIG["ai"]["model"]))


def ensure_runtime_dirs() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    DECISION_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
