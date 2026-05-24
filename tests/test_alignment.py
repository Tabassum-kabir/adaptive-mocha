from backend.alignment import build_trials, _diff_axes
from backend.domains import DOMAINS, load_seed


def test_pairs_differ_on_exactly_one_axis():
    for d in DOMAINS.values():
        seed = load_seed(d)
        trials = build_trials(seed, d, pairs_per_axis=3, triples=False)
        assert trials, f"no trials for {d.name}"
        for t in trials:
            if len(t.items) == 2:
                diff = _diff_axes(t.items[0], t.items[1])
                assert diff == [t.contrast_axis], (t.items, diff, t.contrast_axis)


def test_triples_walk_one_axis():
    for d in DOMAINS.values():
        seed = load_seed(d)
        trials = build_trials(seed, d, pairs_per_axis=0, triples=True)
        triples = [t for t in trials if len(t.items) == 3]
        for t in triples:
            for a, b in [(0, 1), (1, 2)]:
                diff = _diff_axes(t.items[a], t.items[b])
                if diff:
                    assert t.contrast_axis in diff, (diff, t.contrast_axis)


def test_trials_difficulty_sorted():
    for d in DOMAINS.values():
        seed = load_seed(d)
        trials = build_trials(seed, d)
        diffs = [t.difficulty for t in trials]
        assert diffs == sorted(diffs)
