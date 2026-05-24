"""Centralised configuration loaded from environment / .env.

Keeping all knobs in one place makes the pre-registration table easy to audit.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
RUNS_DIR = REPO_ROOT / "runs"
RUNS_DIR.mkdir(exist_ok=True)


def _int(name: str, default: int) -> int:
    v = os.environ.get(name)
    try:
        return int(v) if v is not None and v != "" else default
    except ValueError:
        return default


@dataclass(frozen=True)
class Config:
    provider: str = os.environ.get("AM_PROVIDER", "mock").lower()
    openai_key: str = os.environ.get("OPENAI_API_KEY", "")
    openai_model: str = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    anthropic_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.environ.get(
        "ANTHROPIC_MODEL", "claude-3-5-haiku-20241022"
    )
    ollama_host: str = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    ollama_model: str = os.environ.get("OLLAMA_MODEL", "phi3:mini")

    token_budget: int = _int("AM_TOKEN_BUDGET", 200_000)
    block_seconds: int = _int("AM_BLOCK_SECONDS", 1200)
    practice_seconds: int = _int("AM_PRACTICE_SECONDS", 180)
    random_seed: int = _int("AM_RANDOM_SEED", 20260517)

    cache_dir: Path = REPO_ROOT / "analysis" / "cache" / "llm"


CFG = Config()
CFG.cache_dir.mkdir(parents=True, exist_ok=True)
