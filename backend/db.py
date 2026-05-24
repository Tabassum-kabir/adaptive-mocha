"""SQLite schema and helpers for per-participant study logs.

Each participant gets their own SQLite file under `runs/<participant>.sqlite`.
This keeps data physically separable for withdrawal requests and reduces the
risk of cross-participant contamination.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator

from .config import RUNS_DIR


SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    participant_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    condition TEXT NOT NULL,
    started_at REAL NOT NULL,
    ended_at REAL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    ts REAL NOT NULL,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
);

CREATE TABLE IF NOT EXISTS labels (
    label_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    example_id TEXT NOT NULL,
    label TEXT NOT NULL,
    confidence INTEGER,
    rationale TEXT,
    shown_at REAL NOT NULL,
    submitted_at REAL NOT NULL,
    dwell_ms INTEGER NOT NULL,
    controller_state_json TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
);

CREATE TABLE IF NOT EXISTS tlx (
    tlx_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    when_in_block TEXT NOT NULL,
    mental INTEGER, physical INTEGER, temporal INTEGER,
    performance INTEGER, effort INTEGER, frustration INTEGER,
    mean_raw REAL,
    submitted_at REAL NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
);

CREATE TABLE IF NOT EXISTS quiz (
    quiz_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    answer TEXT NOT NULL,
    correct INTEGER NOT NULL,
    submitted_at REAL NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
);

CREATE TABLE IF NOT EXISTS classifier_eval (
    eval_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    when_in_block TEXT NOT NULL,
    probe_set TEXT NOT NULL,
    n_correct INTEGER NOT NULL,
    n_total INTEGER NOT NULL,
    accuracy REAL NOT NULL,
    macro_f1 REAL,
    submitted_at REAL NOT NULL,
    details_json TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
);

CREATE INDEX IF NOT EXISTS idx_events_session ON events (session_id);
CREATE INDEX IF NOT EXISTS idx_labels_session ON labels (session_id);
"""


def db_path_for(participant_id: str) -> Path:
    safe = "".join(c for c in participant_id if c.isalnum() or c in ("-", "_"))
    return RUNS_DIR / f"{safe}.sqlite"


@contextmanager
def connect(participant_id: str) -> Iterator[sqlite3.Connection]:
    path = db_path_for(participant_id)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def new_session(
    participant_id: str, domain: str, condition: str, notes: str | None = None
) -> str:
    sid = uuid.uuid4().hex
    with connect(participant_id) as c:
        c.execute(
            "INSERT INTO sessions (session_id, participant_id, domain, condition, started_at, notes)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (sid, participant_id, domain, condition, time.time(), notes),
        )
    return sid


def end_session(participant_id: str, session_id: str) -> None:
    with connect(participant_id) as c:
        c.execute(
            "UPDATE sessions SET ended_at = ? WHERE session_id = ?",
            (time.time(), session_id),
        )


def log_event(
    participant_id: str, session_id: str, kind: str, payload: dict[str, Any]
) -> None:
    with connect(participant_id) as c:
        c.execute(
            "INSERT INTO events (session_id, ts, kind, payload_json) VALUES (?, ?, ?, ?)",
            (session_id, time.time(), kind, json.dumps(payload, ensure_ascii=False)),
        )


def log_label(
    participant_id: str,
    session_id: str,
    example_id: str,
    label: str,
    confidence: int | None,
    rationale: str | None,
    shown_at: float,
    submitted_at: float,
    controller_state: dict[str, Any] | None,
) -> None:
    dwell_ms = max(0, int((submitted_at - shown_at) * 1000))
    with connect(participant_id) as c:
        c.execute(
            "INSERT INTO labels (session_id, example_id, label, confidence, rationale,"
            " shown_at, submitted_at, dwell_ms, controller_state_json)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                example_id,
                label,
                confidence,
                rationale,
                shown_at,
                submitted_at,
                dwell_ms,
                json.dumps(controller_state) if controller_state else None,
            ),
        )


def log_tlx(
    participant_id: str,
    session_id: str,
    when_in_block: str,
    values: dict[str, int],
) -> None:
    mean = sum(values.values()) / len(values)
    with connect(participant_id) as c:
        c.execute(
            "INSERT INTO tlx (session_id, when_in_block, mental, physical, temporal,"
            " performance, effort, frustration, mean_raw, submitted_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                when_in_block,
                values.get("mental"),
                values.get("physical"),
                values.get("temporal"),
                values.get("performance"),
                values.get("effort"),
                values.get("frustration"),
                mean,
                time.time(),
            ),
        )


def log_quiz(
    participant_id: str,
    session_id: str,
    items: Iterable[tuple[str, str, bool]],
) -> None:
    rows = [(session_id, iid, ans, int(correct), time.time()) for iid, ans, correct in items]
    with connect(participant_id) as c:
        c.executemany(
            "INSERT INTO quiz (session_id, item_id, answer, correct, submitted_at)"
            " VALUES (?, ?, ?, ?, ?)",
            rows,
        )


def log_classifier_eval(
    participant_id: str,
    session_id: str,
    when_in_block: str,
    probe_set: str,
    n_correct: int,
    n_total: int,
    macro_f1: float | None,
    details: dict[str, Any] | None,
) -> None:
    acc = n_correct / max(1, n_total)
    with connect(participant_id) as c:
        c.execute(
            "INSERT INTO classifier_eval (session_id, when_in_block, probe_set, n_correct,"
            " n_total, accuracy, macro_f1, submitted_at, details_json)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                when_in_block,
                probe_set,
                n_correct,
                n_total,
                acc,
                macro_f1,
                time.time(),
                json.dumps(details) if details else None,
            ),
        )
