"""Generate a clearly-labelled synthetic study run for end-to-end analysis testing.

This is **not** a replacement for the human study described in the
pre-registration. It is a pipeline-validation tool that lets the analysis
scripts, figures, and paper draft be exercised with realistic numbers before
real participants are recruited. Every generated `runs/*.sqlite` is tagged in
the `sessions.notes` field with `synthetic=true` so we can never accidentally
mix this with real data later.

Usage:

    python scripts/generate_synthetic_study.py --n 24 --tag pilot
    python scripts/generate_synthetic_study.py --n 24 --tag mainstudy

A `runs/manifest_<tag>.csv` records which participant got which order.
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import random
import shutil
import sys
import time
from itertools import permutations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("AM_PROVIDER", "mock")
os.environ.setdefault("AM_BLOCK_SECONDS", "1200")
os.environ.setdefault("AM_TOKEN_BUDGET", "10000000")

from backend.session import Session, CONDITIONS  # noqa: E402
from backend.domains import get as get_domain, load_quiz  # noqa: E402
from backend import db  # noqa: E402


ORDERS = list(permutations(CONDITIONS))


def simulated_label(example: dict, fatigue: float, skill: float, rng: random.Random) -> str:
    """Probability of agreeing with the gold label depends on difficulty,
    fatigue, and per-participant skill. The same generator is used for all
    three conditions; what changes across conditions is fatigue dynamics."""
    diff = float(example.get("difficulty", 0.5))
    p_correct = max(0.05, min(0.98,
        0.95 - 0.6 * diff - 0.25 * fatigue + 0.10 * (skill - 0.5)
    ))
    if rng.random() < p_correct:
        return example["label"]
    return rng.choice([l for l in ("positive", "negative", "mixed", "strong", "weak", "borderline")
                       if l != example["label"]])


def run_block(participant: str, domain_key: str, condition: str, *, skill: float, seed: int) -> dict:
    domain = get_domain(domain_key)
    sess = Session(participant_id=participant, domain=domain, condition=condition)
    rng = random.Random(seed)
    fatigue = 0.0
    # Fatigue dynamics differ by condition. The pre-registered theory:
    #   - Random: examples are unstructured -> higher cognitive load -> faster fatigue.
    #   - MOCHA-Fixed: structured pairs reduce load somewhat -> medium fatigue.
    #   - MOCHA-Adaptive: controller actively dampens fatigue when load is high.
    rise = {"random": 0.022, "fixed": 0.016, "adaptive": 0.014}[condition]
    recover = 0.0 if condition != "adaptive" else 0.06
    n_trials = 40
    for t in range(n_trials):
        view = sess.next_trial()
        if view is None:
            break
        gold = sess.open_ticket.trial.items[: view["controller"]["batch_size"]]
        responses = []
        for ex in gold:
            label = simulated_label(ex, fatigue, skill, rng)
            responses.append({"label": label, "confidence": int(80 - 30 * fatigue), "rationale": ""})
        # Simulate dwell time by sleeping briefly so the dwell_ms log is non-trivial.
        time.sleep(0.005 + 0.01 * fatigue)
        sess.submit_labels(responses)
        if t % 12 == 11:
            sess.record_micro_tlx(min(10.0, 3.0 + 7.0 * fatigue))
        fatigue = min(1.0, fatigue + rise)
        if condition == "adaptive" and fatigue > 0.6:
            fatigue = max(0.0, fatigue - recover)
    eval_result = sess.evaluate_classifier(when="post-block")
    sess.submit_tlx({
        "mental": int(8 + 8 * fatigue),
        "physical": int(2 + 2 * fatigue),
        "temporal": int(7 + 6 * fatigue),
        "performance": int(8 - 4 * fatigue),
        "effort": int(7 + 7 * fatigue),
        "frustration": int(3 + 12 * fatigue),
    })
    quiz = load_quiz(domain)
    rows = []
    quiz_score = 0
    for q in quiz:
        if rng.random() < 0.55 + 0.25 * skill - 0.30 * fatigue + 0.10 * (1 if condition != "random" else 0):
            ans = q["answer"]
        else:
            ans = rng.choice([o for o in q["options"] if o != q["answer"]])
        ok = ans == q["answer"]
        quiz_score += int(ok)
        rows.append((q["id"], ans, ok))
    sess.submit_quiz(rows)
    sess.end()
    return {
        "accuracy": eval_result["accuracy"],
        "macro_f1": eval_result["macro_f1"],
        "quiz_score": quiz_score,
        "final_fatigue": fatigue,
        "n_taught": len(sess.classifier.taught),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--tag", default="pilot")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--purge", action="store_true", help="delete prior runs for this tag first")
    args = ap.parse_args()

    runs_dir = REPO_ROOT / "runs"
    runs_dir.mkdir(exist_ok=True)
    manifest_path = runs_dir / f"manifest_{args.tag}.csv"

    if args.purge:
        for p in runs_dir.glob(f"{args.tag}-*.sqlite"):
            p.unlink()
        if manifest_path.exists():
            manifest_path.unlink()

    rng = random.Random(args.seed)
    rows = []
    print(f"# Generating SYNTHETIC pilot dataset (tag={args.tag}, n={args.n})")
    print(f"# This data is for pipeline validation only. Do NOT submit it as scientific evidence.")
    for i in range(args.n):
        order = ORDERS[i % len(ORDERS)]
        domain = "d1" if i % 2 == 0 else "d2"
        pid = f"{args.tag}-P{(i+1):02d}"
        skill = 0.5 + rng.uniform(-0.25, 0.25)
        seed_i = args.seed + i * 7
        per_cond = {}
        for c in order:
            r = run_block(pid, domain, c, skill=skill, seed=seed_i)
            per_cond[c] = r
        rows.append({
            "participant_id": pid,
            "domain": domain,
            "order_1": order[0], "order_2": order[1], "order_3": order[2],
            "skill": round(skill, 3),
            **{f"acc_{c}": per_cond[c]["accuracy"] for c in order},
            **{f"f1_{c}": per_cond[c]["macro_f1"] for c in order},
            **{f"quiz_{c}": per_cond[c]["quiz_score"] for c in order},
            **{f"fatigue_{c}": per_cond[c]["final_fatigue"] for c in order},
            **{f"taught_{c}": per_cond[c]["n_taught"] for c in order},
            "synthetic": True,
        })
        print(
            f"  {pid:>14s} dom={domain} order={'>'.join(order):>30s}  "
            f"acc(r/f/a)={per_cond['random']['accuracy']:.2f}/"
            f"{per_cond['fixed']['accuracy']:.2f}/"
            f"{per_cond['adaptive']['accuracy']:.2f}"
        )
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote manifest to {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
