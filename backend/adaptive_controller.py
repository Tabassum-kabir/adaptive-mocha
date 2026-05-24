"""Rule-based adaptive pacing controller.

Given a stream of `Trial` candidates and the current cognitive-load estimate,
the controller chooses:

  - **difficulty**: target difficulty band (easy / medium / hard).
  - **batch_size**: how many examples to show per trial (2-4).
  - **inter_trial_spacing_ms**: pause after a label submission before the next
    trial appears.

The policy is intentionally simple and pre-registered so we can publish the
*rule* alongside the results. CHI reviewers reasonably distrust black-box
adaptation; a transparent rule we can audit per participant is more credible
than a learned policy trained on this small a dataset.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .alignment import Trial


@dataclass
class ControllerDecision:
    difficulty_band: str  # "easy" | "medium" | "hard"
    batch_size: int      # 2..4
    inter_trial_ms: int  # 0..2500
    rationale: str       # human-readable reason, logged for paper figures
    load: float          # the load estimate that drove the decision


@dataclass
class AdaptiveController:
    """Policy used by the MOCHA-Adaptive condition.

    Hyper-parameters here are pre-registered in `study/preregistration.md`.
    """
    initial_difficulty: str = "easy"
    high_load_threshold: float = 0.65
    low_load_threshold: float = 0.35

    last_difficulty: str = field(default="easy", init=False)
    last_batch_size: int = field(default=2, init=False)

    def decide(self, load: float) -> ControllerDecision:
        if load >= self.high_load_threshold:
            band = "easy"
            batch = 2
            pause_ms = 1500
            reason = (
                f"Load {load:.2f} >= {self.high_load_threshold:.2f}: "
                "step down to easy, smallest batch, longest pause."
            )
        elif load <= self.low_load_threshold:
            band = "hard"
            batch = 3
            pause_ms = 250
            reason = (
                f"Load {load:.2f} <= {self.low_load_threshold:.2f}: "
                "push toward boundary-near hard items, slightly larger batch."
            )
        else:
            band = "medium"
            batch = 2
            pause_ms = 750
            reason = f"Load {load:.2f} in moderate band: medium difficulty, default pause."

        self.last_difficulty = band
        self.last_batch_size = batch
        return ControllerDecision(
            difficulty_band=band,
            batch_size=batch,
            inter_trial_ms=pause_ms,
            rationale=reason,
            load=load,
        )

    @staticmethod
    def filter_trials(trials: Iterable[Trial], band: str) -> list[Trial]:
        if band == "easy":
            return [t for t in trials if t.difficulty < 0.45]
        if band == "hard":
            return [t for t in trials if t.difficulty >= 0.6]
        return [t for t in trials if 0.35 <= t.difficulty < 0.75]


@dataclass
class FixedController:
    """The non-adaptive MOCHA-Fixed and Random conditions both use this.

    Difficulty band is held constant at "medium". Batch size and pause are
    fixed at pre-registered values so the only thing that varies across
    conditions is the *teaching strategy*, not the pacing.
    """

    band: str = "medium"
    batch_size: int = 2
    inter_trial_ms: int = 800

    def decide(self, load: float | None = None) -> ControllerDecision:
        return ControllerDecision(
            difficulty_band=self.band,
            batch_size=self.batch_size,
            inter_trial_ms=self.inter_trial_ms,
            rationale="Fixed policy (non-adaptive).",
            load=load or 0.0,
        )

    @staticmethod
    def filter_trials(trials: Iterable[Trial], band: str = "medium") -> list[Trial]:
        return AdaptiveController.filter_trials(trials, band)
