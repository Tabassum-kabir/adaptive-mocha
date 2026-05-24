# Concept-Understanding Quiz Specifications

After each teaching block, a 12-item multiple-choice quiz tests whether the participant has internalized the **concept boundary**, not just the labels they happened to see.

The quiz is generated **per domain**, not per condition. The same 12-item pool is used for all three conditions, but item presentation order is randomized per block. Item leakage is avoided by ensuring quiz items are disjoint from the teaching pool and the held-out probe set used for classifier evaluation.

## Domain D1: Mixed-sentiment movie reviews

Concept under test: "Overall sentiment of the review, accounting for mixed signals."

Item types (4 of each):

1. **Surface-positive but overall-negative** (e.g., "The cinematography was gorgeous, but the story collapsed in the second act and never recovered.").
2. **Surface-negative but overall-positive** (e.g., "It dragged at times, but the ending landed so hard I forgave every flaw.").
3. **Genuinely mixed** (no clear majority).

Each item: pick one of {Positive, Negative, Mixed}.

## Domain D2: Argument quality

Concept under test: "Is the supporting evidence strong enough to back the conclusion?"

Item types (4 of each):

1. **Strong** — explicit data, expert citation, or structurally sound logic.
2. **Weak** — anecdote-only, appeal to popularity, or non-sequitur.
3. **Borderline** — plausible but missing a specific link or quantification.

Each item: pick one of {Strong, Weak, Borderline}.

## Scoring

- Each correct answer = 1 point. Total range 0-12.
- Reported as `quiz_score` per block per participant.

## Generation

The 12 quiz items per domain are stored in `data/<domain>/quiz.jsonl` and are version-controlled with a fixed seed. They are reviewed by the researcher before the pilot starts. No quiz item is ever shown to a participant during teaching.
