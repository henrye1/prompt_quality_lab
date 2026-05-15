"""Thin wrapper around the Anthropic SDK. All API calls flow through here."""
from __future__ import annotations

from anthropic import Anthropic

from prompt_quality_lab.config import DEFAULT_MODEL


def call_claude(
    client: Anthropic,
    prompt: str,
    model: str = DEFAULT_MODEL,
    system: str | None = None,
    max_tokens: int = 2048,
) -> str:
    """Single-turn Claude call. Returns the assistant's text."""
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system or "You are a helpful assistant.",
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


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
