import json
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import DB_PATH, ensure_runtime_dirs


@contextmanager
def get_conn(db_path: Path = DB_PATH):
    ensure_runtime_dirs()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS market_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at TEXT NOT NULL,
                status TEXT NOT NULL,
                market_state TEXT,
                risk_state TEXT,
                total_amount REAL,
                payload TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS market_amount_history (
                trade_date TEXT PRIMARY KEY,
                total_amount REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def save_market_amount(trade_date: str, total_amount: float) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO market_amount_history (trade_date, total_amount, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(trade_date) DO UPDATE SET
                total_amount = excluded.total_amount,
                created_at = excluded.created_at
            """,
            (trade_date, total_amount, datetime.now().isoformat(timespec="seconds")),
        )


def get_previous_market_amount(current_trade_date: str) -> float | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT total_amount
            FROM market_amount_history
            WHERE trade_date < ?
            ORDER BY trade_date DESC
            LIMIT 1
            """,
            (current_trade_date,),
        ).fetchone()
        return None if row is None else float(row["total_amount"])


def save_run(
    *,
    status: str,
    market_state: str | None,
    risk_state: str | None,
    total_amount: float | None,
    payload: dict[str, Any],
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO market_runs
                (run_at, status, market_state, risk_state, total_amount, payload)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                status,
                market_state,
                risk_state,
                total_amount,
                json.dumps(payload, ensure_ascii=False, default=str),
            ),
        )


if __name__ == "__main__":
    init_db()
    print(f"SQLite initialized: {DB_PATH}")
