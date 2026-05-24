# Domain D1: Mixed-sentiment movie reviews

## Concept under test

> "Given a 1-2 sentence movie review that may contain conflicting signals, decide the **overall sentiment** the writer is conveying."

Labels:

- `positive` — the writer would recommend the film overall.
- `negative` — the writer would not recommend the film overall.
- `mixed` — the writer is genuinely on the fence, with neither side dominating.

## Boundary-defining features

These are the axes that distinguish nearby examples from each other. Variation Theory generates counterfactuals along exactly one of these axes at a time.

| Feature | Values | Why it matters |
|---|---|---|
| `surface_contrast` | none / mild / strong | A "however" or "but" clause can flip the surface polarity without flipping the overall judgment. |
| `intensity` | low / medium / high | How emphatically the dominant polarity is expressed. |
| `hedging` | none / mild / heavy | "Kind of", "I guess", "in some ways" weaken commitment. |
| `sarcasm_signal` | absent / present | Surface-positive lexicon used to convey negative meaning. |
| `genre_marker` | none / present | Genre cues like "for a horror film" reframe baseline expectations. |

## Gold labelling rule (researcher-facing)

If the writer would clearly recommend or not recommend the film overall, pick `positive` or `negative` even if one clause leans the other way. Reserve `mixed` for cases where neither side dominates after rereading.

Two co-authors independently labelled every seed item and probe item; disagreements were resolved by a third labeller. Inter-rater agreement (Cohen's kappa) is reported in the paper appendix.
