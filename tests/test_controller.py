from backend.adaptive_controller import AdaptiveController, FixedController
from backend.cognitive_load import CognitiveLoadEstimator, LoadSample


def test_adaptive_steps_down_on_high_load():
    c = AdaptiveController()
    d = c.decide(load=0.9)
    assert d.difficulty_band == "easy"
    assert d.batch_size == 2
    assert d.inter_trial_ms >= 1000


def test_adaptive_pushes_up_on_low_load():
    c = AdaptiveController()
    d = c.decide(load=0.1)
    assert d.difficulty_band == "hard"
    assert d.inter_trial_ms <= 500


def test_fixed_is_constant():
    c = FixedController()
    d1 = c.decide(load=0.1)
    d2 = c.decide(load=0.9)
    assert d1.difficulty_band == d2.difficulty_band == "medium"
    assert d1.batch_size == d2.batch_size


def test_load_estimator_baseline():
    est = CognitiveLoadEstimator(baseline_n=3)
    for ms in [400, 500, 600]:
        est.add(LoadSample(dwell_ms=ms))
    assert est.baseline_dwell is not None
    est.add(LoadSample(dwell_ms=2000))
    out = est.estimate()
    assert out["load"] >= 0.0 and out["load"] <= 1.0
    assert "dwell_component" in out
