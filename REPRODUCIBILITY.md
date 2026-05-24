# Reproducibility appendix

This document records every choice that affects the numbers in the paper.
It accompanies the open-source release and is updated only when the system
or analysis changes.

## System version

`adaptive-mocha v0.1.0-rc1` (see `VERSION`, `CHANGELOG.md`). The release used
in the camera-ready paper will be tagged `v1.0.0`.

## Runtime

- OS: Windows 10 (build 22631) tested. Linux and macOS supported by the same
  Python codebase; the FastAPI server listens on `127.0.0.1:8000`.
- Python: 3.13.7 (3.11+ supported).
- Hardware: any CPU-only laptop with 4 GB RAM. No GPU.
- Dependencies pinned in `requirements-lock.txt`.

## LLM provider

| Field | Value |
|---|---|
| Primary provider | OpenAI |
| Primary model | `gpt-4o-mini` |
| Fallback provider | Anthropic |
| Fallback model | `claude-3-5-haiku-20241022` |
| Local dev fallback | Ollama `phi3:mini` |
| Token budget per session | 200,000 (cap enforced by `backend/llm.LEDGER`) |
| Caching | SHA-256 of (provider, model, messages, params) on disk in `analysis/cache/llm/` |

Every API call is logged with its returned `usage` block. The cache means
repeated runs are deterministic.

## Counterbalancing

`python scripts/assign_order.py --n 24 --out study/assignment.csv`

The 6-order Latin square is enumerated once per study; the CSV is the
canonical record of which participant got which condition order.

## Data sources

- D1 seed pool: hand-authored, 72 items, `data/d1_sentiment/seed.jsonl`
- D1 probe set: hand-authored, 50 items, `data/d1_sentiment/probe.jsonl`
- D1 quiz: hand-authored, 12 items, `data/d1_sentiment/quiz.jsonl`
- D2 seed pool: hand-authored, 72 items, `data/d2_argquality/seed.jsonl`
- D2 probe set: hand-authored, 50 items, `data/d2_argquality/probe.jsonl`
- D2 quiz: hand-authored, 12 items, `data/d2_argquality/quiz.jsonl`

All examples were independently labelled by two of the co-authors;
disagreements were resolved by a third. Inter-rater agreement (Cohen's
$\kappa$) is reported in the paper appendix.

Probe and quiz items are **disjoint from the seed pool** (tested by
`tests/test_domains.py::test_seed_disjoint_from_probe` and
`test_quiz_disjoint_from_probe`).

## Random seeds

| Where | Seed | Effect |
|---|---|---|
| `CFG.random_seed` | 20260517 | Base seed for per-participant RNGs |
| Per-participant RNG | base + `hash(participant_id) % 100000` | Trial order, counterbalancing |
| Synthetic dataset (pipeline test only) | CLI `--seed` | Reproduce synthetic SQLite |

## Reproducing the pipeline

End-to-end on a fresh machine:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-lock.txt
pytest -q

# (mock-only, no API calls)
$env:AM_PROVIDER = "mock"
python scripts/generate_synthetic_study.py --n 24 --tag mainstudy --seed 2026 --purge
python analysis/analyze.py --tag mainstudy
python analysis/figures.py --tag mainstudy
```

For the human study, replace `--tag mainstudy` with `--tag chi27` and run
`python -m backend.app` to serve the UI; the analysis scripts accept the
new tag unchanged.

## Files released

- `backend/` (Apache-2.0)
- `frontend/` (Apache-2.0)
- `analysis/` (Apache-2.0)
- `data/*/seed.jsonl`, `probe.jsonl`, `quiz.jsonl` (CC-BY-4.0)
- `study/*.md` (CC-BY-4.0)
- `paper/paper.tex`, `references.bib` (CC-BY-4.0 once accepted)
- `runs/manifest_chi27.csv` (data release after de-identification; SQLite
  files anonymised and aggregated)

Audio recordings and raw transcripts are **not** released; coded segment
counts are.

## Estimated cost

A real-LLM run of $N = 24$ participants $\times$ 3 conditions $\times$ ~40
trials at `gpt-4o-mini` averages USD 0.40-0.60 per session, putting the
full study budget at USD 30-60. The token cap of 200,000 per session is a
hard ceiling.
