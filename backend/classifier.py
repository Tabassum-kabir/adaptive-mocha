"""LLM-backed classifier whose prompt grows with taught examples.

This is the *model under teaching* across all three conditions. The same
classifier is used in Random, MOCHA-Fixed, and MOCHA-Adaptive; what differs is
which teaching examples it sees and in what order. This means any accuracy
difference is attributable to the teaching strategy, not to the model.
"""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from typing import Any

from . import llm
from .domains import Domain


SYS_TEMPLATE = """[CLASSIFY task]
{concept}

You will see labelled examples (TEACH) and then one new example (CLASSIFY).
Return JSON with fields:
  label: one of {labels}
  confidence: float in [0, 1]

Be conservative when the example is genuinely ambiguous. If unsure between two
labels with roughly equal pull, you may use the in-between label if one exists
in the label set.
"""


@dataclass
class Classifier:
    domain: Domain
    taught: list[dict[str, str]] = field(default_factory=list)
    max_in_context: int = 24

    def teach(self, text: str, label: str, rationale: str | None = None) -> None:
        if label not in self.domain.labels:
            raise ValueError(f"label {label!r} not in domain labels {self.domain.labels}")
        self.taught.append({"text": text, "label": label, "rationale": rationale or ""})

    def _build_messages(self, example_text: str) -> list[dict[str, str]]:
        sys = SYS_TEMPLATE.format(
            concept=self.domain.concept_prompt.strip(),
            labels=", ".join(self.domain.labels),
        )
        examples = self.taught[-self.max_in_context :]
        teach_block = "\n".join(
            f"- TEACH | text: {t['text']!r} | label: {t['label']}"
            + (f" | rationale: {t['rationale']}" if t['rationale'] else "")
            for t in examples
        ) or "(no examples taught yet)"
        user = (
            f"Here are the taught examples so far:\n{teach_block}\n\n"
            f"Now classify this new example:\nCLASSIFY: {example_text!r}\n"
            f"Respond with JSON only."
        )
        return [{"role": "system", "content": sys}, {"role": "user", "content": user}]

    def predict(self, text: str) -> dict[str, Any]:
        out = llm.complete(self._build_messages(text), temperature=0.0, max_tokens=128, json_mode=True)
        label, conf = _parse_label_conf(out["text"], allowed=self.domain.labels)
        return {
            "label": label,
            "confidence": conf,
            "provider": out["provider"],
            "cached": out["cached"],
            "usage": out["usage"],
        }

    def evaluate(self, examples: list[dict[str, Any]]) -> dict[str, Any]:
        n = len(examples)
        n_correct = 0
        per_label_tp: dict[str, int] = {l: 0 for l in self.domain.labels}
        per_label_fp: dict[str, int] = {l: 0 for l in self.domain.labels}
        per_label_fn: dict[str, int] = {l: 0 for l in self.domain.labels}
        per_example: list[dict[str, Any]] = []
        for ex in examples:
            pred = self.predict(ex["text"])
            true = ex["label"]
            ok = pred["label"] == true
            n_correct += int(ok)
            if ok:
                per_label_tp[true] += 1
            else:
                per_label_fp[pred["label"]] += 1
                per_label_fn[true] += 1
            per_example.append(
                {"id": ex["id"], "true": true, "pred": pred["label"], "conf": pred["confidence"]}
            )
        macro_f1 = _macro_f1(per_label_tp, per_label_fp, per_label_fn)
        return {
            "n_total": n,
            "n_correct": n_correct,
            "accuracy": n_correct / max(1, n),
            "macro_f1": macro_f1,
            "per_example": per_example,
        }


def _parse_label_conf(raw: str, allowed: tuple[str, ...]) -> tuple[str, float]:
    text = raw.strip()
    try:
        obj = json.loads(_extract_json(text))
        label = str(obj.get("label", "")).lower().strip()
        conf = float(obj.get("confidence", 0.5))
    except Exception:
        label = ""
        conf = 0.0
        for cand in allowed:
            if cand.lower() in text.lower():
                label = cand
                conf = 0.4
                break
    if label not in allowed:
        label = allowed[0]
        conf = 0.0
    conf = max(0.0, min(1.0, conf))
    return label, conf


def _extract_json(text: str) -> str:
    m = re.search(r"\{[\s\S]*\}", text)
    return m.group(0) if m else text


def _macro_f1(tp: dict[str, int], fp: dict[str, int], fn: dict[str, int]) -> float:
    f1s: list[float] = []
    for label in tp:
        denom_p = tp[label] + fp[label]
        denom_r = tp[label] + fn[label]
        p = tp[label] / denom_p if denom_p else 0.0
        r = tp[label] / denom_r if denom_r else 0.0
        f1 = (2 * p * r / (p + r)) if (p + r) else 0.0
        f1s.append(f1)
    return sum(f1s) / max(1, len(f1s))


def random_sampler(pool: list[dict[str, Any]], rng: random.Random) -> list[dict[str, Any]]:
    """Shuffled copy of the pool, used by the Random baseline condition."""
    indexed = list(pool)
    rng.shuffle(indexed)
    return indexed
