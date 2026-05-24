# Operational Protocol — Adaptive MOCHA Lab Session

Duration: ~75 minutes per participant. One participant at a time.

## Materials checklist (before session)

- [ ] PC running `adaptive-mocha` with API key set in `.env`.
- [ ] Empty `runs/<participant_id>.sqlite` database, participant ID generated.
- [ ] Counterbalancing assignment confirmed (`scripts/assign_order.py`).
- [ ] Consent form (paper or online).
- [ ] Compensation envelope or receipt template.
- [ ] Audio recorder (or recorder app), charged.
- [ ] Researcher script printed.

## Researcher script

### 1. Welcome (3 min)

> "Thanks for coming. Today you'll teach a computer to recognize a concept. You'll do this three different ways. Each way takes about 20 minutes. Between each one, we'll ask you about how the task felt and give you a short quiz. At the end I have a few questions for you. The whole session is about an hour and 15 minutes. Any questions before we start?"

### 2. Consent (5 min)

Walk through the consent form. Confirm 18+. Confirm audio recording opt-in.

### 3. Pre-task questionnaire (5 min)

Open `frontend/pre_questionnaire.html` (served at `/pre`). Fields:

- Age (18-24, 25-34, 35-44, 45-54, 55+, prefer not to say).
- Gender (free text, optional).
- Native language English (yes/no).
- Prior ML/data labeling experience (none / casual / professional).
- Baseline NASA-TLX.

### 4. Practice block (3 min)

Run the practice condition (`/teach?condition=practice`). 5 trivially easy examples. Confirm the participant understands the UI.

### 5. Teaching blocks (3 × 22 min = 66 min including TLX + quiz)

For each block (in counterbalanced order):

1. Start the teaching session at `/teach?condition=<random|fixed|adaptive>&participant=<id>&domain=<d1|d2>`.
2. Teaching runs for 20 minutes with a visible countdown.
3. NASA-TLX appears automatically (2 min).
4. Concept-understanding quiz appears automatically (3 min).
5. 2-minute mandatory break (timer; researcher can chat or stay silent).

### 6. Exit interview (5 min, audio if consented)

Semi-structured prompts:

1. Which of the three teaching modes felt most natural? Why?
2. Were there moments when you felt the system was helping you think more clearly? Were there moments when it got in the way?
3. Did you notice the system changing how fast it gave you examples, or how hard they were? If so, how did that feel?
4. What would you want to change about the way the system presented examples?

### 7. Debrief and compensation (3 min)

Read `debrief.md` aloud. Hand over the compensation. Thank them.

## Researcher checklist after session

- [ ] Database file zipped and moved to `runs/archive/`.
- [ ] Audio transcribed within 7 days, recording deleted.
- [ ] Counterbalancing sheet updated.
- [ ] Adverse-event log updated (even if none).

## Stopping rules

- Participant requests to stop → stop immediately, mark block as withdrawn, pay full compensation.
- System error during a block → log the error, attempt one restart, otherwise end the session and pay full compensation; data marked as incomplete.
- Visible distress → researcher offers a break, then offers to stop.
