"""Variation Theory counterfactual generator.

Marton's Variation Theory (1981, 2014) argues that a learner discriminates a
concept by experiencing **contrasting variation** along the concept's
critical features while other features are held constant. We implement this
two ways:

1. **LLM generator** (`generate_variations`): asks the model to perturb one
   boundary-defining feature at a time, producing a small fan of
   counterfactuals around a seed example.

2. **Symbolic generator** (`pick_boundary_neighbours`): selects items from the
   existing seed pool that differ from the anchor on exactly one feature axis.
   This requires no LLM call and is used as a deterministic fallback during
   pilot dry-runs.

Both return a list of `Variation` records with explicit `varied_feature` tags
so downstream Structural Alignment can group them sensibly.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from . import llm
from .domains import Domain


VARIATION_PROMPT = """[VARIATION task]
You are generating contrasting variations of a seed example for concept
teaching, following Marton's Variation Theory: vary exactly one
boundary-defining feature at a time, keep everything else constant.

Concept and labels:
{concept}

Boundary-defining features for this domain (vary one at a time):
{features}

Seed example:
  text: {seed_text!r}
  current label: {seed_label}
  current feature values: {seed_features}

Produce {k} contrasting variations. For each variation:
  - pick exactly ONE feature to flip or move
  - keep the topic / surface domain similar
  - the variation should be a single short sentence, like the seed
  - include the *expected* label after the change

Return JSON:
{{
  "variations": [
    {{"text": "...", "varied_feature": "...", "new_value": "...", "expected_label": "..."}}
  ]
}}
"""


@dataclass
class Variation:
    text: str
    expected_label: str
    varied_feature: str
    new_value: str
    parent_id: str | None = None
    source: str = "llm"  # "llm" or "symbolic"
    id: str = ""


FEATURE_AXES: dict[str, dict[str, tuple[str, ...]]] = {
    "d1": {
        "surface_contrast": ("none", "mild", "strong"),
        "intensity": ("low", "medium", "high"),
        "hedging": ("none", "mild", "heavy"),
        "sarcasm_signal": ("absent", "present"),
        "genre_marker": ("none", "present"),
    },
    "d2": {
        "evidence_type": ("data", "citation", "anecdote", "none"),
        "quantification": ("specific", "vague", "absent"),
        "logical_link": ("tight", "loose", "broken"),
        "fallacy_signal": ("none", "present"),
        "hedging": ("none", "mild", "heavy"),
    },
}


def feature_axes_for(domain: Domain) -> dict[str, tuple[str, ...]]:
    return FEATURE_AXES[domain.name]


def generate_variations(
    seed: dict[str, Any],
    domain: Domain,
    k: int = 4,
) -> list[Variation]:
    """LLM-driven counterfactual fan around a single seed example."""
    axes = feature_axes_for(domain)
    feature_list = "\n".join(f"  - {name}: {' | '.join(values)}" for name, values in axes.items())
    msg_user = VARIATION_PROMPT.format(
        concept=domain.concept_prompt.strip(),
        features=feature_list,
        seed_text=seed["text"],
        seed_label=seed["label"],
        seed_features=seed.get("features", {}),
        k=k,
    )
    out = llm.complete(
        [
            {"role": "system", "content": "[VARIATION task] You are a careful pedagogical assistant."},
            {"role": "user", "content": msg_user},
        ],
        temperature=0.4,
        max_tokens=800,
        json_mode=True,
    )
    return _parse_variations(out["text"], domain, seed.get("id"))


def _parse_variations(raw: str, domain: Domain, parent_id: str | None) -> list[Variation]:
    m = re.search(r"\{[\s\S]*\}", raw)
    text = m.group(0) if m else raw
    try:
        obj = json.loads(text)
    except Exception:
        return []
    out: list[Variation] = []
    for i, v in enumerate(obj.get("variations", [])):
        label = str(v.get("expected_label", "")).lower().strip()
        if label not in domain.labels:
            continue
        out.append(
            Variation(
                text=str(v.get("text", "")).strip(),
                expected_label=label,
                varied_feature=str(v.get("varied_feature", "")).strip(),
                new_value=str(v.get("new_value", "")).strip(),
                parent_id=parent_id,
                source="llm",
                id=f"{parent_id or 'seed'}-v{i+1}",
            )
        )
    return out


def pick_boundary_neighbours(
    anchor: dict[str, Any],
    pool: Iterable[dict[str, Any]],
    domain: Domain,
    k: int = 4,
) -> list[Variation]:
    """Pick examples from `pool` that differ from `anchor` on exactly one feature.

    This is the deterministic fallback used when no LLM is available or when
    we want to certify a clean Variation-Theory step from existing data.
    """
    anchor_id = anchor.get("id")
    anchor_features: dict[str, str] = dict(anchor.get("features", {}))
    candidates: list[tuple[int, str, dict[str, Any]]] = []
    for ex in pool:
        if ex.get("id") == anchor_id:
            continue
        feats: dict[str, str] = dict(ex.get("features", {}))
        differing = [k_ for k_ in anchor_features if anchor_features.get(k_) != feats.get(k_)]
        if len(differing) == 1:
            candidates.append((len(differing), differing[0], ex))
    candidates.sort(key=lambda t: (t[0], t[1]))
    out: list[Variation] = []
    seen_axes: set[str] = set()
    for _, axis, ex in candidates:
        if axis in seen_axes:
            continue
        seen_axes.add(axis)
        out.append(
            Variation(
                text=ex["text"],
                expected_label=ex["label"],
                varied_feature=axis,
                new_value=str(ex.get("features", {}).get(axis, "")),
                parent_id=anchor_id,
                source="symbolic",
                id=str(ex.get("id", "")),
            )
        )
        if len(out) >= k:
            break
    return out
