"""Domain registry: labels, prompt fragments, and data loaders."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import DATA_DIR


@dataclass(frozen=True)
class Domain:
    name: str
    title: str
    description: str
    labels: tuple[str, ...]
    concept_prompt: str
    seed_path: Path
    probe_path: Path
    quiz_path: Path


D1_PROMPT = """You are classifying short movie-review snippets by overall sentiment.

Labels:
- positive: the writer would recommend the film overall.
- negative: the writer would not recommend the film overall.
- mixed: the writer is genuinely on the fence; neither side dominates.

Mixed-signal sentences with a strong final clause usually take the polarity of
that final clause. Reserve `mixed` for cases where neither side clearly wins.
"""

D2_PROMPT = """You are judging the strength of evidence in short argumentative paragraphs.

Labels:
- strong: explicit data, expert citation, or a structurally sound logical link.
- weak: anecdote-only, appeal to popularity or authority, or a broken link.
- borderline: plausible but missing a specific link or quantification.

Vague phrases like "many studies suggest" without a specific source typically
indicate `borderline`. Anecdotes and appeals to popularity are `weak` even when
the conclusion happens to be true.
"""


DOMAINS: dict[str, Domain] = {
    "d1": Domain(
        name="d1",
        title="Mixed-sentiment movie reviews",
        description="Decide the overall sentiment of a short review.",
        labels=("positive", "negative", "mixed"),
        concept_prompt=D1_PROMPT,
        seed_path=DATA_DIR / "d1_sentiment" / "seed.jsonl",
        probe_path=DATA_DIR / "d1_sentiment" / "probe.jsonl",
        quiz_path=DATA_DIR / "d1_sentiment" / "quiz.jsonl",
    ),
    "d2": Domain(
        name="d2",
        title="Argument quality",
        description="Judge whether the supporting evidence is strong enough.",
        labels=("strong", "weak", "borderline"),
        concept_prompt=D2_PROMPT,
        seed_path=DATA_DIR / "d2_argquality" / "seed.jsonl",
        probe_path=DATA_DIR / "d2_argquality" / "probe.jsonl",
        quiz_path=DATA_DIR / "d2_argquality" / "quiz.jsonl",
    ),
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def load_seed(domain: Domain) -> list[dict[str, Any]]:
    return load_jsonl(domain.seed_path)


def load_probe(domain: Domain) -> list[dict[str, Any]]:
    return load_jsonl(domain.probe_path)


def load_quiz(domain: Domain) -> list[dict[str, Any]]:
    return load_jsonl(domain.quiz_path)


def get(domain_key: str) -> Domain:
    if domain_key not in DOMAINS:
        raise KeyError(f"unknown domain {domain_key!r}; expected one of {list(DOMAINS)}")
    return DOMAINS[domain_key]
