"""Structural Alignment Theory grouping.

Gentner's Structural Alignment Theory (1983, 2010) says that two examples are
maximally informative when they are aligned on most features and differ on the
feature whose role you want the learner to notice.

This module takes a set of seed examples (and optional generated variations)
and assembles **trials**: small batches that the UI shows side-by-side. A
trial is a list of 2-4 examples that share most of their feature values but
contrast on exactly one axis. Each trial is also tagged with the axis it
teaches, which the controller uses to balance coverage.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any

from .domains import Domain
from .variation import FEATURE_AXES, Variation


@dataclass
class Trial:
    items: list[dict[str, Any]] = field(default_factory=list)
    contrast_axis: str = ""
    rationale: str = ""
    difficulty: float = 0.5
    source: str = "seed"  # "seed" | "variation" | "mixed"


def _features(ex: dict[str, Any]) -> dict[str, str]:
    return dict(ex.get("features", {}))


def _diff_axes(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    fa, fb = _features(a), _features(b)
    return [k for k in fa.keys() | fb.keys() if fa.get(k) != fb.get(k)]


def build_trials(
    examples: list[dict[str, Any]],
    domain: Domain,
    *,
    pairs_per_axis: int = 4,
    triples: bool = True,
) -> list[Trial]:
    """Group `examples` into Structural-Alignment trials.

    The function prefers **pairs that differ on exactly one axis** (textbook
    alignment), then upgrades a subset to **triples** that walk a single axis
    across three values (e.g. evidence_type: data -> citation -> anecdote).
    Trials are returned in a difficulty-ascending order so the UI can pace.
    """
    by_axis: dict[str, list[tuple[dict[str, Any], dict[str, Any], str]]] = {}
    for a, b in itertools.combinations(examples, 2):
        diff = _diff_axes(a, b)
        if len(diff) == 1:
            axis = diff[0]
            by_axis.setdefault(axis, []).append((a, b, axis))

    trials: list[Trial] = []
    for axis, pairs in by_axis.items():
        pairs.sort(key=lambda t: abs(t[0].get("difficulty", 0.5) - t[1].get("difficulty", 0.5)))
        for a, b, ax in pairs[:pairs_per_axis]:
            trial = Trial(
                items=[a, b],
                contrast_axis=ax,
                rationale=(
                    f"These two examples are identical except for '{ax}'. "
                    f"Notice how the change in {ax!r} moves the label."
                ),
                difficulty=(a.get("difficulty", 0.5) + b.get("difficulty", 0.5)) / 2,
                source="seed",
            )
            trials.append(trial)

    if triples:
        trials.extend(_build_triples(examples, domain))

    trials.sort(key=lambda t: t.difficulty)
    return trials


def _build_triples(examples: list[dict[str, Any]], domain: Domain) -> list[Trial]:
    """Find chains of 3 examples that walk one axis through three values."""
    axes = FEATURE_AXES[domain.name]
    by_id = {ex["id"]: ex for ex in examples}
    triples: list[Trial] = []
    for axis, values in axes.items():
        if len(values) < 3:
            continue
        for combo in itertools.permutations(values, 3):
            bucket: dict[str, list[dict[str, Any]]] = {v: [] for v in combo}
            for ex in examples:
                v = _features(ex).get(axis)
                if v in bucket:
                    bucket[v].append(ex)
            if not all(bucket[v] for v in combo):
                continue
            cands = [bucket[v][0] for v in combo]
            ids = {c["id"] for c in cands}
            others = {k: [_features(c).get(k) for c in cands] for k in axes if k != axis}
            agree = all(len(set(vs)) == 1 for vs in others.values())
            if agree and len(ids) == 3:
                triples.append(
                    Trial(
                        items=cands,
                        contrast_axis=axis,
                        rationale=(
                            f"Three examples that vary only on '{axis}' "
                            f"({combo[0]} -> {combo[1]} -> {combo[2]}). "
                            f"Notice how the label changes as that axis moves."
                        ),
                        difficulty=sum(c.get("difficulty", 0.5) for c in cands) / 3,
                        source="seed",
                    )
                )
                break  # one triple per axis is plenty
    return triples


def trials_with_variations(
    seeds: list[dict[str, Any]],
    variations_by_seed: dict[str, list[Variation]],
    domain: Domain,
) -> list[Trial]:
    """Combine seeds with their LLM-generated variations into mixed trials.

    Each trial pairs a seed with one of its variations on a known axis. Used
    by MOCHA-Fixed and MOCHA-Adaptive when LLM generation is available.
    """
    trials: list[Trial] = []
    for seed in seeds:
        vs = variations_by_seed.get(seed["id"], [])
        for v in vs:
            seeds_features = _features(seed)
            seeds_features_view = {
                **seeds_features,
                v.varied_feature: v.new_value or seeds_features.get(v.varied_feature, ""),
            }
            sibling = {
                "id": v.id or f"{seed['id']}-vX",
                "text": v.text,
                "label": v.expected_label,
                "features": seeds_features_view,
                "difficulty": min(1.0, seed.get("difficulty", 0.5) + 0.1),
            }
            trials.append(
                Trial(
                    items=[seed, sibling],
                    contrast_axis=v.varied_feature,
                    rationale=(
                        f"The second example is the first with '{v.varied_feature}' "
                        f"changed to {v.new_value!r}; the expected label moves accordingly."
                    ),
                    difficulty=(seed.get("difficulty", 0.5) + sibling["difficulty"]) / 2,
                    source="mixed",
                )
            )
    trials.sort(key=lambda t: t.difficulty)
    return trials
