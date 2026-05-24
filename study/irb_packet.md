# IRB Submission Packet — Adaptive MOCHA

**Protocol Title:** Adaptive MOCHA: Co-Adaptive Concept Teaching with Cognitive-Load-Aware Pacing

**Principal Investigator:** _[PI name and affiliation]_
**Study Personnel:** _[student investigator(s)]_
**Funding Source:** _[grant or unfunded]_
**Anticipated Submission Venue:** ACM CHI 2027

**Review Category Requested:** Expedited (Category 7 — research on group characteristics or behavior using surveys, interviews, or observation of public behavior).

## 1. Background and Rationale

We extend MOCHA (Gebreegziabher, Yang, Glassman, Li, 2024; arXiv:2409.16561), an interactive machine teaching system grounded in Variation Theory and Structural Alignment Theory. The original study reported three explicit limitations: a short 25-minute interaction window, only two example domains, and only a neuro-symbolic model. We add a Cognitive-Load-Aware adaptive pacing controller and replace the neuro-symbolic backend with an LLM-based classifier. The aim is to test whether adaptive pacing improves both post-teaching classifier accuracy and learner experience.

## 2. Objectives and Hypotheses

- **RQ1:** Does cognitive-load-aware adaptive pacing improve post-teaching model accuracy versus fixed-pace MOCHA and a random baseline?
- **RQ2:** Does adaptive pacing improve learner experience (NASA-TLX, fatigue, concept understanding) without sacrificing teaching efficiency?
- **RQ3:** Do the gains from Variation Theory + Structural Alignment Theory transfer to LLM classifiers?

## 3. Participants

- **Target N:** 24 (12 per domain), university students 18+.
- **Recruitment:** University subject pool, mailing lists, flyers in computer science and psychology departments. No coercion; participation is voluntary.
- **Inclusion:** 18+, fluent English reader (study text is English), self-reported normal or corrected-to-normal vision.
- **Exclusion:** Co-authors, lab members closely involved with the project.
- **Compensation:** USD 20 (or local equivalent) for a ~75-minute session.

## 4. Procedure

1. Online or in-lab consent (5 min).
2. Pre-task questionnaire: demographics, prior ML/labeling experience, baseline NASA-TLX (5 min).
3. Three teaching blocks of ~20 minutes each (Random, MOCHA-Fixed, MOCHA-Adaptive) presented in counterbalanced order using a 6-order Latin square. Each block ends with a 2-minute NASA-TLX and a 3-minute concept-understanding quiz.
4. Semi-structured exit interview (5 min, audio recorded with consent).
5. Debrief and compensation (5 min).

Total per-participant time: ~75 minutes.

## 5. Risks

- **Minimal psychological risk:** the task involves labeling movie reviews or argument paragraphs. Material is screened to exclude profanity, slurs, graphic violence, and sexual content.
- **Fatigue:** mitigated by mandatory 2-minute breaks between blocks and an opt-out option at any time.
- **Privacy:** no PII is collected in study logs; consent forms are stored separately from data; audio is transcribed and deleted within 30 days.

## 6. Benefits

No direct benefits beyond compensation. Indirect: contribution to the science of human-AI collaboration.

## 7. Data Handling

- All study data stored on a single password-protected PC in `runs/` (SQLite). No cloud sync.
- LLM API calls send only system-curated examples, never participant free-text.
- Demographic data anonymized at collection; participant IDs are random UUIDs.
- Data shared on OSF after de-identification (no demographics linked to behavioral data unless aggregated).
- Retained 5 years post-publication, then deleted.

## 8. Conflict of Interest

None declared.

## 9. Attachments

- `consent.md` — informed consent form
- `protocol.md` — operational protocol with researcher script
- `debrief.md` — debrief sheet
- `quiz_specs.md` — concept-understanding quiz items per domain
- `tlx_form.md` — NASA-TLX implementation
- `recruitment_flyer.md` — recruitment text
