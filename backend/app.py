"""FastAPI app: routes for consent, teaching, TLX, quiz, evaluation.

The frontend is a vanilla HTML/JS bundle in `frontend/`; we serve it as
StaticFiles. Sessions live in-process during the study run; the SQLite log is
the durable record.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import db
from .config import CFG, REPO_ROOT
from .domains import DOMAINS, get as get_domain, load_quiz
from .session import Session


app = FastAPI(title="Adaptive MOCHA", version="0.1.0")
FRONTEND_DIR = REPO_ROOT / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


SESSIONS: dict[str, Session] = {}


def _key(participant: str, condition: str) -> str:
    return f"{participant}::{condition}"


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/teach")
def teach_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "teach.html")


@app.get("/tlx")
def tlx_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "tlx.html")


@app.get("/quiz")
def quiz_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "quiz.html")


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "provider": CFG.provider,
        "block_seconds": CFG.block_seconds,
        "token_used": __import__("backend.llm", fromlist=["LEDGER"]).LEDGER.used,
        "token_cap": CFG.token_budget,
        "domains": list(DOMAINS.keys()),
    }


class StartReq(BaseModel):
    participant: str
    domain: str
    condition: str


@app.post("/api/session/start")
def start_session(req: StartReq) -> dict[str, Any]:
    if req.domain not in DOMAINS:
        raise HTTPException(400, f"unknown domain {req.domain!r}")
    domain = get_domain(req.domain)
    session = Session(participant_id=req.participant, domain=domain, condition=req.condition)
    SESSIONS[_key(req.participant, req.condition)] = session
    return {
        "session_id": session.session_id,
        "domain": domain.name,
        "domain_title": domain.title,
        "domain_description": domain.description,
        "labels": list(domain.labels),
        "block_seconds": CFG.block_seconds,
        "condition": session.condition,
        "is_adaptive": session.condition == "adaptive",
        "show_alignment_hint": session.condition in ("fixed", "adaptive"),
    }


def _require_session(participant: str, condition: str) -> Session:
    s = SESSIONS.get(_key(participant, condition))
    if s is None:
        raise HTTPException(404, "session not found; call /api/session/start first")
    return s


@app.get("/api/next")
def next_trial(participant: str, condition: str) -> dict[str, Any]:
    s = _require_session(participant, condition)
    trial = s.next_trial()
    if trial is None:
        return {"done": True}
    return {"done": False, **trial}


class LabelItem(BaseModel):
    label: str
    confidence: int | None = None
    rationale: str | None = None


class LabelsReq(BaseModel):
    participant: str
    condition: str
    labels: list[LabelItem]


@app.post("/api/labels")
def submit_labels(req: LabelsReq) -> dict[str, Any]:
    s = _require_session(req.participant, req.condition)
    return s.submit_labels([item.model_dump() for item in req.labels])


class MicroTLXReq(BaseModel):
    participant: str
    condition: str
    value: float


@app.post("/api/micro_tlx")
def micro_tlx(req: MicroTLXReq) -> dict[str, Any]:
    s = _require_session(req.participant, req.condition)
    s.record_micro_tlx(req.value)
    return {"ok": True}


class TLXReq(BaseModel):
    participant: str
    condition: str
    mental: int
    physical: int
    temporal: int
    performance: int
    effort: int
    frustration: int


@app.post("/api/tlx")
def post_tlx(req: TLXReq) -> dict[str, Any]:
    s = _require_session(req.participant, req.condition)
    s.submit_tlx({
        "mental": req.mental,
        "physical": req.physical,
        "temporal": req.temporal,
        "performance": req.performance,
        "effort": req.effort,
        "frustration": req.frustration,
    })
    return {"ok": True}


class QuizReq(BaseModel):
    participant: str
    condition: str
    answers: dict[str, str]  # item_id -> chosen label


@app.post("/api/quiz")
def submit_quiz(req: QuizReq) -> dict[str, Any]:
    s = _require_session(req.participant, req.condition)
    quiz = load_quiz(s.domain)
    correct = {q["id"]: q["answer"] for q in quiz}
    rows: list[tuple[str, str, bool]] = []
    n_correct = 0
    for item_id, answer in req.answers.items():
        if item_id not in correct:
            continue
        ok = correct[item_id] == answer
        rows.append((item_id, answer, ok))
        n_correct += int(ok)
    s.submit_quiz(rows)
    return {"ok": True, "score": n_correct, "total": len(rows)}


@app.get("/api/quiz_items")
def quiz_items(participant: str, condition: str) -> dict[str, Any]:
    s = _require_session(participant, condition)
    quiz = load_quiz(s.domain)
    return {
        "items": [
            {"id": q["id"], "text": q["text"], "options": q["options"]}
            for q in quiz
        ]
    }


@app.post("/api/evaluate")
def evaluate(participant: str, condition: str, when: str = "post-block") -> dict[str, Any]:
    s = _require_session(participant, condition)
    return s.evaluate_classifier(when=when)


@app.post("/api/session/end")
def end_session(participant: str, condition: str) -> dict[str, Any]:
    s = _require_session(participant, condition)
    s.end()
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=False)
