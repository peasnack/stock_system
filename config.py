from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
DB_PATH = BASE_DIR / "data" / "stock_system.db"

TIMEZONE = "Asia/Shanghai"
JOB_HOUR = 14
JOB_MINUTE = 50

TARGET_STOCKS = {
    "601138": {
        "name": "工业富联",
        "factor": "科技",
    },
    "002475": {
        "name": "立讯精密",
        "factor": "消费电子",
    },
}

INDEX_CODES = {
    "000001": "上证指数",
    "399001": "深证成指",
    "399006": "创业板指",
}

MARKET_AMOUNT_CHANGE_THRESHOLD = -0.05
STOCK_STRONG_SCORE = 70
STOCK_WEAK_SCORE = 50
HARD_DROP_PCT = -5.0


def ensure_runtime_dirs() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
