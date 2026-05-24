from backend.domains import DOMAINS, load_probe, load_quiz, load_seed


def test_domains_load():
    assert set(DOMAINS) == {"d1", "d2"}
    for d in DOMAINS.values():
        seed = load_seed(d)
        probe = load_probe(d)
        quiz = load_quiz(d)
        assert len(seed) >= 60, f"{d.name} seed too small: {len(seed)}"
        assert len(probe) >= 40, f"{d.name} probe too small: {len(probe)}"
        assert len(quiz) == 12, f"{d.name} quiz must have exactly 12 items"
        for ex in seed:
            assert ex["label"] in d.labels, ex
            assert "features" in ex, ex
            assert "difficulty" in ex, ex
        for ex in probe:
            assert ex["label"] in d.labels, ex
        for q in quiz:
            assert q["answer"] in d.labels, q
            assert set(q["options"]).issubset(d.labels), q


def test_quiz_disjoint_from_probe():
    for d in DOMAINS.values():
        probe_texts = {ex["text"] for ex in load_probe(d)}
        for q in load_quiz(d):
            assert q["text"] not in probe_texts, (
                f"{d.name} quiz item {q['id']} leaks into probe set"
            )


def test_seed_disjoint_from_probe():
    for d in DOMAINS.values():
        seed_texts = {ex["text"] for ex in load_seed(d)}
        probe_texts = {ex["text"] for ex in load_probe(d)}
        assert not (seed_texts & probe_texts), f"{d.name} seed/probe overlap"
