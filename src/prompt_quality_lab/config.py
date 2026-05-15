"""Configuration: model IDs, defaults, environment loading."""
from __future__ import annotations

from dotenv import load_dotenv

# Load .env once at import. Idempotent and safe if .env is missing.
load_dotenv()

AVAILABLE_MODELS: list[str] = [
    "claude-sonnet-4-6",
    "claude-opus-4-7",
    "claude-haiku-4-5-20251001",
]

DEFAULT_MODEL: str = AVAILABLE_MODELS[0]
