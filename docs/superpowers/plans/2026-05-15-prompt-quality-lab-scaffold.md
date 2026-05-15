# Prompt Quality Lab Scaffold — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the 482-line single-file Streamlit app into a structured `src/`-layout Python project with module split, starter tests, ruff, uv, and VS Code workspace config. Preserves all existing behavior except updating `claude-opus-4-6` → `claude-opus-4-7` and loading the Anthropic API key from `.env`.

**Architecture:** Pure-logic modules (`loaders.py`, `optimisers/dspy_bootstrap.py`) have no Streamlit or Anthropic imports, so they unit-test trivially. API-calling code is concentrated in `anthropic_client.py` and the per-optimiser modules. `app.py` is UI-only — it imports and composes. `streamlit_app.py` at the repo root is a 3-line entry point that works around the known src-layout + Streamlit import-path issue.

**Tech Stack:** Python 3.11, Streamlit, Anthropic SDK, LangChain, python-dotenv, pytest, ruff, uv.

**Note on commits:** This project is not a git repo (user opted out). Where a normal plan would commit, this plan ends each task with a **Checkpoint** — a verification step (run tests, run lint, or smoke-test the app) so you don't carry broken state into the next task.

---

## File Structure

**Created (config / workspace):**
- `pyproject.toml` — uv project metadata, deps, ruff + pytest config
- `.python-version` — `3.11`
- `.gitignore` — Python + VS Code + uv ignores
- `.env.example` — `ANTHROPIC_API_KEY=`
- `.vscode/settings.json` — interpreter, ruff, pytest
- `.vscode/launch.json` — Streamlit debug config
- `.vscode/extensions.json` — recommend Python + Ruff
- `README.md` — quick start + dev workflow

**Created (package):**
- `streamlit_app.py` — root entry
- `src/prompt_quality_lab/__init__.py`
- `src/prompt_quality_lab/app.py` — Streamlit UI
- `src/prompt_quality_lab/config.py` — model constants + dotenv load
- `src/prompt_quality_lab/loaders.py` — file parsing (pure)
- `src/prompt_quality_lab/anthropic_client.py` — call_claude, evaluate_against_expected
- `src/prompt_quality_lab/optimisers/__init__.py`
- `src/prompt_quality_lab/optimisers/prompt_improver.py`
- `src/prompt_quality_lab/optimisers/dspy_bootstrap.py` — pure
- `src/prompt_quality_lab/optimisers/variants.py`
- `src/prompt_quality_lab/optimisers/langchain_template.py`

**Created (tests):**
- `tests/__init__.py`
- `tests/conftest.py`
- `tests/test_loaders.py`
- `tests/test_dspy_bootstrap.py`
- `tests/test_anthropic_client.py`

**Deleted at end:**
- `prompt_quality_lab.py` — replaced by the package

---

## Task 1: Bootstrap project config files

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `.gitignore`
- Create: `.env.example`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "prompt-quality-lab"
version = "0.1.0"
description = "Test prompt-optimisation frameworks against Anthropic Claude"
requires-python = ">=3.11"
dependencies = [
    "streamlit>=1.32",
    "anthropic>=0.40",
    "langchain>=0.3",
    "langchain-core>=0.3",
    "langchain-anthropic>=0.3",
    "python-dotenv>=1.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "ruff>=0.6",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/prompt_quality_lab"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: Write `.python-version`**

```
3.11
```

- [ ] **Step 3: Write `.gitignore`**

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
.eggs/
dist/
build/

# Virtual envs
.venv/
venv/
env/

# Tooling caches
.pytest_cache/
.ruff_cache/
.mypy_cache/

# Env
.env
.env.local

# VS Code (workspace settings kept; user settings ignored)
.vscode/*.code-workspace

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 4: Write `.env.example`**

```
ANTHROPIC_API_KEY=
```

- [ ] **Step 5: Checkpoint — verify files exist**

Run in PowerShell:
```powershell
Test-Path pyproject.toml, .python-version, .gitignore, .env.example
```
Expected: four `True` lines.

---

## Task 2: Create package skeleton and install deps

**Files:**
- Create: `src/prompt_quality_lab/__init__.py`
- Create: `src/prompt_quality_lab/optimisers/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `src/prompt_quality_lab/__init__.py`**

```python
"""Prompt Quality Lab — multi-framework prompt optimisation reviewer."""

__version__ = "0.1.0"
```

- [ ] **Step 2: Create `src/prompt_quality_lab/optimisers/__init__.py`**

Empty file:
```python
```

- [ ] **Step 3: Create `tests/__init__.py`**

Empty file:
```python
```

- [ ] **Step 4: Create `tests/conftest.py`**

```python
"""Shared pytest fixtures."""
```

(Intentionally empty for now — tests use local fixtures. File exists so pytest discovers it cleanly later.)

- [ ] **Step 5: Run `uv sync`**

```powershell
uv sync
```
Expected: creates `.venv/`, installs all runtime + dev deps, prints final "Installed N packages" line. If `uv` is not installed, install it first per https://docs.astral.sh/uv/getting-started/installation/.

- [ ] **Step 6: Checkpoint — verify pytest discovers tests directory**

```powershell
uv run pytest --collect-only
```
Expected: exits 0 (or "no tests ran"), no import errors.

---

## Task 3: Implement `config.py`

**Files:**
- Create: `src/prompt_quality_lab/config.py`

- [ ] **Step 1: Write `config.py`**

```python
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
```

- [ ] **Step 2: Checkpoint — verify import**

```powershell
uv run python -c "from prompt_quality_lab.config import AVAILABLE_MODELS, DEFAULT_MODEL; print(AVAILABLE_MODELS, DEFAULT_MODEL)"
```
Expected: prints the list and `claude-sonnet-4-6`.

---

## Task 4: Implement `loaders.py` (TDD)

**Files:**
- Create: `tests/test_loaders.py`
- Create: `src/prompt_quality_lab/loaders.py`

**Design note:** Original `load_prompts` called `st.warning()` for malformed input. The pure version returns `(prompts, warnings)` so it has no Streamlit dependency. `app.py` displays the warnings.

- [ ] **Step 1: Write `tests/test_loaders.py`**

```python
"""Tests for the file loaders. No Streamlit, no Anthropic API."""
from __future__ import annotations

from prompt_quality_lab.loaders import _coerce_row, load_prompts


class FakeFile:
    """Minimal stand-in for a Streamlit UploadedFile."""

    def __init__(self, name: str, content: str | bytes):
        self.name = name
        self._content = content.encode("utf-8") if isinstance(content, str) else content

    def read(self) -> bytes:
        return self._content


def test_coerce_row_uses_alternate_keys():
    row = {"prompt_id": "p1", "text": "hello", "expected": "world"}
    assert _coerce_row(row, "fallback") == {
        "id": "p1",
        "prompt": "hello",
        "expected_output": "world",
    }


def test_coerce_row_falls_back_when_id_missing():
    row = {"prompt": "x"}
    assert _coerce_row(row, "fallback")["id"] == "fallback"


def test_load_prompts_csv():
    files = [FakeFile("data.csv", "id,prompt,expected_output\np1,hello,world\np2,foo,bar\n")]
    prompts, warnings = load_prompts(files)
    assert warnings == []
    assert prompts == [
        {"id": "p1", "prompt": "hello", "expected_output": "world"},
        {"id": "p2", "prompt": "foo", "expected_output": "bar"},
    ]


def test_load_prompts_json_list():
    content = '[{"id": "p1", "prompt": "hello", "expected_output": "world"}]'
    files = [FakeFile("data.json", content)]
    prompts, warnings = load_prompts(files)
    assert warnings == []
    assert prompts == [{"id": "p1", "prompt": "hello", "expected_output": "world"}]


def test_load_prompts_txt():
    files = [FakeFile("essay.txt", "  this is a prompt  ")]
    prompts, warnings = load_prompts(files)
    assert warnings == []
    assert prompts == [{"id": "essay.txt", "prompt": "this is a prompt", "expected_output": ""}]


def test_load_prompts_skips_empty_prompt_rows():
    files = [FakeFile("data.csv", "id,prompt,expected_output\np1,,world\np2,foo,bar\n")]
    prompts, _ = load_prompts(files)
    assert len(prompts) == 1
    assert prompts[0]["id"] == "p2"


def test_load_prompts_warns_on_invalid_json():
    files = [FakeFile("bad.json", "{not valid json")]
    prompts, warnings = load_prompts(files)
    assert prompts == []
    assert len(warnings) == 1
    assert "bad.json" in warnings[0]


def test_load_prompts_warns_on_unknown_extension():
    files = [FakeFile("mystery.xyz", "data")]
    prompts, warnings = load_prompts(files)
    assert prompts == []
    assert len(warnings) == 1
    assert "mystery.xyz" in warnings[0]


def test_load_prompts_handles_latin1_fallback():
    # Bytes that are not valid UTF-8 but are valid latin-1.
    files = [FakeFile("essay.txt", b"caf\xe9")]
    prompts, _ = load_prompts(files)
    assert prompts[0]["prompt"] == "café"
```

- [ ] **Step 2: Run tests — verify they fail**

```powershell
uv run pytest tests/test_loaders.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'prompt_quality_lab.loaders'` or `ImportError`.

- [ ] **Step 3: Write `src/prompt_quality_lab/loaders.py`**

```python
"""Prompt file loaders. Pure: no Streamlit, no Anthropic imports."""
from __future__ import annotations

import csv
import io
import json


def _coerce_row(row: dict, fallback_id: str) -> dict:
    """Normalise a record to {id, prompt, expected_output}."""
    pid = row.get("id") or row.get("prompt_id") or fallback_id
    text = (
        row.get("prompt")
        or row.get("prompt_text")
        or row.get("text")
        or row.get("input")
        or ""
    )
    expected = (
        row.get("expected_output")
        or row.get("expected")
        or row.get("output")
        or ""
    )
    return {"id": str(pid), "prompt": str(text), "expected_output": str(expected)}


def load_prompts(uploaded_files) -> tuple[list[dict], list[str]]:
    """Auto-detect file type and return (prompts, warnings).

    Each prompt is {id, prompt, expected_output}. Warnings are human-readable
    strings that the UI layer can surface to the user.
    """
    prompts: list[dict] = []
    warnings: list[str] = []

    for f in uploaded_files:
        name = f.name.lower()
        raw = f.read()
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            content = raw.decode("latin-1")

        if name.endswith(".csv"):
            reader = csv.DictReader(io.StringIO(content))
            for i, row in enumerate(reader):
                rec = _coerce_row(row, f"{f.name}#{i}")
                if rec["prompt"]:
                    prompts.append(rec)

        elif name.endswith(".json"):
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                warnings.append(f"Skipping {f.name}: invalid JSON ({e})")
                continue
            if isinstance(data, list):
                for i, item in enumerate(data):
                    if isinstance(item, dict):
                        rec = _coerce_row(item, f"{f.name}#{i}")
                    else:
                        rec = {
                            "id": f"{f.name}#{i}",
                            "prompt": str(item),
                            "expected_output": "",
                        }
                    if rec["prompt"]:
                        prompts.append(rec)
            elif isinstance(data, dict):
                rec = _coerce_row(data, f.name)
                if rec["prompt"]:
                    prompts.append(rec)

        elif name.endswith((".txt", ".md")):
            prompts.append(
                {"id": f.name, "prompt": content.strip(), "expected_output": ""}
            )

        else:
            warnings.append(f"Skipping unsupported file type: {f.name}")

    return prompts, warnings
```

- [ ] **Step 4: Run tests — verify they pass**

```powershell
uv run pytest tests/test_loaders.py -v
```
Expected: all 9 tests pass.

- [ ] **Step 5: Checkpoint — lint the new code**

```powershell
uv run ruff check src/prompt_quality_lab/loaders.py tests/test_loaders.py
```
Expected: `All checks passed!`

---

## Task 5: Implement `anthropic_client.py` (TDD)

**Files:**
- Create: `tests/test_anthropic_client.py`
- Create: `src/prompt_quality_lab/anthropic_client.py`

- [ ] **Step 1: Write `tests/test_anthropic_client.py`**

```python
"""Tests for the Anthropic client wrapper. Uses a MagicMock client — no real API calls."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from prompt_quality_lab.anthropic_client import call_claude, evaluate_against_expected


def make_fake_client(text: str) -> MagicMock:
    """Return a MagicMock that mimics `Anthropic` and yields `text` from messages.create."""
    client = MagicMock()
    client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(text=text)]
    )
    return client


def test_call_claude_passes_model_and_prompt():
    client = make_fake_client("response text")
    out = call_claude(client, "hello", model="claude-sonnet-4-6")
    assert out == "response text"

    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["model"] == "claude-sonnet-4-6"
    assert kwargs["messages"] == [{"role": "user", "content": "hello"}]
    assert kwargs["system"] == "You are a helpful assistant."
    assert kwargs["max_tokens"] == 2048


def test_call_claude_uses_custom_system():
    client = make_fake_client("ok")
    call_claude(client, "hi", model="m", system="You are a judge.")
    assert client.messages.create.call_args.kwargs["system"] == "You are a judge."


def test_evaluate_returns_actual_only_when_no_expected():
    client = make_fake_client("actual response")
    actual, score = evaluate_against_expected(client, "prompt", expected="", model="m")
    assert actual == "actual response"
    assert score is None
    assert client.messages.create.call_count == 1


def test_evaluate_parses_integer_score():
    client = MagicMock()
    client.messages.create.side_effect = [
        SimpleNamespace(content=[SimpleNamespace(text="the actual response")]),
        SimpleNamespace(content=[SimpleNamespace(text="8")]),
    ]
    actual, score = evaluate_against_expected(client, "prompt", expected="exp", model="m")
    assert actual == "the actual response"
    assert score == 8.0


def test_evaluate_parses_decimal_with_trailing_punctuation():
    client = MagicMock()
    client.messages.create.side_effect = [
        SimpleNamespace(content=[SimpleNamespace(text="output")]),
        SimpleNamespace(content=[SimpleNamespace(text="7.5.")]),
    ]
    _, score = evaluate_against_expected(client, "p", expected="e", model="m")
    assert score == 7.5


def test_evaluate_returns_none_when_score_unparseable():
    client = MagicMock()
    client.messages.create.side_effect = [
        SimpleNamespace(content=[SimpleNamespace(text="output")]),
        SimpleNamespace(content=[SimpleNamespace(text="not a number")]),
    ]
    _, score = evaluate_against_expected(client, "p", expected="e", model="m")
    assert score is None
```

- [ ] **Step 2: Run tests — verify they fail**

```powershell
uv run pytest tests/test_anthropic_client.py -v
```
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `src/prompt_quality_lab/anthropic_client.py`**

```python
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
    judge = f"""You are a strict evaluator. Compare the ACTUAL response to the EXPECTED response for semantic equivalence and quality.

EXPECTED:
\"\"\"
{expected}
\"\"\"

ACTUAL:
\"\"\"
{actual}
\"\"\"

Reply with ONLY a single number 0-10 (10 = perfect match, 0 = completely wrong). No words."""
    score_text = call_claude(client, judge, model=model, max_tokens=10)
    try:
        first_token = score_text.strip().split()[0].rstrip(".,")
        return actual, float(first_token)
    except (ValueError, IndexError):
        return actual, None
```

- [ ] **Step 4: Run tests — verify they pass**

```powershell
uv run pytest tests/test_anthropic_client.py -v
```
Expected: all 6 tests pass.

- [ ] **Step 5: Checkpoint — lint**

```powershell
uv run ruff check src/prompt_quality_lab/anthropic_client.py tests/test_anthropic_client.py
```
Expected: `All checks passed!`

---

## Task 6: Implement `optimisers/dspy_bootstrap.py` (TDD)

**Files:**
- Create: `tests/test_dspy_bootstrap.py`
- Create: `src/prompt_quality_lab/optimisers/dspy_bootstrap.py`

- [ ] **Step 1: Write `tests/test_dspy_bootstrap.py`**

```python
"""Tests for DSPy-style few-shot bootstrap. Pure function — no API needed."""
from __future__ import annotations

from prompt_quality_lab.optimisers.dspy_bootstrap import dspy_style_bootstrap


def test_returns_original_when_no_examples():
    assert dspy_style_bootstrap("write a haiku", []) == "write a haiku"


def test_returns_original_when_examples_lack_expected_output():
    examples = [{"id": "a", "prompt": "x", "expected_output": ""}]
    assert dspy_style_bootstrap("target", examples) == "target"


def test_builds_few_shot_block_from_labelled_examples():
    examples = [
        {"id": "a", "prompt": "input A", "expected_output": "output A"},
        {"id": "b", "prompt": "input B", "expected_output": "output B"},
    ]
    result = dspy_style_bootstrap("new target", examples)
    assert "Input:\ninput A\n\nOutput:\noutput A" in result
    assert "Input:\ninput B\n\nOutput:\noutput B" in result
    assert "new target" in result


def test_filters_out_examples_with_empty_expected():
    examples = [
        {"id": "a", "prompt": "labelled", "expected_output": "yes"},
        {"id": "b", "prompt": "unlabelled", "expected_output": ""},
    ]
    result = dspy_style_bootstrap("target", examples)
    assert "labelled" in result
    assert "unlabelled" not in result
```

- [ ] **Step 2: Run tests — verify they fail**

```powershell
uv run pytest tests/test_dspy_bootstrap.py -v
```
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `src/prompt_quality_lab/optimisers/dspy_bootstrap.py`**

```python
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
```

- [ ] **Step 4: Run tests — verify they pass**

```powershell
uv run pytest tests/test_dspy_bootstrap.py -v
```
Expected: all 4 tests pass.

- [ ] **Step 5: Checkpoint — run full test suite + lint**

```powershell
uv run pytest -v
uv run ruff check .
```
Expected: 19 tests pass, no lint errors.

---

## Task 7: Implement `optimisers/prompt_improver.py`

**Files:**
- Create: `src/prompt_quality_lab/optimisers/prompt_improver.py`

- [ ] **Step 1: Write the module**

```python
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
    return call_claude(client, meta, model=model)
```

- [ ] **Step 2: Checkpoint — verify import**

```powershell
uv run python -c "from prompt_quality_lab.optimisers.prompt_improver import anthropic_prompt_improver; print('ok')"
```
Expected: prints `ok`.

---

## Task 8: Implement `optimisers/variants.py`

**Files:**
- Create: `src/prompt_quality_lab/optimisers/variants.py`

- [ ] **Step 1: Write the module**

```python
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
    request = f"""Generate exactly {n} alternative rewrites of the following prompt. Each should test a different angle (e.g. more concise, more structured, role-prefix, chain-of-thought, output-format-first). Preserve the original intent.

Return ONLY a valid JSON array of {n} strings. No commentary, no markdown fences.

PROMPT:
\"\"\"
{prompt}
\"\"\""""
    raw = call_claude(client, request, model=model)
    try:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        variants = json.loads(raw[start:end])
        return [str(v) for v in variants][:n]
    except (json.JSONDecodeError, ValueError):
        return [raw]
```

- [ ] **Step 2: Checkpoint — verify import**

```powershell
uv run python -c "from prompt_quality_lab.optimisers.variants import generate_variants; print('ok')"
```
Expected: prints `ok`.

---

## Task 9: Implement `optimisers/langchain_template.py`

**Files:**
- Create: `src/prompt_quality_lab/optimisers/langchain_template.py`

**Design note:** This module re-exports the two LangChain classes it needs and exposes an `AVAILABLE` flag so the UI can check before constructing anything. If LangChain isn't installed, the module imports cleanly and `AVAILABLE` is `False`.

- [ ] **Step 1: Write the module**

```python
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
```

- [ ] **Step 2: Checkpoint — verify import and flag**

```powershell
uv run python -c "from prompt_quality_lab.optimisers import langchain_template as lct; print(lct.AVAILABLE)"
```
Expected: prints `True` (LangChain is in our deps).

---

## Task 10: Implement `app.py` (Streamlit UI)

**Files:**
- Create: `src/prompt_quality_lab/app.py`

**Design note:** This is the biggest single file in the refactor (~250 lines) because it owns all UI. Every line of logic delegates to the modules built in tasks 3-9. No new behavior — this is a faithful port of the UI from the original monolith with two small adjustments: (a) loader warnings come back as a list and are displayed via `st.warning`, and (b) the LangChain tab uses `lct.AVAILABLE` instead of a try/except at function scope.

- [ ] **Step 1: Write `src/prompt_quality_lab/app.py`**

```python
"""Streamlit UI for Prompt Quality Lab. Composes the optimiser modules."""
from __future__ import annotations

import os

import streamlit as st
from anthropic import Anthropic

from prompt_quality_lab.anthropic_client import call_claude, evaluate_against_expected
from prompt_quality_lab.config import AVAILABLE_MODELS
from prompt_quality_lab.loaders import load_prompts
from prompt_quality_lab.optimisers import langchain_template as lct
from prompt_quality_lab.optimisers.dspy_bootstrap import dspy_style_bootstrap
from prompt_quality_lab.optimisers.prompt_improver import anthropic_prompt_improver
from prompt_quality_lab.optimisers.variants import generate_variants


def _sidebar() -> tuple[str, str, list]:
    """Render the sidebar. Returns (api_key, model, uploaded_files)."""
    with st.sidebar:
        st.header("⚙️ Setup")
        api_key = st.text_input(
            "Anthropic API key",
            type="password",
            value=os.environ.get("ANTHROPIC_API_KEY", ""),
            help="Get one at https://console.anthropic.com/",
        )
        model = st.selectbox("Model", AVAILABLE_MODELS, index=0)
        st.divider()
        st.subheader("📂 Upload prompts")
        uploaded = st.file_uploader(
            "CSV / JSON / .txt — multiple OK",
            type=["csv", "json", "txt", "md"],
            accept_multiple_files=True,
        )
        st.divider()
        with st.expander("Input format hints"):
            st.markdown(
                """
**CSV** — columns: `id, prompt, expected_output` *(expected_output optional)*

**JSON** — list of objects:
```json
[
  {"id": "p1", "prompt": "...", "expected_output": "..."}
]
```

**.txt** — one prompt per file; filename becomes the ID.
"""
            )
    return api_key, model, uploaded


def _tab_prompt_improver(client: Anthropic, prompts: list[dict], model: str) -> None:
    st.subheader("Rewrite each prompt for clarity (meta-prompting)")
    st.caption(
        "Claude rewrites your prompt to be clearer, more specific, and better structured. "
        "If you have expected outputs, both versions are scored."
    )
    also_score = st.checkbox(
        "Score original vs improved (uses extra API calls)",
        value=True,
        key="improver_score",
    )
    if st.button("🚀 Improve all prompts", key="improver_run", type="primary"):
        for p in prompts:
            with st.expander(f"📝 {p['id']}", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Original**")
                    st.code(p["prompt"], language="markdown")
                with col2:
                    st.markdown("**Improved**")
                    with st.spinner("Improving..."):
                        improved = anthropic_prompt_improver(client, p["prompt"], model)
                    st.code(improved, language="markdown")

                if also_score and p["expected_output"]:
                    with st.spinner("Scoring..."):
                        _, orig_score = evaluate_against_expected(
                            client, p["prompt"], p["expected_output"], model
                        )
                        _, new_score = evaluate_against_expected(
                            client, improved, p["expected_output"], model
                        )
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Original score", orig_score)
                    c2.metric("Improved score", new_score)
                    if orig_score is not None and new_score is not None:
                        c3.metric("Δ", round(new_score - orig_score, 2))


def _tab_dspy(client: Anthropic, prompts: list[dict], labelled: list[dict], model: str) -> None:
    st.subheader("Bootstrap few-shot examples (DSPy-style)")
    st.caption(
        f"Uses your **{len(labelled)}** labelled prompt(s) as few-shot examples "
        "for the rest, then compares baseline vs few-shot output."
    )
    if not labelled:
        st.warning(
            "Need at least one prompt with `expected_output` filled in to use as a few-shot example."
        )
        return

    n_shots = st.slider(
        "Few-shot examples per prompt",
        1,
        min(5, len(labelled)),
        min(3, len(labelled)),
    )
    if st.button("🚀 Run DSPy-style optimisation", key="dspy_run", type="primary"):
        for target in prompts:
            fs_pool = [p for p in labelled if p["id"] != target["id"]][:n_shots]
            augmented = dspy_style_bootstrap(target["prompt"], fs_pool)

            with st.expander(f"📝 {target['id']}", expanded=True):
                st.markdown(
                    f"**Few-shot examples used:** {[e['id'] for e in fs_pool] or 'none'}"
                )
                with st.spinner("Running baseline + few-shot..."):
                    baseline = call_claude(client, target["prompt"], model=model)
                    boosted = call_claude(client, augmented, model=model)

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Baseline output**")
                    st.write(baseline)
                with col2:
                    st.markdown("**Few-shot output**")
                    st.write(boosted)

                if target["expected_output"]:
                    with st.spinner("Scoring..."):
                        _, b_score = evaluate_against_expected(
                            client, target["prompt"], target["expected_output"], model
                        )
                        _, n_score = evaluate_against_expected(
                            client, augmented, target["expected_output"], model
                        )
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Baseline score", b_score)
                    c2.metric("Few-shot score", n_score)
                    if b_score is not None and n_score is not None:
                        c3.metric("Δ", round(n_score - b_score, 2))

                with st.expander("View augmented prompt"):
                    st.code(augmented, language="markdown")


def _tab_variants(client: Anthropic, prompts: list[dict], model: str) -> None:
    st.subheader("Generate N variants and score side-by-side (promptfoo-style)")
    st.caption(
        "Claude generates rewrites of each prompt; all variants run; outputs are "
        "scored against `expected_output` if provided."
    )
    n_variants = st.slider("Number of variants per prompt", 2, 5, 3, key="n_variants")
    if st.button("🚀 Generate & compare variants", key="variants_run", type="primary"):
        for p in prompts:
            with st.expander(f"📝 {p['id']}", expanded=True):
                with st.spinner("Generating variants..."):
                    variants = generate_variants(client, p["prompt"], n_variants, model)

                all_versions = [("Original", p["prompt"])] + [
                    (f"Variant {i+1}", v) for i, v in enumerate(variants)
                ]

                rows = []
                for label, text in all_versions:
                    with st.spinner(f"Running {label}..."):
                        actual, score = evaluate_against_expected(
                            client, text, p["expected_output"], model
                        )
                    rows.append(
                        {"version": label, "score": score, "prompt": text, "output": actual}
                    )

                summary = [{"version": r["version"], "score": r["score"]} for r in rows]
                st.markdown("**Score summary**")
                st.dataframe(summary, use_container_width=True)

                for r in rows:
                    with st.expander(f"{r['version']}  —  score: {r['score']}"):
                        st.markdown("**Prompt**")
                        st.code(r["prompt"], language="markdown")
                        st.markdown("**Output**")
                        st.write(r["output"])


def _tab_langchain(client: Anthropic, prompts: list[dict], api_key: str, model: str) -> None:
    st.subheader("LangChain PromptTemplate + simple evals")
    st.caption(
        "Wraps each prompt as a `PromptTemplate`. If the prompt contains `{variables}`, "
        "you'll be asked to fill them in. Then runs via LangChain's Anthropic wrapper."
    )
    if not lct.AVAILABLE:
        st.warning(
            "LangChain not installed. Run:\n"
            "```\npip install langchain langchain-anthropic langchain-core\n```"
        )
        return

    llm = lct.ChatAnthropic(model=model, anthropic_api_key=api_key)
    for p in prompts:
        with st.expander(f"📝 {p['id']}", expanded=True):
            try:
                tmpl = lct.PromptTemplate.from_template(p["prompt"])
            except Exception as e:
                st.error(f"Couldn't parse as template: {e}")
                continue

            vars_needed = list(tmpl.input_variables)
            st.markdown(f"**Input variables:** `{vars_needed or 'none'}`")

            if vars_needed:
                vals: dict[str, str] = {}
                for v in vars_needed:
                    vals[v] = st.text_input(
                        f"Value for `{v}`", key=f"lc_{p['id']}_{v}"
                    )
                ready = all(v.strip() for v in vals.values())
            else:
                vals = {}
                ready = True

            if ready and st.button(f"Run {p['id']}", key=f"lc_run_{p['id']}"):
                rendered = tmpl.format(**vals) if vals else p["prompt"]
                with st.spinner("Calling Claude via LangChain..."):
                    response = llm.invoke(rendered).content
                st.markdown("**Output**")
                st.write(response)
                if p["expected_output"]:
                    with st.spinner("Scoring..."):
                        _, score = evaluate_against_expected(
                            client, rendered, p["expected_output"], model
                        )
                    st.metric("Score vs expected", score)


def main() -> None:
    st.set_page_config(page_title="Prompt Quality Lab", page_icon="🧪", layout="wide")
    st.title("🧪 Prompt Quality Lab")
    st.caption(
        "Test four prompt-optimisation strategies on your own prompts — powered by Anthropic Claude"
    )

    api_key, model, uploaded = _sidebar()

    if not api_key:
        st.warning("👈 Add your Anthropic API key in the sidebar to begin.")
        st.stop()
    if not uploaded:
        st.info("👈 Upload one or more prompt files in the sidebar.")
        st.stop()

    client = Anthropic(api_key=api_key)
    prompts, warnings = load_prompts(uploaded)
    for w in warnings:
        st.warning(w)
    if not prompts:
        st.error("No prompts could be loaded. Check the file format hints in the sidebar.")
        st.stop()

    labelled = [p for p in prompts if p["expected_output"].strip()]
    st.success(
        f"Loaded **{len(prompts)}** prompt(s) — **{len(labelled)}** have expected outputs "
        "(usable as eval data)."
    )
    with st.expander("👀 Preview loaded prompts"):
        st.dataframe(prompts, use_container_width=True)

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "🔧 Prompt Improver",
            "📊 DSPy-style Few-Shot",
            "⚖️ Variant Comparison",
            "🔗 LangChain + Evals",
        ]
    )
    with tab1:
        _tab_prompt_improver(client, prompts, model)
    with tab2:
        _tab_dspy(client, prompts, labelled, model)
    with tab3:
        _tab_variants(client, prompts, model)
    with tab4:
        _tab_langchain(client, prompts, api_key, model)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Checkpoint — verify the module imports cleanly**

```powershell
uv run python -c "from prompt_quality_lab.app import main; print('ok')"
```
Expected: prints `ok` (no import errors). Streamlit prints some deprecation noise occasionally — that's fine, only failure is an exception.

- [ ] **Step 3: Checkpoint — lint everything**

```powershell
uv run ruff check .
```
Expected: `All checks passed!`

---

## Task 11: Create `streamlit_app.py` root entry

**Files:**
- Create: `streamlit_app.py`

- [ ] **Step 1: Write `streamlit_app.py`**

```python
"""Root entry point so `streamlit run streamlit_app.py` works with the src/ layout."""
from prompt_quality_lab.app import main

main()
```

- [ ] **Step 2: Checkpoint — verify file exists**

```powershell
Test-Path streamlit_app.py
```
Expected: `True`. The file is only verified end-to-end by Task 14's smoke test (`streamlit run streamlit_app.py`) — importing it directly would invoke `main()` outside a Streamlit context and fail noisily.

---

## Task 12: Create `.vscode/` workspace settings

**Files:**
- Create: `.vscode/settings.json`
- Create: `.vscode/launch.json`
- Create: `.vscode/extensions.json`

- [ ] **Step 1: Write `.vscode/settings.json`**

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}\\.venv\\Scripts\\python.exe",
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.testing.pytestArgs": ["tests"],
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    }
  },
  "ruff.importStrategy": "fromEnvironment"
}
```

- [ ] **Step 2: Write `.vscode/launch.json`**

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Streamlit: Run app",
      "type": "debugpy",
      "request": "launch",
      "module": "streamlit",
      "args": ["run", "${workspaceFolder}/streamlit_app.py"],
      "justMyCode": false,
      "console": "integratedTerminal"
    },
    {
      "name": "Pytest: Current file",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": ["${file}", "-v"],
      "justMyCode": false,
      "console": "integratedTerminal"
    }
  ]
}
```

- [ ] **Step 3: Write `.vscode/extensions.json`**

```json
{
  "recommendations": [
    "ms-python.python",
    "charliermarsh.ruff"
  ]
}
```

- [ ] **Step 4: Checkpoint — verify JSON parses**

```powershell
Get-Content .vscode/settings.json, .vscode/launch.json, .vscode/extensions.json | ConvertFrom-Json | Out-Null
if ($?) { Write-Output "all json valid" }
```
Expected: prints `all json valid`.

---

## Task 13: Write `README.md`

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

````markdown
# Prompt Quality Lab

A Streamlit app for testing prompt-optimisation strategies against your own prompts using Anthropic Claude. Four approaches in one UI:

1. **Anthropic Prompt Improver** — Claude rewrites your prompt for clarity
2. **DSPy-style Few-Shot** — bootstrap few-shot examples from labelled prompts
3. **Variant Comparison** — generate N rewrites, score each side-by-side
4. **LangChain Template + Evals** — wrap prompts in `PromptTemplate`, fill variables, run, score

## Quick start

```powershell
# 1. Install uv if you haven't (https://docs.astral.sh/uv/getting-started/installation/)

# 2. Install deps
uv sync

# 3. Set your API key
Copy-Item .env.example .env
# Edit .env and paste your key, or paste it in the sidebar each run.

# 4. Run
uv run streamlit run streamlit_app.py
```

Open the URL Streamlit prints (usually http://localhost:8501).

## Input formats

The sidebar accepts multiple files. Auto-detected by extension:

| Format | Schema |
| --- | --- |
| **CSV** | `id, prompt, expected_output` (expected optional) |
| **JSON** | list of `{"id": "...", "prompt": "...", "expected_output": "..."}` |
| **.txt / .md** | one prompt per file; filename becomes the ID |

## Project layout

```
src/prompt_quality_lab/
├── app.py                  # Streamlit UI (composes everything below)
├── config.py               # Model IDs, dotenv load
├── loaders.py              # File parsing (pure)
├── anthropic_client.py     # Claude API wrapper
└── optimisers/
    ├── prompt_improver.py
    ├── dspy_bootstrap.py
    ├── variants.py
    └── langchain_template.py
```

## Dev workflow

```powershell
uv run pytest                    # run tests
uv run ruff check .              # lint
uv run ruff format .             # format
```

In VS Code: open the folder, accept the recommended extensions, hit **F5** to launch with the debugger attached.

## Specs and plans

Design rationale lives under [docs/superpowers/specs/](docs/superpowers/specs/). Implementation plans live under [docs/superpowers/plans/](docs/superpowers/plans/).
````

- [ ] **Step 2: Checkpoint — verify it renders**

Open `README.md` in VS Code's preview (`Ctrl+Shift+V`). Expected: headings, table, and code blocks render correctly.

---

## Task 14: Smoke test + remove the old monolith

**Files:**
- Delete: `prompt_quality_lab.py`

- [ ] **Step 1: Run the full test suite**

```powershell
uv run pytest -v
```
Expected: 19 tests pass (9 loaders + 6 anthropic_client + 4 dspy_bootstrap).

- [ ] **Step 2: Run the linter on everything**

```powershell
uv run ruff check .
```
Expected: `All checks passed!`

- [ ] **Step 3: Launch the app**

```powershell
uv run streamlit run streamlit_app.py
```
Expected: Streamlit prints `Local URL: http://localhost:8501`. Open it in a browser.

- [ ] **Step 4: Manual smoke test in the browser**

1. Sidebar shows API key field, model dropdown (verify `claude-opus-4-7` is in the list), file uploader.
2. Paste your API key (or pre-fill via `.env`).
3. Upload a small CSV with one labelled prompt, e.g. save this as `smoke.csv`:
   ```
   id,prompt,expected_output
   p1,"Write a haiku about coffee.","A short three-line poem with 5-7-5 syllables about coffee."
   ```
4. Verify the success banner shows "Loaded 1 prompt(s) — 1 have expected outputs".
5. Click into each of the four tabs to verify they render without errors. You don't need to run them all — just confirm the UI scaffolding renders.
6. Run the **Prompt Improver** tab end-to-end to verify a real Claude call works. Should see Original / Improved side-by-side with metric scores.
7. Stop the server (Ctrl+C in the terminal).

- [ ] **Step 5: Delete the old monolith**

```powershell
Remove-Item prompt_quality_lab.py
```

- [ ] **Step 6: Final verification**

```powershell
uv run pytest -v
uv run ruff check .
Test-Path prompt_quality_lab.py
```
Expected: tests pass, lint passes, `False` (old file is gone).

---

## Done

The project is now a structured Python package with:
- 12 source modules (~270 lines in `app.py`, all others under 100 lines)
- 3 test files, 19 starter tests, no API key required
- Ruff format-on-save in VS Code
- F5 launches Streamlit with breakpoints
- `.env` keeps the API key out of the repo

Ready to start refining the app.
