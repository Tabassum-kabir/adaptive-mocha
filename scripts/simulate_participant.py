"""Simulate a participant teaching the LLM across one or more conditions.

This script powers two things:

1. **Smoke tests**: the system pipeline (Session, controller, classifier, db)
   must run end-to-end on the lab PC with no API key. The `mock` LLM
   provider makes that possible.

2. **Pre-pilot validation**: even with the mock LLM the simulator produces
   labelled events and can be used to verify that telemetry, evaluation, and
   counterbalancing are wired correctly *before* recruiting humans.

The simulator uses a noisy-oracle policy: it agrees with the gold label with
probability that decays as difficulty rises, modulated by simulated cognitive
load. This is a tool for plumbing, not a substitute for the human study.
"""
from __future__ import annotations

import argparse
import os
import random
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("AM_PROVIDER", "mock")
os.environ.setdefault("AM_BLOCK_SECONDS", "60")  # short blocks for smoke
os.environ.setdefault("AM_TOKEN_BUDGET", "10000000")

from backend.session import Session, CONDITIONS  # noqa: E402
from backend.domains import get as get_domain, load_quiz  # noqa: E402


def simulated_label(example: dict, fatigue: float, rng: random.Random) -> str:
    diff = float(example.get("difficulty", 0.5))
    base = 0.95 - 0.55 * diff - 0.20 * fatigue
    if rng.random() < base:
        return example["label"]
    distractors = [l for l in example.get("alt_labels", []) if l != example["label"]]
    if not distractors:
        labels = ["positive", "negative", "mixed", "strong", "weak", "borderline"]
        distractors = [l for l in labels if l != example["label"]]
    return rng.choice(distractors)


def simulate_block(participant: str, domain_key: str, condition: str, *, n_trials: int = 40, seed: int = 0) -> dict:
    domain = get_domain(domain_key)
    sess = Session(participant_id=participant, domain=domain, condition=condition)
    rng = random.Random(seed)
    label_counts: dict[str, int] = {l: 0 for l in domain.labels}
    fatigue = 0.0
    for t in range(n_trials):
        view = sess.next_trial()
        if view is None:
            break
        # convert the items in `view` back to their gold examples using the trial
        gold = sess.open_ticket.trial.items[: view["controller"]["batch_size"]]
        responses = []
        for ex in gold:
            label = simulated_label(ex, fatigue, rng)
            responses.append({"label": label, "confidence": 50, "rationale": ""})
            label_counts[label] = label_counts.get(label, 0) + 1
        sess.submit_labels(responses)
        if t % 12 == 11:
            sess.record_micro_tlx(min(10.0, 4.0 + 6.0 * fatigue))
        fatigue = min(1.0, fatigue + (0.01 if condition == "adaptive" else 0.018))
        if condition == "adaptive" and fatigue > 0.6:
            fatigue = max(0.0, fatigue - 0.10)
    eval_result = sess.evaluate_classifier(when="post-block")
    sess.submit_tlx({
        "mental": int(8 + 6 * fatigue),
        "physical": int(2 + 2 * fatigue),
        "temporal": int(7 + 5 * fatigue),
        "performance": int(8 - 4 * fatigue),
        "effort": int(7 + 6 * fatigue),
        "frustration": int(4 + 10 * fatigue),
    })
    quiz = load_quiz(domain)
    quiz_score = 0
    rows = []
    for q in quiz:
        # The simulator answers correctly with probability 0.7 minus fatigue
        if rng.random() < 0.80 - 0.30 * fatigue:
            ans = q["answer"]
        else:
            ans = rng.choice([o for o in q["options"] if o != q["answer"]])
        ok = ans == q["answer"]
        quiz_score += int(ok)
        rows.append((q["id"], ans, ok))
    sess.submit_quiz(rows)
    sess.end()
    return {
        "participant": participant,
        "domain": domain_key,
        "condition": condition,
        "n_taught": len(sess.classifier.taught),
        "accuracy": eval_result["accuracy"],
        "macro_f1": eval_result["macro_f1"],
        "quiz_score": quiz_score,
        "final_fatigue": fatigue,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--participant", required=True)
    ap.add_argument("--domain", choices=["d1", "d2"], default="d1")
    ap.add_argument("--condition", choices=list(CONDITIONS) + ["all"], default="all")
    ap.add_argument("--n-trials", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    conds = list(CONDITIONS) if args.condition == "all" else [args.condition]
    results = []
    for c in conds:
        r = simulate_block(args.participant, args.domain, c, n_trials=args.n_trials, seed=args.seed)
        results.append(r)
        print(
            f"  {c:>9s}  acc={r['accuracy']:.3f}  f1={r['macro_f1']:.3f}  "
            f"quiz={r['quiz_score']}/12  taught={r['n_taught']:3d}  fatigue={r['final_fatigue']:.2f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
