# NASA-TLX implementation notes

We use the **raw (unweighted) NASA-TLX** as recommended for short within-subject comparisons (Hart, 2006). It is administered after each teaching block.

## Items

Each item is rated on a 21-point scale (0 = Very Low / Perfect, 20 = Very High / Failure). The frontend renders sliders with the endpoint labels below.

| ID | Dimension | Left anchor (0) | Right anchor (20) |
|----|-----------|------------------|--------------------|
| `mental` | Mental Demand | Very Low | Very High |
| `physical` | Physical Demand | Very Low | Very High |
| `temporal` | Temporal Demand | Very Low | Very High |
| `performance` | Performance | Perfect | Failure |
| `effort` | Effort | Very Low | Very High |
| `frustration` | Frustration | Very Low | Very High |

## Scoring

Raw TLX = arithmetic mean of the six items, range 0-20.

## Mid-block micro-TLX (Adaptive condition only)

At minute 8 and minute 14 of the Adaptive block, the system shows a single-item probe:

> "Right now, how hard does this feel?" (0 = very easy, 10 = very hard)

This single value feeds the cognitive-load estimator. It is **not** part of the post-block TLX and is **not** reported as a primary outcome.
