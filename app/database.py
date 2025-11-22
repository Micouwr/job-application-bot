# app/database.py
from __future__ import annotations
import sqlite3
from typing import Iterator, List, Dict, Any, Optional
import contextlib
import logging
import os

logger = logging.getLogger(__name__)


DEFAULT_DB_PATH = os.getenv("JOBBOT_DB", "jobbot.sqlite3")


class Database:
    """
    Lightweight SQLite wrapper for storing history of runs.

    This is intentionally simple; replace with SQLAlchemy if you prefer.
    """

    def __init__(self, path: str = DEFAULT_DB_PATH) -> None:
        self.path = path
        self._ensure_db()

    def _ensure_db(self) -> None:
        with self.get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    input_text TEXT,
                    result_text TEXT
                )
            """
            )
            conn.commit()

    @contextlib.contextmanager
    def get_conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=30)
        try:
            yield conn
        finally:
            conn.close()

    def save_history(
        self, action: str, input_text: Optional[str], result_text: Optional[str]
    ) -> int:
        import time

        ts = int(time.time())
        with self.get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO history (timestamp, action, input_text, result_text) VALUES (?, ?, ?, ?)",
                (ts, action, input_text, result_text),
            )
            conn.commit()
            last_id = cur.lastrowid
        logger.debug("Saved history id=%s action=%s", last_id, action)
        return last_id

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_conn() as conn:
            cur = conn.execute(
                "SELECT id, timestamp, action, input_text, result_text FROM history ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = cur.fetchall()
        return [
            {"id": r[0], "timestamp": r[1], "action": r[2], "input_text": r[3], "result_text": r[4]}
            for r in rows
        ]