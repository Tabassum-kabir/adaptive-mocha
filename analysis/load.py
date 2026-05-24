"""Load per-participant SQLite logs into tidy pandas DataFrames.

`load_study(tag)` returns a dict of DataFrames keyed by table:

  - sessions    one row per participant x condition
  - labels      one row per labelled example
  - tlx         one row per post-block NASA-TLX submission
  - quiz        one row per quiz item
  - eval        one row per classifier evaluation
  - events      one row per logged event (used for controller trace)
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = REPO_ROOT / "runs"


def _iter_db_paths(tag: str) -> Iterable[Path]:
    return sorted(RUNS_DIR.glob(f"{tag}-*.sqlite"))


def _read_all(paths: Iterable[Path], query: str) -> pd.DataFrame:
    frames = []
    for p in paths:
        con = sqlite3.connect(p)
        try:
            df = pd.read_sql_query(query, con)
            df["participant_id"] = p.stem
            frames.append(df)
        finally:
            con.close()
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def load_study(tag: str = "mainstudy") -> dict[str, pd.DataFrame]:
    paths = list(_iter_db_paths(tag))
    if not paths:
        raise FileNotFoundError(f"no run databases match tag {tag!r} in {RUNS_DIR}")
    sessions = _read_all(paths, "SELECT * FROM sessions")
    labels = _read_all(paths, "SELECT * FROM labels")
    tlx = _read_all(paths, "SELECT * FROM tlx")
    quiz = _read_all(paths, "SELECT * FROM quiz")
    evals = _read_all(paths, "SELECT * FROM classifier_eval")
    events = _read_all(paths, "SELECT * FROM events")
    if not sessions.empty:
        sessions = sessions.rename(columns={"participant_id": "_db_id"})
        sessions["participant_id"] = sessions["participant_id_y"] if "participant_id_y" in sessions.columns else sessions.get("_db_id")
        if "participant_id" not in sessions.columns:
            sessions["participant_id"] = sessions["_db_id"]
        sessions = sessions.drop(columns=[c for c in ("_db_id",) if c in sessions.columns])
    for df, key in (
        (labels, "session_id"),
        (tlx, "session_id"),
        (quiz, "session_id"),
        (evals, "session_id"),
        (events, "session_id"),
    ):
        if df.empty:
            continue
        join_cols = ["session_id", "domain", "condition"]
        if not all(c in sessions.columns for c in join_cols):
            continue
        df_merge = df.merge(
            sessions[["session_id", "domain", "condition", "participant_id"]],
            on="session_id", how="left",
        )
        if "participant_id_x" in df_merge.columns and "participant_id_y" in df_merge.columns:
            df_merge["participant_id"] = df_merge["participant_id_y"].fillna(df_merge["participant_id_x"])
            df_merge = df_merge.drop(columns=["participant_id_x", "participant_id_y"])
        for col in list(df_merge.columns):
            if col not in df.columns and col in ("domain", "condition"):
                df[col] = df_merge[col]
            elif col == "participant_id":
                df[col] = df_merge[col]
    return {
        "sessions": sessions,
        "labels": labels,
        "tlx": tlx,
        "quiz": quiz,
        "eval": evals,
        "events": events,
    }


def primary_outcome_table(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Wide-ish table with one row per session, key outcomes."""
    sessions = data["sessions"][["participant_id", "session_id", "domain", "condition"]].copy()
    eval_post = data["eval"].copy()
    if not eval_post.empty:
        eval_post = eval_post[eval_post["when_in_block"] == "post-block"]
        eval_post = eval_post.groupby("session_id", as_index=False).agg({
            "accuracy": "last", "macro_f1": "last", "n_total": "last", "n_correct": "last",
        })
    tlx = data["tlx"][["session_id", "mean_raw", "mental", "physical", "temporal",
                       "performance", "effort", "frustration"]].copy() if not data["tlx"].empty else pd.DataFrame()
    quiz_score = pd.DataFrame()
    if not data["quiz"].empty:
        quiz_score = (
            data["quiz"].groupby("session_id")["correct"].sum().reset_index().rename(columns={"correct": "quiz_score"})
        )
    labels = data["labels"].copy()
    time_per_label = pd.DataFrame()
    if not labels.empty:
        time_per_label = labels.groupby("session_id")["dwell_ms"].median().reset_index().rename(
            columns={"dwell_ms": "median_dwell_ms"}
        )
    out = sessions
    for piece in (eval_post, tlx, quiz_score, time_per_label):
        if not piece.empty:
            out = out.merge(piece, on="session_id", how="left")
    return out
