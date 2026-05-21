"""Anthropic Prompt Improver — meta-prompts Claude to rewrite the prompt."""
from __future__ import annotations

from anthropic import Anthropic

from prompt_quality_lab.anthropic_client import call_claude


def anthropic_prompt_improver(client: Anthropic, prompt: str, model: str) -> str:
    """Ask Claude to rewrite `prompt` for clarity, specificity, and structure."""
    meta = f"""You are an expert prompt engineer. Rewrite the prompt below to be:
- clearer and more specific about the task and the desired output format
- structured (use sections / numbered steps where helpful)
- free of ambiguity, while preserving the original intent

Return ONLY the improved prompt. No preamble, no commentary, no markdown fences.

ORIGINAL PROMPT:
\"\"\"
{prompt}
\"\"\""""
    return call_claude(client, meta, model=model, max_tokens=64000)
