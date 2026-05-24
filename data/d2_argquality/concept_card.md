# Domain D2: Argument quality

## Concept under test

> "Given a short paragraph that defends a claim, judge whether the **supporting evidence is strong enough** to back the conclusion."

Labels:

- `strong` — explicit data, expert citation, or structurally sound logic that directly supports the claim.
- `weak` — anecdote-only, appeal to popularity, fallacy, or non-sequitur.
- `borderline` — plausible but missing a specific link or quantification.

## Boundary-defining features

| Feature | Values | Why it matters |
|---|---|---|
| `evidence_type` | data / citation / anecdote / none | What kind of warrant the writer offers. |
| `quantification` | specific / vague / absent | "47%" vs "many" vs "" |
| `logical_link` | tight / loose / broken | Does the evidence connect to the claim being made? |
| `fallacy_signal` | none / present | Appeals to authority, popularity, etc. |
| `hedging` | none / mild / heavy | Confidence in the conclusion. |

## Gold labelling rule

Treat the conclusion as fixed and ask: "If a careful reader believed only the sentences in this paragraph, would they consider the conclusion supported?" `strong` is reserved for explicit quantified evidence with a tight logical link. `weak` covers any paragraph relying on anecdote, popularity, or a broken link. `borderline` is for everything in between: plausible but underspecified.
