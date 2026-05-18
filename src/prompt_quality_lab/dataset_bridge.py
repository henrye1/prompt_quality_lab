"""Bridge between the curated `credit_datasets` records and the optimiser pipeline.

The optimisers consume a flat list of `{id, prompt, expected_output, source}` dicts
(same shape as `prompt_quality_lab.loaders.load_prompts` returns). This module
converts `credit_datasets.Record` objects into that shape so the Dataset Manager's
curated entries can be fed into the same Prompt Improver / DSPy / Variants /
LangChain tabs as uploaded files.
"""
from __future__ import annotations

from pathlib import Path

from credit_datasets.schema import Record


def _read_text_safe(path: Path) -> str:
    """Read a file as text. Binary or unreadable files return an empty string."""
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def record_to_prompt(record: Record, root: Path) -> dict:
    """Convert a single Record into the prompt dict the optimisers consume.

    Multiple input files in `record.inputs_dir()` are concatenated with a separator
    so the optimiser sees the whole picture. If `record.gold_file()` is present its
    contents become `expected_output`; otherwise `expected_output` is empty (the
    optimisers will run unscored, same as for unlabelled uploaded files).
    """
    input_parts = [_read_text_safe(p) for p in record.input_files(root)]
    prompt_text = "\n\n---\n\n".join(part for part in input_parts if part)

    gold = record.gold_file(root)
    expected = _read_text_safe(gold) if gold is not None else ""

    return {
        "id": record.id,
        "prompt": prompt_text,
        "expected_output": expected,
        "source": f"dataset:{record.id}",
    }


def records_to_prompts(records: list[Record], root: Path) -> list[dict]:
    """Convert many Records. Records whose concatenated input text is empty are dropped."""
    out = [record_to_prompt(r, root) for r in records]
    return [p for p in out if p["prompt"]]
