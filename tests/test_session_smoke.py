"""End-to-end smoke test: each condition runs a few trials without error,
SQLite logs are populated, and classifier accuracy is computable."""
from __future__ import annotations

import sqlite3
import uuid

from backend.session import Session, CONDITIONS
from backend.domains import get as get_domain, load_quiz
from backend import db


def _run_short_block(participant: str, condition: str, n: int = 12) -> dict:
    domain = get_domain("d1")
    s = Session(participant_id=participant, domain=domain, condition=condition)
    for _ in range(n):
        view = s.next_trial()
        if view is None:
            break
        responses = [
            {"label": s.open_ticket.trial.items[i]["label"], "confidence": 70, "rationale": "test"}
            for i in range(view["controller"]["batch_size"])
        ]
        s.submit_labels(responses)
    s.submit_tlx({"mental": 8, "physical": 1, "temporal": 6, "performance": 9, "effort": 7, "frustration": 3})
    rows = []
    for q in load_quiz(domain):
        rows.append((q["id"], q["answer"], True))
    s.submit_quiz(rows)
    result = s.evaluate_classifier()
    s.end()
    return result


def test_each_condition_runs():
    for cond in CONDITIONS:
        pid = f"sm-{cond}-{uuid.uuid4().hex[:6]}"
        out = _run_short_block(pid, cond)
        assert 0.0 <= out["accuracy"] <= 1.0
        assert out["n_total"] >= 40
        path = db.db_path_for(pid)
        assert path.exists()
        con = sqlite3.connect(path)
        try:
            sessions = con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            labels = con.execute("SELECT COUNT(*) FROM labels").fetchone()[0]
            tlx = con.execute("SELECT COUNT(*) FROM tlx").fetchone()[0]
            quiz = con.execute("SELECT COUNT(*) FROM quiz").fetchone()[0]
            evals = con.execute("SELECT COUNT(*) FROM classifier_eval").fetchone()[0]
        finally:
            con.close()
        assert sessions == 1
        assert labels >= 1
        assert tlx == 1
        assert quiz == 12
        assert evals == 1


def test_pipeline_produces_sane_accuracies_across_conditions():
    """All three conditions should run end-to-end and emit accuracies in
    [0, 1] on the probe set. The token-overlap mock LLM is NOT a faithful
    proxy for a real model (it actually rewards diversity, which works
    against MOCHA in the mock). The scientific question — whether
    structured teaching beats random in real LLMs — is answered by the
    human study, not by this smoke test."""
    for cond in CONDITIONS:
        pid = f"sm-cmp-{cond}-{uuid.uuid4().hex[:6]}"
        out = _run_short_block(pid, cond, n=20)
        assert 0.0 <= out["accuracy"] <= 1.0
        assert out["n_total"] >= 40


def test_counterbalance_orders():
    from scripts.assign_order import assign
    rows = assign(24)
    assert len(rows) == 24
    starts = [r["order_1"] for r in rows]
    assert set(starts) == {"random", "fixed", "adaptive"}
    for r in rows:
        triple = (r["order_1"], r["order_2"], r["order_3"])
        assert len(set(triple)) == 3
