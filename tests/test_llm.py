from backend import llm
from backend.llm import LEDGER, BudgetExceeded, reset_ledger


def test_mock_classify_uses_taught_examples():
    reset_ledger(cap=10_000_000)
    messages = [
        {"role": "system", "content": "[CLASSIFY task]"},
        {
            "role": "user",
            "content": (
                "- TEACH | text: 'A wonderful joyful triumph.' | label: positive\n"
                "- TEACH | text: 'Awful boring waste.' | label: negative\n"
                "\nCLASSIFY: 'A wonderful triumph that I loved.'"
            ),
        },
    ]
    out = llm.complete(messages, use_cache=False)
    assert out["provider"] == "mock"
    import json
    parsed = json.loads(out["text"])
    assert parsed["label"] == "positive"


def test_mock_cache_hits():
    reset_ledger(cap=10_000_000)
    messages = [
        {"role": "system", "content": "[CLASSIFY task]"},
        {"role": "user", "content": "- TEACH | text: 'great' | label: positive\nCLASSIFY: 'great'"},
    ]
    a = llm.complete(messages)
    b = llm.complete(messages)
    assert b["cached"] is True
    assert a["text"] == b["text"]


def test_budget_cap():
    reset_ledger(cap=50)
    messages = [
        {"role": "system", "content": "[CLASSIFY task]"},
        {"role": "user", "content": "- TEACH | text: 'x' | label: positive\nCLASSIFY: 'x'"},
    ]
    try:
        for i in range(50):
            llm.complete(
                [
                    {"role": "system", "content": "[CLASSIFY task]"},
                    {
                        "role": "user",
                        "content": f"- TEACH | text: 'x{i}' | label: positive\nCLASSIFY: 'x{i}'",
                    },
                ],
                use_cache=False,
            )
    except BudgetExceeded:
        pass
    else:
        raise AssertionError("budget cap did not fire")
    reset_ledger(cap=10_000_000)
