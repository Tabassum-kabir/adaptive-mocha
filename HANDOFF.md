# Handoff: from this artifact to CHI 2027 submission

This file lists what is **done in code** and what still requires **human
action** before submission. Read this first.

## What is done

- Full system (`backend/`, `frontend/`) with three conditions: Random,
  MOCHA-Fixed, MOCHA-Adaptive. End-to-end smoke-tested over HTTP on this PC.
- Variation Theory + Structural Alignment implementations, both symbolic and
  LLM-driven.
- Cognitive Load Estimator + transparent rule-based Adaptive Controller.
- Provider-agnostic LLM client (OpenAI / Anthropic / Ollama / deterministic
  mock) with caching and a hard token-budget cap.
- D1 (sentiment) and D2 (argument quality) seed pools, held-out probe sets,
  concept-understanding quizzes, and concept cards.
- 6-order Latin square counterbalancing assignment script.
- IRB packet (consent, protocol, debrief, TLX form, quiz spec, flyer).
- Pre-registration document (`study/preregistration.md`) and reproducibility
  appendix (`REPRODUCIBILITY.md`).
- Pre-registered analysis pipeline (`analysis/analyze.py`) with mixed-effects
  models, Holm-Bonferroni pairwise contrasts, and Cohen's $d_z$. Runs on
  synthetic data today; runs on real data unchanged.
- Publication-ready figure scripts (`analysis/figures.py`) producing PDF + PNG.
- Qualitative codebook and counts/kappa script for exit interviews.
- LaTeX paper scaffold (`paper/paper.tex`) keyed to the figures and outcomes.
- 16 unit + smoke tests, all passing on Python 3.13 / Windows.
- Pinned `requirements-lock.txt`, version tag `0.1.0-rc1`, CHANGELOG.

## What still requires human action

In the rough order it must happen.

1. **IRB submission and approval.** Fill in PI name and institution in
   `study/irb_packet.md`, attach `consent.md`, `protocol.md`, `debrief.md`,
   `tlx_form.md`, `quiz_specs.md`, `recruitment_flyer.md`, submit to your
   institution's IRB. **Do not collect human data until approval.**

2. **Get an LLM API key.** OpenAI is the pre-registered primary. Copy
   `.env.example` to `.env`, set `AM_PROVIDER=openai`, set `OPENAI_API_KEY`.
   Expected per-session cost USD 0.40-0.60. Token cap is set to 200,000.

3. **OSF pre-registration.** Create an OSF project, upload
   `study/preregistration.md` and the system source as a frozen archive,
   note the OSF ID in the paper file.

4. **Recruit participants.** Use `study/recruitment_flyer.md`. Target N=24
   from your university subject pool. Schedule ~75-minute sessions.

5. **Run the pilot (N=4-6).** Use `python -m backend.app` to serve the UI.
   Each participant: open `http://127.0.0.1:8000/`, enter their participant
   ID, domain, and condition; the system handles the rest. Watch for UI
   issues; iterate; re-freeze with a new version tag.

6. **Run the main study (N=24).** Use the assignment sheet from
   `python scripts/assign_order.py --n 24` to decide each participant's
   condition order and domain. **Use `--tag chi27`** (or whatever you choose)
   so the SQLite files live alongside--but distinct from--the synthetic
   pipeline-test data.

7. **Code the exit interviews.** Two coders. Save annotations as CSVs in
   `analysis/qualitative_codes/<participant>_<coder>.csv` with columns
   `segment_id,codes`. Run `python analysis/qualitative.py` for counts and
   Cohen's kappa.

8. **Re-run the analysis.** `python analysis/analyze.py --tag chi27` and
   `python analysis/figures.py --tag chi27`. Copy the resulting figures
   into `paper/`. Replace every `\chiplaceholder{...}` in `paper.tex` with
   the real number.

9. **Compile the paper.** `pdflatex paper.tex; bibtex paper; pdflatex
   paper.tex; pdflatex paper.tex`.

10. **Open-source release.** Push the `adaptive-mocha/` folder to a
    public repo with a `v1.0.0` tag matching the camera-ready. Confirm
    `tests/` still pass on a clean clone. Confirm no participant text or
    API keys are in the history.

11. **Submit to CHI 2027.** Target deadline mid-September 2026 (verify
    the exact deadline at <https://chi2027.acm.org>).

## What cannot be done in code

- IRB approval (institutional process, ~2-4 weeks).
- Recruiting and consenting human participants.
- Running the live sessions and exit interviews.
- Coding the qualitative interview data.
- Any payment to participants.

Everything else is here.
