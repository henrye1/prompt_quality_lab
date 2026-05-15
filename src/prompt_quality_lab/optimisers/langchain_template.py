"""LangChain PromptTemplate + ChatAnthropic helper.

Exposes `AVAILABLE` so the UI can render a friendly message when LangChain
isn't installed rather than crashing on import.
"""
from __future__ import annotations

try:
    from langchain_anthropic import ChatAnthropic
    from langchain_core.prompts import PromptTemplate

    AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when langchain is missing
    ChatAnthropic = None  # type: ignore[assignment, misc]
    PromptTemplate = None  # type: ignore[assignment, misc]
    AVAILABLE = False

__all__ = ["AVAILABLE", "ChatAnthropic", "PromptTemplate"]
