"""Per-participant teaching session: glues domain, classifier, MOCHA, and controller.

A Session is **single-condition**. To run the full within-subjects protocol,
the orchestration layer creates three Sessions per participant in the
counterbalanced order.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any

from . import db
from .adaptive_controller import AdaptiveController, FixedController, ControllerDecision
from .alignment import Trial, build_trials, trials_with_variations
from .classifier import Classifier, random_sampler
from .cognitive_load import CognitiveLoadEstimator, LoadSample
from .config import CFG
from .domains import Domain, load_seed, load_probe
from .variation import generate_variations, pick_boundary_neighbours


CONDITIONS = ("random", "fixed", "adaptive")


@dataclass
class TrialTicket:
    """A Trial that has been shown to the participant and is awaiting labels."""
    trial: Trial
    shown_at: float
    expected_batch: int
    decision: ControllerDecision


@dataclass
class Session:
    participant_id: str
    domain: Domain
    condition: str  # one of CONDITIONS
    session_id: str = ""
    classifier: Classifier = field(init=False)
    seed_pool: list[dict[str, Any]] = field(default_factory=list)
    probe_pool: list[dict[str, Any]] = field(default_factory=list)
    trials: list[Trial] = field(default_factory=list)
    rng: random.Random = field(init=False)
    controller: Any = field(init=False)
    load_estimator: CognitiveLoadEstimator = field(default_factory=CognitiveLoadEstimator)
    open_ticket: TrialTicket | None = None
    cursor: int = 0

    def __post_init__(self) -> None:
        if self.condition not in CONDITIONS:
            raise ValueError(f"unknown condition {self.condition!r}; expected {CONDITIONS}")
        self.classifier = Classifier(domain=self.domain)
        self.rng = random.Random(CFG.random_seed + hash(self.participant_id) % 100000)
        self.seed_pool = load_seed(self.domain)
        self.probe_pool = load_probe(self.domain)
        if self.condition == "adaptive":
            self.controller = AdaptiveController()
        else:
            self.controller = FixedController()
        self._materialize_trials()
        self.session_id = db.new_session(
            self.participant_id, self.domain.name, self.condition,
            notes=f"trials={len(self.trials)}, pool={len(self.seed_pool)}",
        )
        db.log_event(self.participant_id, self.session_id, "session.start", {
            "condition": self.condition,
            "domain": self.domain.name,
            "n_trials_built": len(self.trials),
            "n_probe": len(self.probe_pool),
        })

    def _materialize_trials(self) -> None:
        if self.condition == "random":
            shuffled = random_sampler(self.seed_pool, self.rng)
            self.trials = [
                Trial(items=[ex], contrast_axis="(random)", rationale="", difficulty=ex.get("difficulty", 0.5))
                for ex in shuffled
            ]
            return

        symbolic_variations = {}
        for seed in self.seed_pool:
            neighbours = pick_boundary_neighbours(seed, self.seed_pool, self.domain, k=4)
            if neighbours:
                symbolic_variations[seed["id"]] = neighbours
        seed_trials = build_trials(self.seed_pool, self.domain, pairs_per_axis=4, triples=True)
        variation_trials = trials_with_variations(
            self.seed_pool[:8], symbolic_variations, self.domain
        )
        self.trials = seed_trials + variation_trials

    def next_trial(self) -> dict[str, Any] | None:
        if self.open_ticket is not None:
            return _trial_view(self.open_ticket.trial, self.open_ticket.decision)

        load_state = self.load_estimator.estimate()
        decision = self.controller.decide(load_state["load"])
        candidates = AdaptiveController.filter_trials(self.trials, decision.difficulty_band)
        if not candidates:
            candidates = self.trials
        for trial in candidates[self.cursor :]:
            self.cursor += 1
            self.open_ticket = TrialTicket(
                trial=trial,
                shown_at=time.time(),
                expected_batch=min(decision.batch_size, len(trial.items)),
                decision=decision,
            )
            db.log_event(self.participant_id, self.session_id, "controller.decision", {
                "load_state": load_state,
                "decision": decision.__dict__,
                "trial_axis": trial.contrast_axis,
                "trial_difficulty": trial.difficulty,
            })
            return _trial_view(trial, decision)
        return None

    def submit_labels(self, labels: list[dict[str, Any]]) -> dict[str, Any]:
        if self.open_ticket is None:
            return {"ok": False, "error": "no open trial"}
        trial = self.open_ticket.trial
        shown_at = self.open_ticket.shown_at
        decision = self.open_ticket.decision
        now = time.time()
        n_correct_cal = 0
        n_cal = 0
        for i, lbl in enumerate(labels):
            if i >= len(trial.items):
                break
            ex = trial.items[i]
            chosen = str(lbl.get("label", "")).lower().strip()
            confidence = lbl.get("confidence")
            rationale = lbl.get("rationale")
            db.log_label(
                self.participant_id, self.session_id,
                example_id=str(ex.get("id", "")),
                label=chosen,
                confidence=int(confidence) if confidence is not None else None,
                rationale=rationale,
                shown_at=shown_at,
                submitted_at=now,
                controller_state={
                    "load": decision.load,
                    "band": decision.difficulty_band,
                    "batch_size": decision.batch_size,
                    "inter_trial_ms": decision.inter_trial_ms,
                    "trial_axis": trial.contrast_axis,
                    "trial_difficulty": trial.difficulty,
                },
            )
            if chosen in self.domain.labels:
                self.classifier.teach(ex["text"], chosen, rationale)
            if ex.get("difficulty", 0.5) < 0.3:
                n_cal += 1
                n_correct_cal += int(chosen == ex.get("label"))

        dwell_ms = max(1, int((now - shown_at) * 1000 / max(1, len(labels))))
        cal = (n_correct_cal == n_cal) if n_cal else None
        self.load_estimator.add(LoadSample(dwell_ms=dwell_ms, correct_calibration=cal))
        self.open_ticket = None
        return {"ok": True, "load_state": self.load_estimator.estimate()}

    def record_micro_tlx(self, value: float) -> None:
        self.load_estimator.add(LoadSample(dwell_ms=0, self_report=float(value)))
        db.log_event(self.participant_id, self.session_id, "micro_tlx", {"value": value})

    def evaluate_classifier(self, when: str = "post-block") -> dict[str, Any]:
        result = self.classifier.evaluate(self.probe_pool)
        db.log_classifier_eval(
            participant_id=self.participant_id,
            session_id=self.session_id,
            when_in_block=when,
            probe_set=f"{self.domain.name}/probe.jsonl",
            n_correct=result["n_correct"],
            n_total=result["n_total"],
            macro_f1=result["macro_f1"],
            details={"per_example": result["per_example"][:200]},
        )
        return result

    def submit_tlx(self, values: dict[str, int]) -> None:
        db.log_tlx(self.participant_id, self.session_id, when_in_block="post-block", values=values)

    def submit_quiz(self, items: list[tuple[str, str, bool]]) -> None:
        db.log_quiz(self.participant_id, self.session_id, items)

    def end(self) -> None:
        db.log_event(self.participant_id, self.session_id, "session.end", {
            "n_taught": len(self.classifier.taught),
        })
        db.end_session(self.participant_id, self.session_id)


def _trial_view(trial: Trial, decision: ControllerDecision) -> dict[str, Any]:
    visible_items = trial.items[: decision.batch_size]
    return {
        "items": [
            {"id": ex.get("id"), "text": ex["text"]}
            for ex in visible_items
        ],
        "contrast_axis": trial.contrast_axis,
        "rationale": trial.rationale,
        "difficulty": trial.difficulty,
        "controller": {
            "band": decision.difficulty_band,
            "batch_size": len(visible_items),
            "inter_trial_ms": decision.inter_trial_ms,
            "load": decision.load,
        },
    }
