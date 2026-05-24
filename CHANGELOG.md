# Changelog

All notable changes to Adaptive MOCHA.

## [0.1.0-rc1] — 2026-05-17

The "system freeze" release used for the pilot study. Pre-registered analysis
plan is locked against this version.

### Added

- Provider-agnostic LLM client (`backend/llm.py`) with on-disk cache and token-budget guard.
  Supports OpenAI, Anthropic, Ollama, and a deterministic mock.
- Variation Theory counterfactual generator (`backend/variation.py`): both LLM and symbolic.
- Structural Alignment Theory grouper (`backend/alignment.py`): pairs and triples.
- LLM-backed classifier with growing in-context teaching prompt (`backend/classifier.py`).
- Rolling cognitive load estimator (`backend/cognitive_load.py`).
- Adaptive and Fixed controllers (`backend/adaptive_controller.py`).
- Per-participant SQLite logs (`backend/db.py`) with sessions, events, labels, TLX, quiz, classifier_eval.
- FastAPI app (`backend/app.py`) and vanilla-JS frontend (`frontend/`).
- D1 (sentiment) and D2 (argument quality) seed pools, probe sets, quiz items, concept cards.
- IRB packet, consent, protocol, debrief, TLX form, quiz spec, recruitment flyer (`study/`).
- 6-order Latin square counterbalancer (`scripts/assign_order.py`).
- Synthetic-participant simulator (`scripts/simulate_participant.py`).
- Synthetic study generator (`scripts/generate_synthetic_study.py`) — pipeline validation only.
- Unit + smoke tests (`tests/`) — 16 tests, all passing on Python 3.13 Windows.
- Pinned `requirements-lock.txt` for reproducibility.

### Pre-registered for next minor version (0.1.x)

- Pilot human participants (N=4-6) and any UI fixes that surface.
- Final freeze tag (`v0.1.0`) at the moment recruitment for the main study starts.
