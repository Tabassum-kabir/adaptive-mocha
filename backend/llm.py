"""Provider-agnostic LLM client with on-disk cache and a token-budget guard.

Providers:
    - openai     (gpt-4o-mini etc., real API)
    - anthropic  (claude-3-5-haiku, real API)
    - ollama     (local CPU model)
    - mock       (deterministic; no network, used for dev / smoke tests / CI)

All calls go through :func:`complete` which returns a dict with
``{text, usage, provider, cached}``.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .config import CFG


@dataclass
class LLMUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class BudgetExceeded(RuntimeError):
    pass


class _UsageLedger:
    """Tracks cumulative tokens for the running process so a runaway sampling
    bug cannot quietly burn through API credits during a study night."""

    def __init__(self, cap: int) -> None:
        self.cap = cap
        self.used = 0

    def record(self, total: int) -> None:
        self.used += int(total)
        if self.used > self.cap:
            raise BudgetExceeded(
                f"Token budget exhausted: used {self.used} of cap {self.cap}"
            )


LEDGER = _UsageLedger(cap=CFG.token_budget)


def _cache_key(provider: str, model: str, messages: list[dict[str, str]], **kw: Any) -> str:
    blob = json.dumps(
        {"provider": provider, "model": model, "messages": messages, "kw": kw},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _cache_path(key: str) -> Path:
    return CFG.cache_dir / f"{key}.json"


def _cache_get(key: str) -> dict[str, Any] | None:
    p = _cache_path(key)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _cache_put(key: str, value: dict[str, Any]) -> None:
    try:
        _cache_path(key).write_text(
            json.dumps(value, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        pass


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def complete(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int = 512,
    json_mode: bool = False,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Single-turn completion. ``messages`` is OpenAI-style list of role/content."""
    provider = CFG.provider

    if provider == "openai":
        model = CFG.openai_model
    elif provider == "anthropic":
        model = CFG.anthropic_model
    elif provider == "ollama":
        model = CFG.ollama_model
    else:
        model = "mock-v1"

    key = _cache_key(
        provider, model, messages,
        temperature=temperature, max_tokens=max_tokens, json_mode=json_mode,
    )
    if use_cache:
        cached = _cache_get(key)
        if cached is not None:
            cached["cached"] = True
            return cached

    if provider == "openai":
        result = _call_openai(messages, model, temperature, max_tokens, json_mode)
    elif provider == "anthropic":
        result = _call_anthropic(messages, model, temperature, max_tokens, json_mode)
    elif provider == "ollama":
        result = _call_ollama(messages, model, temperature, max_tokens, json_mode)
    else:
        result = _call_mock(messages, model, temperature, max_tokens, json_mode)

    LEDGER.record(result["usage"]["total_tokens"])
    result["cached"] = False
    if use_cache:
        _cache_put(key, result)
    return result


# ----------------------------------------------------------------------------
# Provider implementations
# ----------------------------------------------------------------------------

def _call_openai(messages, model, temperature, max_tokens, json_mode) -> dict[str, Any]:
    if not CFG.openai_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    headers = {"Authorization": f"Bearer {CFG.openai_key}", "Content-Type": "application/json"}
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    with httpx.Client(timeout=60.0) as client:
        r = client.post("https://models.inference.ai.azure.com/chat/completions", headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return {
        "text": text,
        "provider": "openai",
        "model": model,
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", _approx_tokens(json.dumps(messages))),
            "completion_tokens": usage.get("completion_tokens", _approx_tokens(text)),
            "total_tokens": usage.get("total_tokens", _approx_tokens(json.dumps(messages)) + _approx_tokens(text)),
        },
    }


def _call_anthropic(messages, model, temperature, max_tokens, json_mode) -> dict[str, Any]:
    if not CFG.anthropic_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    system = ""
    converted: list[dict[str, str]] = []
    for m in messages:
        if m["role"] == "system":
            system = m["content"]
        else:
            converted.append({"role": m["role"], "content": m["content"]})
    headers = {
        "x-api-key": CFG.anthropic_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": converted,
    }
    if system:
        body["system"] = system
    with httpx.Client(timeout=60.0) as client:
        r = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
    text = "".join(part.get("text", "") for part in data.get("content", []) if part.get("type") == "text")
    usage = data.get("usage", {})
    return {
        "text": text,
        "provider": "anthropic",
        "model": model,
        "usage": {
            "prompt_tokens": usage.get("input_tokens", _approx_tokens(json.dumps(messages))),
            "completion_tokens": usage.get("output_tokens", _approx_tokens(text)),
            "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
            or (_approx_tokens(json.dumps(messages)) + _approx_tokens(text)),
        },
    }


def _call_ollama(messages, model, temperature, max_tokens, json_mode) -> dict[str, Any]:
    body = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    if json_mode:
        body["format"] = "json"
    with httpx.Client(timeout=120.0) as client:
        r = client.post(f"{CFG.ollama_host}/api/chat", json=body)
        r.raise_for_status()
        data = r.json()
    text = data.get("message", {}).get("content", "")
    pt = data.get("prompt_eval_count", _approx_tokens(json.dumps(messages)))
    ct = data.get("eval_count", _approx_tokens(text))
    return {
        "text": text,
        "provider": "ollama",
        "model": model,
        "usage": {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct},
    }


def _call_mock(messages, model, temperature, max_tokens, json_mode) -> dict[str, Any]:
    """Deterministic mock used for smoke tests and offline dev.

    For the CLASSIFY task the mock does **token-overlap nearest-example
    retrieval** over the TEACH block embedded in the user message. This
    means: as the participant teaches more examples, the mock starts to
    answer more like the gold labels, and the *teaching strategy* (which
    examples it sees) genuinely affects accuracy. That keeps the simulator
    useful as a pipeline pre-pilot without pretending to be a real LLM.
    """
    sys_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
    user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")
    tag = "generic"
    for candidate in ("VARIATION", "ALIGNMENT", "CLASSIFY", "GENERATE_PROBE", "DIFFICULTY"):
        if candidate in sys_msg or candidate in user_msg:
            tag = candidate
            break

    if tag == "CLASSIFY":
        label = _mock_classify(user_msg)
        h = int(hashlib.sha1(user_msg.encode("utf-8")).hexdigest(), 16)
        conf = 0.5 + (h % 50) / 100.0
        text = json.dumps({"label": label, "confidence": conf})
    elif tag == "VARIATION":
        text = json.dumps({
            "variations": [
                {"text": "[VAR] " + user_msg[:80] + " (intensified)", "expected_label": "positive"},
                {"text": "[VAR] " + user_msg[:80] + " (hedged)", "expected_label": "mixed"},
                {"text": "[VAR] " + user_msg[:80] + " (negated)", "expected_label": "negative"},
            ]
        })
    elif tag == "ALIGNMENT":
        text = json.dumps({
            "feature_axis": "intensity",
            "pairs": [[0, 1], [2, 3]],
        })
    elif tag == "DIFFICULTY":
        h = int(hashlib.sha1(user_msg.encode("utf-8")).hexdigest(), 16) % 100
        text = json.dumps({"difficulty": h / 100.0})
    else:
        text = "OK"

    return {
        "text": text,
        "provider": "mock",
        "model": model,
        "usage": {
            "prompt_tokens": _approx_tokens(json.dumps(messages)),
            "completion_tokens": _approx_tokens(text),
            "total_tokens": _approx_tokens(json.dumps(messages)) + _approx_tokens(text),
        },
    }


def reset_ledger(cap: int | None = None) -> None:
    LEDGER.used = 0
    if cap is not None:
        LEDGER.cap = cap


# ----------------------------------------------------------------------------
# Mock helpers
# ----------------------------------------------------------------------------

import re as _re


_TEACH_RE = _re.compile(
    r"- TEACH \| text: ['\"](?P<text>.+?)['\"] \| label: (?P<label>[a-zA-Z]+)"
)
_CLASSIFY_RE = _re.compile(r"CLASSIFY: ['\"](?P<text>.+?)['\"]")
_STOPWORDS = {
    "the", "a", "an", "is", "it", "of", "and", "to", "in", "on", "for", "but",
    "or", "with", "that", "this", "as", "at", "be", "by", "are", "was", "were",
    "i", "he", "she", "we", "they", "you", "me", "my", "our", "your", "their",
    "not", "no", "so", "if", "than", "then", "from", "into", "about", "over",
    "out", "up", "down", "very", "just", "more", "less", "most", "least", "all",
    "any", "some", "every", "each", "much", "many", "few", "still", "only",
    "even", "ever", "never", "always", "also", "too", "again", "almost",
    "would", "could", "should", "have", "has", "had", "do", "does", "did",
}


def _tokenize(s: str) -> set[str]:
    return {w for w in _re.findall(r"[a-zA-Z]+", s.lower()) if w not in _STOPWORDS and len(w) > 2}


def _mock_classify(user_msg: str) -> str:
    """Token-overlap NN against the TEACH block extracted from the prompt."""
    teach = list(_TEACH_RE.finditer(user_msg))
    classify_match = _CLASSIFY_RE.search(user_msg)
    if not teach or not classify_match:
        labels = ["positive", "negative", "mixed", "strong", "weak", "borderline"]
        return labels[int(hashlib.sha1(user_msg.encode("utf-8")).hexdigest(), 16) % len(labels)]
    target = _tokenize(classify_match.group("text"))
    best_label = None
    best_score = -1.0
    for m in teach:
        toks = _tokenize(m.group("text"))
        if not toks:
            continue
        inter = len(target & toks)
        union = len(target | toks) or 1
        score = inter / union
        if score > best_score:
            best_score = score
            best_label = m.group("label").lower()
    if best_label is None or best_score == 0.0:
        labels_seen = [m.group("label").lower() for m in teach]
        return max(set(labels_seen), key=labels_seen.count)
    return best_label
