"""DSPy-style few-shot bootstrap. Pure string formatting — no API calls."""
from __future__ import annotations


def dspy_style_bootstrap(target_prompt: str, examples: list[dict]) -> str:
    """Build a few-shot version of `target_prompt` using labelled `examples`.

    Examples without an `expected_output` are ignored. If no usable examples
    remain, the target prompt is returned unchanged.
    """
    usable = [e for e in examples if e.get("expected_output", "").strip()]
    if not usable:
        return target_prompt
    fs_block = "\n\n".join(
        f"Input:\n{e['prompt']}\n\nOutput:\n{e['expected_output']}" for e in usable
    )
    return f"""Here are reference examples of how to respond:

{fs_block}

---

Now respond to this new input in the same style:

{target_prompt}"""
