"""Rolling cognitive-load estimator.

Three signals feed a single normalised load score in [0, 1]:

1. **Dwell time** per trial, z-scored against the participant's own baseline.
2. **Calibration-probe accuracy** on a small set of easy items the system
   slips in to detect early fatigue (Paas et al., 2003 use a similar slip).
3. **Self-reported single-item load** from the mid-block micro-TLX probe.

The estimator is intentionally cheap and explainable: every component is
visible in the log, and the controller's decisions can be reconstructed
offline from the SQLite events table.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from statistics import median, pstdev
from typing import Deque


@dataclass
class LoadSample:
    dwell_ms: int
    correct_calibration: bool | None = None
    self_report: float | None = None  # 0-10 if available


@dataclass
class CognitiveLoadEstimator:
    window: int = 8
    baseline_n: int = 5
    samples: Deque[LoadSample] = field(default_factory=lambda: deque(maxlen=64))
    baseline_dwell: float | None = None
    last_self_report: float | None = None

    def add(self, sample: LoadSample) -> None:
        self.samples.append(sample)
        if sample.self_report is not None:
            self.last_self_report = sample.self_report
        if self.baseline_dwell is None and len(self.samples) >= self.baseline_n:
            dwells = [s.dwell_ms for s in list(self.samples)[: self.baseline_n] if s.dwell_ms > 0]
            if dwells:
                self.baseline_dwell = float(median(dwells))

    def _dwell_component(self) -> float:
        recent = list(self.samples)[-self.window :]
        dwells = [s.dwell_ms for s in recent if s.dwell_ms > 0]
        if not dwells or self.baseline_dwell is None:
            return 0.5
        med = float(median(dwells))
        sd = float(pstdev(dwells)) or 1.0
        z = (med - self.baseline_dwell) / max(sd, 1.0)
        return max(0.0, min(1.0, 0.5 + 0.5 * (z / 2.5)))

    def _calibration_component(self) -> float:
        cals = [s.correct_calibration for s in self.samples if s.correct_calibration is not None]
        if not cals:
            return 0.5
        recent = cals[-self.window :]
        miss_rate = 1.0 - (sum(int(b) for b in recent) / len(recent))
        return max(0.0, min(1.0, miss_rate))

    def _self_report_component(self) -> float:
        if self.last_self_report is None:
            return 0.5
        return max(0.0, min(1.0, float(self.last_self_report) / 10.0))

    def estimate(self) -> dict[str, float]:
        d = self._dwell_component()
        c = self._calibration_component()
        s = self._self_report_component()
        load = 0.45 * d + 0.35 * c + 0.20 * s
        return {
            "load": round(load, 3),
            "dwell_component": round(d, 3),
            "calibration_component": round(c, 3),
            "self_report_component": round(s, 3),
            "n_samples": len(self.samples),
        }
