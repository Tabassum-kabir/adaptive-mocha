# Qualitative codebook — Adaptive MOCHA exit interviews

Two coders independently code each transcript. Inter-rater reliability is
reported as **Cohen's kappa** at the segment level. Discrepancies are
resolved through discussion; if discussion does not converge, a third coder
breaks the tie. The codebook is finalised after coding the first three
transcripts and remains fixed thereafter.

## Coding unit

A **segment** is a meaning-complete utterance, typically 1-3 sentences. Codes
are not mutually exclusive within a segment; multi-code is allowed.

## Code families

### 1. Strategy comparison
- `s.preferred-random`         — participant preferred Random over MOCHA.
- `s.preferred-fixed`          — participant preferred MOCHA-Fixed.
- `s.preferred-adaptive`       — participant preferred MOCHA-Adaptive.
- `s.no-clear-preference`      — explicitly says they could not pick.

### 2. Pacing experience
- `p.too-fast`                 — felt rushed.
- `p.too-slow`                 — felt stalled.
- `p.right-pace`               — explicitly endorsed pacing.
- `p.felt-adapting`            — noticed system changing pace or difficulty.
- `p.felt-not-adapting`        — noticed lack of adaptation.

### 3. Concept understanding
- `c.aha-moment`               — described a moment of crystallising the concept.
- `c.persistent-confusion`     — concept boundary still felt unclear.
- `c.boundary-named`           — participant explicitly named a boundary
  feature (e.g., "the hedging mattered more than I thought").

### 4. Trust and agency
- `t.trust-system`             — feels the system supports them.
- `t.distrust-system`          — feels the system gets in their way.
- `t.want-control`             — explicit desire for more control.
- `t.want-defer`               — explicit desire to defer to the system.

### 5. Cognitive load (verbatim)
- `l.fatigue`                  — explicit mention of fatigue, tiredness, "drained".
- `l.flow`                     — explicit mention of flow, "in the zone", absorption.
- `l.boredom`                  — explicit mention of boredom, monotony.
- `l.distraction`              — environmental or internal distraction.

### 6. Design suggestions
- `d.want-rationale`           — wishes the system explained why an example was shown.
- `d.want-summary`             — wishes for an end-of-block summary.
- `d.want-replay`              — wishes to revisit prior examples.
- `d.want-skip`                — wishes to skip an example.
- `d.want-redo`                — wishes to change a prior label.

## Output

For each participant, code counts are exported to `analysis/output/qualitative_counts.csv`
and merged with the quantitative outcomes table for mixed-methods triangulation
in the discussion section.
