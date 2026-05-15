"""Variant generation — promptfoo-style. Asks Claude for N rewrites in JSON."""
from __future__ import annotations

import json

from anthropic import Anthropic

from prompt_quality_lab.anthropic_client import call_claude


def generate_variants(client: Anthropic, prompt: str, n: int, model: str) -> list[str]:
    """Ask Claude for `n` alternative rewrites of `prompt`.

    Returns a list of strings (up to `n`). If parsing fails, returns a single-element
    list containing the raw response so the caller can still display something.
    """
    request = (
        f"Generate exactly {n} alternative rewrites of the following prompt. "
        "Each should test a different angle (e.g. more concise, more structured, "
        "role-prefix, chain-of-thought, output-format-first). "
        "Preserve the original intent.\n\n"
        f"Return ONLY a valid JSON array of {n} strings. "
        "No commentary, no markdown fences.\n\n"
        f'PROMPT:\n"""\n{prompt}\n"""'
    )
    raw = call_claude(client, request, model=model)
    try:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        variants = json.loads(raw[start:end])
        return [str(v) for v in variants][:n]
    except (json.JSONDecodeError, ValueError):
        return [raw]
