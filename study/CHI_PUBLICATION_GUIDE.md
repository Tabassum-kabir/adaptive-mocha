# Complete guide: collect real data → build the CHI 2027 paper

This is the end-to-end playbook for **Adaptive MOCHA**. Read it top to bottom once, then use each phase as a checklist.

**You are new — that is fine.** A CHI paper here is not “write 10 pages first.” It is:

1. Get ethics approval.
2. Run 24 real people through the app.
3. Turn SQLite logs into numbers and figures.
4. Fill in the LaTeX scaffold with those numbers.
5. Submit.

**Never use** `runs/mainstudy-*.sqlite` or `runs/pilot-*.sqlite` from synthetic generators as paper results. Those are pipeline tests only.

---

## Part 0 — What you already have

| Asset | Location |
|-------|----------|
| Working app | `python -m uvicorn backend.app:app` → http://127.0.0.1:8000/ |
| Config (timer, API) | `.env` (not `.env.example`) |
| Study materials | `study/consent.md`, `protocol.md`, `debrief.md`, `irb_packet.md` |
| Pre-registration draft | `study/preregistration.md` |
| Analysis | `analysis/analyze.py`, `analysis/figures.py` |
| Paper scaffold | `paper/paper.tex` (placeholders marked `\chiplaceholder{...}`) |
| Tests | `pytest -q` (16 tests) |

---

## Part 1 — Before any participant (2–4 weeks)

### 1.1 IRB / ethics approval

1. Edit `study/irb_packet.md` — add your name, university, IRB contact, compensation.
2. Attach: `consent.md`, `protocol.md`, `debrief.md`, `tlx_form.md`, `quiz_specs.md`.
3. Submit to your institution’s IRB (request **expedited** review if available).
4. **Wait for approval.** Do not pay participants or report results until approved.

Keep the approval letter in `study/irb_approval/` (create folder).

### 1.2 OSF pre-registration (do before main study)

1. Create account at https://osf.io
2. New project: “Adaptive MOCHA CHI 2027”
3. Upload: `study/preregistration.md`, `study/protocol.md`, frozen `requirements-lock.txt`, git commit hash or zip of code at `v1.0.0`
4. Note the OSF URL — you will put it in the paper

This locks your hypotheses and analysis plan **before** you look at main-study results.

### 1.3 Configure production `.env`

```env
AM_PROVIDER=openai
OPENAI_API_KEY=sk-...your key...
OPENAI_MODEL=gpt-4o-mini
AM_BLOCK_SECONDS=1200
AM_TOKEN_BUDGET=200000
AM_RANDOM_SEED=20260517
```

- `1200` = 20 minutes per teaching block (real study).
- For **your own tests only**, use `AM_BLOCK_SECONDS=120` (2 minutes).

**After every `.env` change:** stop the server (Ctrl+C) and start it again.

### 1.4 Generate participant assignment sheet

Participant IDs **must** match the analysis naming rule: files are `runs/<tag>-P01.sqlite`.

Default tag for the main study: **`chi27`**

```powershell
cd "c:\SDL2-2.26.3\CHI RESEARCH\adaptive-mocha"
.\.venv\Scripts\activate
python scripts/assign_order.py --n 24 --id-prefix chi27 --out study/assignment_main.csv
```

Open `study/assignment_main.csv`. Each row tells you:

- `participant_id` — type **exactly** this in the browser (e.g. `chi27-P01`)
- `domain` — `d1` or `d2` (same for all 3 blocks for that person)
- `order_1`, `order_2`, `order_3` — which condition first, second, third

Print one row per session day.

### 1.5 Lab setup checklist (day before first participant)

- [ ] Laptop charged; server tested
- [ ] `.env` has real API key; `/health` shows `"provider": "openai"`
- [ ] Consent forms printed (or PDF on tablet)
- [ ] Compensation ready (cash / voucher)
- [ ] Quiet room; one person at a time
- [ ] Audio recorder if using interviews (optional consent)
- [ ] `study/assignment_main.csv` printed
- [ ] Researcher copy of this guide + `study/protocol.md`

### 1.6 Pilot study (N = 4–6, after IRB)

**Purpose:** fix bugs and timing — **not** for the paper.

1. Use shorter blocks if needed: `AM_BLOCK_SECONDS=600` (10 min) for pilot only.
2. Run 4–6 people with IDs like `pilot-P01` (separate from main study).
3. After pilot, set `AM_BLOCK_SECONDS=1200`, fix bugs, tag code `v1.0.0`, do not change logic during main study.

---

## Part 2 — Collecting real data (main study, N = 24)

### 2.1 Who participates

- University students or subject pool, age 18+
- Fluent English reader
- **N = 24** (12 on domain D1, 12 on D2 — automatic from assignment CSV)
- Compensation: state amount in consent (e.g. USD 20 for ~75 min)

### 2.2 One participant session — timeline (~75 min)

| Step | Time | What happens |
|------|------|----------------|
| Welcome | 3 min | Explain three teaching modes, not a test of them |
| Consent | 5 min | Sign form; note audio opt-in |
| **Block 1** | ~25 min | Teach → TLX → Quiz (see 2.3) |
| Break | 2 min | Mandatory |
| **Block 2** | ~25 min | Second condition |
| Break | 2 min | |
| **Block 3** | ~25 min | Third condition |
| Interview | 5 min | Four questions in `protocol.md` |
| Debrief + pay | 3 min | Read `debrief.md`; compensation |

They do **not** sit still clicking for 75 minutes straight — there are breaks, questionnaires, and pauses between examples.

### 2.3 Running ONE block (repeat 3 times per person)

**Example:** Participant `chi27-P05`, domain `d1`, first block condition `random`.

1. **Start server** (if not running):

   ```powershell
   cd "c:\SDL2-2.26.3\CHI RESEARCH\adaptive-mocha"
   .\.venv\Scripts\activate
   python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
   ```

2. **Browser:** http://127.0.0.1:8000/

3. **Fill form:**
   - Participant ID: `chi27-P05` (**same ID for all 3 blocks**)
   - Domain: D1 or D2 per CSV
   - Condition: `random` / `fixed` / `adaptive` per CSV for this block number

4. Click **Start teaching block**.

5. **Teaching page** (`/teach`):
   - Timer counts down from `20:00` (if `AM_BLOCK_SECONDS=1200`)
   - Read text(s), click label, optional “why”, **Submit & next**
   - **Fixed / Adaptive:** yellow “Compare these examples” banner may appear
   - **Adaptive only:** gray controller line at bottom
   - **Adaptive only:** at ~8 and ~14 min, a popup asks “how hard does this feel?” (0–10)

6. When timer hits `00:00` → auto redirect to **TLX** (6 sliders, 0–20) → submit.

7. **Quiz** (12 multiple choice) → submit.

8. You return to home page for **next block** (different condition, **same participant ID**).

9. After block 3 → **interview** → **debrief**.

### 2.4 What gets saved (proof data exists)

One file per participant:

```
runs/chi27-P05.sqlite
```

After block 1, the file exists. After all 3 blocks, it contains **3 rows** in `sessions` (one per condition).

Verify after each participant:

```powershell
.\.venv\Scripts\python.exe -c "
import sqlite3
pid = 'chi27-P05'  # change
c = sqlite3.connect(f'runs/{pid}.sqlite')
print('sessions:', c.execute('SELECT condition, domain FROM sessions').fetchall())
print('labels:', c.execute('SELECT COUNT(*) FROM labels').fetchone()[0])
print('tlx:', c.execute('SELECT COUNT(*) FROM tlx').fetchone()[0])
print('quiz items:', c.execute('SELECT COUNT(*) FROM quiz').fetchone()[0])
print('evals:', c.execute('SELECT condition FROM sessions s JOIN classifier_eval e ON s.session_id=e.session_id').fetchall())
"
```

**Healthy session (approximate):**

- 3 sessions (random, fixed, adaptive)
- Dozens to hundreds of `labels` (depends how fast they click)
- 3 `tlx` rows
- ~36 `quiz` rows (12 per block)
- 3 `classifier_eval` rows

### 2.5 Researcher mistakes to avoid

| Mistake | Fix |
|---------|-----|
| Different participant ID each block | **Same** `chi27-Pxx` all 3 times |
| Edited `.env.example` only | Edit **`.env`**, restart server |
| Old browser tab with 20:00 timer | New session from **home page** after restart |
| Used `P05` instead of `chi27-P05` | Analysis won’t find file with `--tag chi27` |
| Included synthetic `mainstudy-*` in analysis | Only `chi27-*.sqlite` for paper |
| Changed code mid-study | Freeze at `v1.0.0`; bugfixes only if critical |

### 2.6 After each participant

- [ ] Mark completed on printed assignment sheet
- [ ] Backup `runs/chi27-Pxx.sqlite` to USB or cloud (encrypted)
- [ ] Save interview notes / audio filename in a log spreadsheet:

| participant_id | date | domain | interviewer | audio_file | notes |
|----------------|------|--------|-------------|------------|-------|

### 2.7 When all 24 are done

You should have exactly:

```
runs/chi27-P01.sqlite
runs/chi27-P02.sqlite
...
runs/chi27-P24.sqlite
```

Do **not** mix in `po1.sqlite`, `p02.sqlite`, or `mainstudy-*.sqlite` for the paper.

---

## Part 3 — Qualitative data (interviews)

1. Transcribe audio (or write bullet notes per question).
2. Two coders independently code using `analysis/qualitative_codebook.md`.
3. Save one CSV per coder per participant:

   ```
   analysis/qualitative_codes/chi27-P01_coderA.csv
   ```

   Columns: `segment_id`, `codes` (comma-separated, e.g. `s.preferred-adaptive,p.felt-adapting`)

4. Run:

   ```powershell
   python analysis/qualitative.py
   ```

5. Report Cohen’s kappa in the paper; use themes in Discussion.

---

## Part 4 — Statistical analysis (numbers for Results)

### 4.1 Run analysis

```powershell
cd "c:\SDL2-2.26.3\CHI RESEARCH\adaptive-mocha"
.\.venv\Scripts\activate
python analysis/analyze.py --tag chi27 --out analysis/output/report_chi27.json
python analysis/figures.py --tag chi27 --out analysis/output/figures_chi27
```

### 4.2 Read the output

Open `analysis/output/report_chi27.json`. For each outcome (`accuracy`, `mean_raw`, `quiz_score`, …):

- **descriptives** — mean/SD per condition (Random, Fixed, Adaptive)
- **contrasts** — pairwise comparisons with `p_holm`, `cohen_dz`

**Hypotheses (from pre-registration):**

- **H1:** Accuracy: Adaptive ≥ Fixed > Random
- **H2:** TLX (`mean_raw`): Adaptive < Fixed (less workload)
- **H3:** Similar pattern on both domains (exploratory)

Write sentences like:

> “Classifier accuracy was highest in the Adaptive condition (M = 0.XX, SD = 0.XX), compared to Fixed (M = …) and Random (M = …). The Adaptive vs Random contrast was significant after Holm correction, t(23) = …, p = …, d_z = ….”

Use **your** numbers from JSON, not examples.

### 4.3 Copy figures into paper folder

```powershell
Copy-Item analysis\output\figures_chi27\*.pdf paper\
```

Create `paper/fig_architecture.pdf` (diagram of system — still required; draw.io or PowerPoint).

---

## Part 5 — Writing the paper (section by section)

File: `paper/paper.tex`. Compile with LaTeX (`pdflatex` + `bibtex`) — see `paper/README.md`.

**Order to write** (easiest for beginners):

### 5.1 Method (write first — mostly before results)

Copy structure from `study/preregistration.md`:

- Participants: N=24, recruitment, inclusion
- Design: within-subjects, 3 conditions, Latin square, domain between-subjects
- Apparatus: Adaptive MOCHA, LLM model name from `.env`
- Procedure: 20 min block + TLX + quiz × 3
- Measures: accuracy on 50-item probe set per domain, NASA-TLX, quiz /12, dwell time
- Analysis: mixed-effects model, Holm-Bonferroni, Cohen’s d_z

### 5.2 System

Explain Random vs Fixed vs Adaptive (see README). Describe Variation Theory, Structural Alignment, load estimator, controller thresholds (0.65 / 0.35). Point to GitHub repo.

Include architecture figure.

### 5.3 Results

Replace every `\chiplaceholder{...}` with values from `report_chi27.json`.

Include figures:

- `fig1_outcomes.pdf` — primary outcomes
- `fig2_controller.pdf` — adaptive trace
- `fig3_tlx_profile.pdf` — TLX breakdown
- `fig4_learning_curve.pdf` — dwell over trials

Add a short paragraph on qualitative themes.

### 5.4 Introduction

1. Teaching concepts to AI is hard; co-adaptation matters.
2. MOCHA + three gaps (LLM, domains, pacing).
3. Your contribution: Adaptive MOCHA + study.
4. One-sentence summary of **actual** findings.

### 5.5 Related Work

Read and cite from `paper/references.bib` — especially MOCHA (2024), Variation Theory, Structural Alignment, Cognitive Load, machine teaching.

### 5.6 Discussion

- Interpret H1/H2/H3 honestly (null results are OK if reported clearly).
- Design implications (3 bullets in scaffold).
- Limitations: N, student sample, hand-authored datasets (72 seeds), single LLM, lab setting.
- **Do not** claim synthetic pilot data.

### 5.7 Abstract (last)

~150 words: problem, method, key numeric results, takeaway.

### 5.8 Title, authors, ACM format

- Switch `anonymous=true` to `false` when submitting non-anonymous version.
- Use official CHI 2027 `acmart` template when released; migrate prose from current scaffold.

---

## Part 6 — Submission package (CHI checklist)

### 6.1 Required artifacts

- [ ] PDF paper (~10 pages + references)
- [ ] Supplementary material (optional): qualitative quotes, extra figures
- [ ] Open-source link (GitHub public, Apache-2.0)
- [ ] OSF link (pre-registration + anonymized data)
- [ ] Reproducibility: `REPRODUCIBILITY.md` in repo

### 6.2 Anonymized data release (OSF)

Export from SQLite:

- Remove any free-text that could identify participants (rationale fields — check IRB)
- Release: probe sets, quiz items, aggregated CSV, analysis script output
- Do **not** release raw audio without consent scope

### 6.3 Internal review before submit

- [ ] Supervisor / co-author reads full draft
- [ ] Spell-check; all figures referenced exist
- [ ] Every number in abstract matches Results
- [ ] No `mainstudy` or `synthetic` mentioned as empirical results
- [ ] Ethics approval stated in paper

### 6.4 Submit

- Portal: ACM CHI 2027 (verify deadline, typically September)
- Keep submission confirmation email

---

## Part 7 — Calendar (suggested)

| Weeks | Focus |
|-------|--------|
| 1 | IRB submit; OSF register; OpenAI self-test; write Method draft |
| 2–3 | IRB approval; pilot N=4–6; freeze v1.0.0 |
| 4–9 | Main study: ~4 participants/week → 24 total |
| 10 | Interviews coded; `analyze.py` + `figures.py` |
| 11–12 | Write Results, Intro, Discussion; figures polish |
| 13 | Internal review; abstract; submit CHI |

Adjust if IRB is slow — start writing Method/System while waiting.

---

## Part 8 — Quick command reference

```powershell
# Setup
cd "c:\SDL2-2.26.3\CHI RESEARCH\adaptive-mocha"
.\.venv\Scripts\activate

# Assignment sheet
python scripts/assign_order.py --n 24 --id-prefix chi27 --out study/assignment_main.csv

# Run study server
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000

# Check config
curl http://127.0.0.1:8000/health

# After 24 participants
python analysis/analyze.py --tag chi27 --out analysis/output/report_chi27.json
python analysis/figures.py --tag chi27 --out analysis/output/figures_chi27

# Tests
pytest -q
```

---

## Part 9 — What “done” looks like

You are ready to submit when:

1. IRB approved and cited.
2. 24 files `runs/chi27-P01.sqlite` … `chi27-P24.sqlite` exist.
3. `report_chi27.json` produced from **only** those files.
4. `paper.tex` has no placeholders; figures are from `figures_chi27`.
5. OSF + GitHub links in the paper.
6. A colleague has read it and you can explain every figure in one sentence.

That is a complete, honest CHI submission — not perfect, but **publishable** if the study was run cleanly and results are reported transparently.
