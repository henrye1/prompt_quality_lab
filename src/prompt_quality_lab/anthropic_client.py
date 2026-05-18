"""Thin wrapper around the Anthropic SDK. All API calls flow through here."""
from __future__ import annotations

import sys
import time

from anthropic import Anthropic, RateLimitError

from prompt_quality_lab.config import DEFAULT_MODEL

_MAX_RETRIES = 5
_BACKOFF_CAP_S = 60.0

# Default sampling temperature for every call. The Anthropic API has no `seed`
# parameter (unlike OpenAI); temperature=0 is the most reproducible setting the
# API exposes. Tabs that need diversity (e.g. variant generation) override this
# explicitly per call.
DEFAULT_TEMPERATURE = 0.0

# Default per-response token budget. Bumped from 2048 because long prompts
# (especially credit-paper-sized) were getting silently truncated mid-rewrite.
# 8192 covers ~6000 words — enough for any realistic prompt-improver / DSPy
# / LangChain output. Anthropic charges per output token *used*, not per
# max_tokens, so a generous cap is safe.
DEFAULT_MAX_TOKENS = 8192


def _retry_after_seconds(err: RateLimitError, attempt: int) -> float:
    """Prefer the server's retry-after hint; otherwise exponential backoff (capped)."""
    response = getattr(err, "response", None)
    headers = getattr(response, "headers", None)
    retry_after = headers.get("retry-after") if headers is not None else None
    if retry_after is not None:
        try:
            return min(float(retry_after), _BACKOFF_CAP_S)
        except (TypeError, ValueError):
            pass
    return min(2.0 ** attempt, _BACKOFF_CAP_S)


def call_claude(
    client: Anthropic,
    prompt: str,
    model: str = DEFAULT_MODEL,
    system: str | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
) -> str:
    """Single-turn Claude call. Retries on 429 with backoff. Returns assistant text.

    `temperature` defaults to 0.0 for reproducibility. Callers that want diverse
    output (e.g. variant generation) should pass a higher value explicitly.

    If the response is truncated because `max_tokens` was reached, a warning is
    printed to stderr (visible in the terminal running Streamlit). Callers that
    need to surface this in the UI should use `call_claude_detailed` instead.
    """
    text, _ = call_claude_detailed(
        client, prompt, model=model, system=system, max_tokens=max_tokens, temperature=temperature
    )
    return text


def call_claude_detailed(
    client: Anthropic,
    prompt: str,
    model: str = DEFAULT_MODEL,
    system: str | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
) -> tuple[str, str]:
    """Like `call_claude` but also returns `stop_reason` so callers can detect
    truncation (`stop_reason == "max_tokens"`) and warn the user."""
    for attempt in range(_MAX_RETRIES):
        try:
            msg = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system or "You are a helpful assistant.",
                messages=[{"role": "user", "content": prompt}],
            )
            stop_reason = getattr(msg, "stop_reason", "") or ""
            if stop_reason == "max_tokens":
                print(
                    f"[anthropic_client] WARNING: response truncated at max_tokens={max_tokens}. "
                    "Increase the cap or shorten the prompt.",
                    file=sys.stderr,
                )
            return msg.content[0].text, stop_reason
        except RateLimitError as err:
            if attempt == _MAX_RETRIES - 1:
                raise
            time.sleep(_retry_after_seconds(err, attempt))
    raise RuntimeError("unreachable")


def evaluate_against_expected(
    client: Anthropic,
    prompt: str,
    expected: str,
    model: str = DEFAULT_MODEL,
) -> tuple[str, float | None]:
    """Run the prompt, then ask Claude to score actual vs expected (0-10).

    Returns (actual_output, score_or_None). Score is None when expected is empty
    or when the judge response can't be parsed as a number.
    """
    actual = call_claude(client, prompt, model=model)
    if not expected.strip():
        return actual, None
    judge = (
        "You are a strict evaluator. Compare the ACTUAL response to the "
        "EXPECTED response for semantic equivalence and quality.\n\n"
        f'EXPECTED:\n"""\n{expected}\n"""\n\n'
        f'ACTUAL:\n"""\n{actual}\n"""\n\n'
        "Reply with ONLY a single number 0-10 (10 = perfect match, "
        "0 = completely wrong). No words."
    )
    score_text = call_claude(client, judge, model=model, max_tokens=10)
    try:
        first_token = score_text.strip().split()[0].rstrip(".,")
        return actual, float(first_token)
    except (ValueError, IndexError):
        return actual, None
