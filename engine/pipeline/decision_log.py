"""
Janus Security Engine - Pass 4: Decision Log (shadow logging)
Records one row per inspected prompt in SQLite: which stage decided, the scores, the judge's
verdict, and per-stage latency. The rows are the dataset for calibrating the judge and for
dashboards. Logging must never break inspection, so record() swallows its own errors.
"""

import hashlib
import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "decisions.db"
DB_PATH = Path(os.getenv("JANUS_DECISION_DB", DEFAULT_DB))
# Prompt text can be sensitive, so by default only a hash and the length are stored.
STORE_PROMPTS = os.getenv("JANUS_LOG_PROMPTS", "0") == "1"

SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    request_id TEXT,
    action TEXT NOT NULL,
    decided_by TEXT NOT NULL,
    reason TEXT,
    gray_area INTEGER NOT NULL,
    slm_injection_prob REAL,
    judge_verdict TEXT,
    judge_model TEXT,
    judge_failed INTEGER NOT NULL DEFAULT 0,
    judge_error TEXT,
    regex_ms REAL,
    slm_ms REAL,
    judge_ms REAL,
    total_ms REAL,
    prompt_sha256 TEXT NOT NULL,
    prompt_len INTEGER NOT NULL,
    prompt_text TEXT
);
CREATE INDEX IF NOT EXISTS idx_decisions_ts ON decisions (ts);
CREATE INDEX IF NOT EXISTS idx_decisions_gray ON decisions (gray_area, decided_by);
"""

COLUMNS = (
    "request_id", "action", "decided_by", "reason", "gray_area", "slm_injection_prob",
    "judge_verdict", "judge_model", "judge_failed", "judge_error",
    "regex_ms", "slm_ms", "judge_ms", "total_ms",
)


class DecisionLog:
    '''Append-only SQLite log of inspection decisions (thread-safe).'''

    def __init__(self, path=DB_PATH, store_prompts: bool = STORE_PROMPTS):
        self.path = Path(path)
        self.store_prompts = store_prompts
        self._lock = threading.Lock()
        self._conn = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self.path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(SCHEMA)
        except (sqlite3.Error, OSError) as e:
            logging.warning("Decision log disabled (%s: %s)", type(e).__name__, e)
            self._conn = None

    def record(self, prompt: str, **fields) -> None:
        '''Append one decision. Never raises: a logging failure must not fail the request.'''
        if self._conn is None:
            return
        row = {name: fields.get(name) for name in COLUMNS}
        row.update(
            ts=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            gray_area=int(bool(row["gray_area"])),
            judge_failed=int(bool(row["judge_failed"])),
            prompt_sha256=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            prompt_len=len(prompt),
            prompt_text=prompt if self.store_prompts else None,
        )
        names = ", ".join(row)
        marks = ", ".join(f":{name}" for name in row)
        try:
            with self._lock, self._conn:
                self._conn.execute(f"INSERT INTO decisions ({names}) VALUES ({marks})", row)
        except sqlite3.Error as e:
            logging.warning("Decision log write failed (%s: %s)", type(e).__name__, e)

    def rows(self, where: str = "1=1", params=()) -> list:
        '''Read decisions back as dicts (for tests, review tooling and dashboards).'''
        if self._conn is None:
            return []
        with self._lock:
            cursor = self._conn.execute(f"SELECT * FROM decisions WHERE {where} ORDER BY id", params)
            names = [col[0] for col in cursor.description]
            return [dict(zip(names, row)) for row in cursor.fetchall()]

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None


@lru_cache(maxsize=1)
def get_decision_log() -> DecisionLog:
    '''Get the global DecisionLog instance'''
    return DecisionLog()
