# A/B Eval Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an A/B prompt-evaluation harness inside `prompt_quality_lab` — a pure-Python `eval` module that re-uses credit_paper's Stage 3 production code, scores outputs with Claude-as-judge against a credit-specific 6-dimension rubric, and a Streamlit page (Setup / Progress / Results) that lets the operator pick two prompt sources, run them against N gold records, and see side-by-side scored comparisons.

**Architecture:** Three repos involved. `credit_paper` gets minimal additive changes (new `pyproject.toml`, a top-level `__init__.py`, and an env-var override of its prompt directory) so it becomes importable as a package. `prompt_quality_lab` gains two new packages: `eval/` (pure Python, fully unit-testable with mocked LLM clients) and `ab_eval/` (thin Streamlit UI over `eval/`). Runs persist as JSONL + raw HTML under `prompt_quality_lab/data/eval_runs/` (gitignored, OneDrive-backed).

**Tech Stack:** Python 3.11+, Anthropic SDK (already a dep), Streamlit ≥ 1.40, pytest, `credit_paper` as an editable local dep.

**Spec:** [2026-05-17-ab-eval-harness-design.md](../specs/2026-05-17-ab-eval-harness-design.md)

---

## File Structure

### Existing: `credit_paper/` (modified, minimal additive changes)

| Path | Change | Responsibility |
|---|---|---|
| `pyproject.toml` | NEW | Makes credit_paper a pip-installable flat-layout package |
| `__init__.py` | NEW (empty) | Required for `credit_paper.*` imports to resolve |
| `prompts/prompt_manager.py` | MODIFIED | Read prompts dir from `$CREDIT_PAPER_PROMPTS_DIR`, fall back to existing path |

### Existing: `prompt_quality_lab/` (modified)

| Path | Change | Responsibility |
|---|---|---|
| `pyproject.toml` | MODIFIED | Add `credit-paper` as editable dep + bump `streamlit>=1.40` |
| `.gitignore` | MODIFIED | Add `data/eval_runs/` |
| `pages/2_AB_Eval.py` | NEW | Streamlit auto-discovered page shim |
| `src/prompt_quality_lab/eval/__init__.py` | NEW | Public exports |
| `src/prompt_quality_lab/eval/schema.py` | NEW | Dimension, Rubric, PromptSource, RecordScore, Run + JSON I/O |
| `src/prompt_quality_lab/eval/rubric.py` | NEW | CREDIT_RUBRIC constant |
| `src/prompt_quality_lab/eval/runner.py` | NEW | `with_prompts_dir` + `generate()` |
| `src/prompt_quality_lab/eval/judge.py` | NEW | `score()` (Claude tool-use) |
| `src/prompt_quality_lab/eval/store.py` | NEW | save_run / load_run / list_runs |
| `src/prompt_quality_lab/eval/ab.py` | NEW | `run_ab()` orchestrator |
| `src/prompt_quality_lab/ab_eval/__init__.py` | NEW | Empty |
| `src/prompt_quality_lab/ab_eval/page.py` | NEW | Mode dispatch |
| `src/prompt_quality_lab/ab_eval/setup_view.py` | NEW | Source pickers + record multiselect + Run button |
| `src/prompt_quality_lab/ab_eval/progress_view.py` | NEW | Progress bar + cancel |
| `src/prompt_quality_lab/ab_eval/results_view.py` | NEW | Run list + drill-down + CSV export |
| `src/prompt_quality_lab/ab_eval/cost.py` | NEW | Per-call price constants + estimate |
| `tests/test_eval_schema.py` | NEW | |
| `tests/test_eval_rubric.py` | NEW | |
| `tests/test_eval_runner.py` | NEW | |
| `tests/test_eval_judge.py` | NEW | |
| `tests/test_eval_store.py` | NEW | |
| `tests/test_eval_ab.py` | NEW | |
| `tests/test_eval_public_api.py` | NEW | |
| `tests/test_ab_eval_cost.py` | NEW | |
| `tests/test_credit_paper_integration.py` | NEW | Smoke: env-var override works end-to-end |

---

## Notes for the implementing engineer

- **Working directories.** Tasks 1–3 happen inside `credit_paper/`. Task 4 happens inside `prompt_quality_lab/`. Tasks 5–17 happen inside `prompt_quality_lab/`. Always `cd` to the right repo before running commands. The repo paths are under `C:\Users\APR\OneDrive - Anchor Point Risk (Pty) Ltd\Desktop\VS_CODE_REPOSITORY\` — quote the path.
- **Branch strategy.** Both `credit_paper` and `prompt_quality_lab` should have a feature branch for this work. Create `feat/ab-eval-harness` in `credit_paper` (Task 1) and `feat/ab-eval-harness` in `prompt_quality_lab` (Task 4). The user can keep, merge, or PR each independently when the plan completes.
- **OneDrive uv quirk.** Set `$env:UV_LINK_MODE='copy'` once in your PowerShell session if you see `os error 396` from uv on OneDrive paths.
- **TDD discipline.** For every task with a test step: write the failing test FIRST, run it to confirm failure, then implement, then run to confirm pass, then commit.
- **No real LLM calls in unit tests.** Both Anthropic and Gemini are mocked via injectable client dependencies. The only test that actually imports `credit_paper` is `test_credit_paper_integration.py` and it exercises the env-var override only — no Gemini calls.
- **`credit_datasets` is already an editable dep** in `prompt_quality_lab` from the prior plan. Don't re-add it; just import.

---

## Phase A — `credit_paper` packaging + override

### Task 1: Add `credit_paper/pyproject.toml` + top-level `__init__.py`

**Files:**
- Create: `credit_paper/pyproject.toml`
- Create: `credit_paper/__init__.py`

- [ ] **Step 1: Create branch + verify clean state**

```powershell
cd "C:\Users\APR\OneDrive - Anchor Point Risk (Pty) Ltd\Desktop\VS_CODE_REPOSITORY\credit_paper"
git status
git checkout -b feat/ab-eval-harness
```

Expected: clean working tree before branch creation. If dirty, ask the user before proceeding.

- [ ] **Step 2: Write `pyproject.toml`**

`credit_paper/pyproject.toml`:

```toml
[project]
name = "credit-paper"
version = "0.1.0"
description = "Credit Paper Assessment Agent — production app + library exports"
requires-python = ">=3.10"
dependencies = [
    "google-genai>=0.3",
    "llama-parse>=0.5",
    "python-docx>=1.1",
    "beautifulsoup4>=4.12",
    "pandas>=2.0",
    "openpyxl>=3.1",
    "python-dotenv>=1.0",
    "streamlit>=1.32",
    "firecrawl-py>=1.0",
    "PyPDF2>=3.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["core", "config", "prompts"]
```

- [ ] **Step 3: Create empty top-level `__init__.py`**

`credit_paper/__init__.py`:

```python
"""Credit Paper Assessment Agent — importable as `credit_paper.*`."""
```

- [ ] **Step 4: Verify imports resolve**

```powershell
cd "C:\Users\APR\OneDrive - Anchor Point Risk (Pty) Ltd\Desktop\VS_CODE_REPOSITORY\credit_paper"
$env:UV_LINK_MODE = "copy"
python -c "import sys; sys.path.insert(0, '.'); from credit_paper.prompts.prompt_manager import load_prompt; print('ok')"
```

Expected: `ok`. The `sys.path` trick mimics what will happen once `credit_paper` is installed as an editable dep in `prompt_quality_lab` (Task 4). If it fails with `ModuleNotFoundError: credit_paper`, the `__init__.py` was placed wrong — verify it's at `credit_paper/__init__.py` (top level), not under `core/` or `prompts/`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml __init__.py
git commit -m "feat: package credit_paper as installable library

Adds pyproject.toml (flat-layout, hatchling) and top-level __init__.py
so credit_paper.core.report_generator and credit_paper.prompts.prompt_manager
can be imported by other tooling. Strictly additive — existing Streamlit
pages keep working unchanged."
```

---

### Task 2: Add `CREDIT_PAPER_PROMPTS_DIR` env-var override to `prompt_manager.py`

**Files:**
- Modify: `credit_paper/prompts/prompt_manager.py`
- Create: `credit_paper/tests/test_prompt_manager_override.py`

- [ ] **Step 1: Inspect current `prompt_manager.py` and locate the hardcoded path**

```bash
cd "C:\Users\APR\OneDrive - Anchor Point Risk (Pty) Ltd\Desktop\VS_CODE_REPOSITORY\credit_paper"
```

Read `prompts/prompt_manager.py`. Find the constant defining the path to `prompts/current/` (likely `_DEFAULT_PROMPTS_DIR` or similar — call it the "current dir constant"). Note its name; you'll reference it in subsequent steps.

- [ ] **Step 2: Write the failing test**

Create `credit_paper/tests/__init__.py` (empty) if it doesn't exist.

Create `credit_paper/tests/test_prompt_manager_override.py`:

```python
"""Verifies CREDIT_PAPER_PROMPTS_DIR env-var override works.

Strictly additive: when the env var is unset, behaviour matches what it
was before this commit.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml


def test_default_dir_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CREDIT_PAPER_PROMPTS_DIR", raising=False)
    from credit_paper.prompts import prompt_manager
    # Re-resolve in case the module cached on first import
    d = prompt_manager._prompts_dir()
    # Should point at the existing prompts/current/ relative to the package
    assert d.name == "current"
    assert d.is_dir()


def test_env_var_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Build a fake prompts dir with one stub YAML file
    fake_dir = tmp_path / "fake_prompts"
    fake_dir.mkdir()
    (fake_dir / "report_instructions.yaml").write_text(
        yaml.safe_dump({"role_definition": "STUB ROLE"}),
        encoding="utf-8",
    )

    monkeypatch.setenv("CREDIT_PAPER_PROMPTS_DIR", str(fake_dir))

    from credit_paper.prompts import prompt_manager
    d = prompt_manager._prompts_dir()
    assert d == fake_dir

    data = prompt_manager.load_prompt("report_instructions")
    assert data["role_definition"] == "STUB ROLE"


def test_override_then_unset_restores_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CREDIT_PAPER_PROMPTS_DIR", str(tmp_path))
    from credit_paper.prompts import prompt_manager
    assert prompt_manager._prompts_dir() == tmp_path

    monkeypatch.delenv("CREDIT_PAPER_PROMPTS_DIR")
    d = prompt_manager._prompts_dir()
    assert d.name == "current"
```

- [ ] **Step 3: Run test — expect failure**

Add `pytest` to credit_paper's dev requirements if not present (the existing project uses `requirements.txt` not `pyproject.toml` for deps — add a `requirements-dev.txt`):

`credit_paper/requirements-dev.txt`:
```
pytest>=8.0
pyyaml>=6.0
```

```powershell
cd "C:\Users\APR\OneDrive - Anchor Point Risk (Pty) Ltd\Desktop\VS_CODE_REPOSITORY\credit_paper"
pip install -r requirements-dev.txt
pytest tests/test_prompt_manager_override.py -v
```

Expected: tests fail because `prompt_manager._prompts_dir()` does not exist yet.

- [ ] **Step 4: Modify `prompt_manager.py` to add the override**

Open `credit_paper/prompts/prompt_manager.py`. At the top of the file (after the existing imports), add:

```python
import os
from pathlib import Path

_DEFAULT_PROMPTS_DIR = Path(__file__).parent / "current"


def _prompts_dir() -> Path:
    """Resolve the prompts directory, honouring CREDIT_PAPER_PROMPTS_DIR."""
    env = os.environ.get("CREDIT_PAPER_PROMPTS_DIR")
    return Path(env) if env else _DEFAULT_PROMPTS_DIR
```

If the file already has its own constant for the prompts directory (e.g., `PROMPTS_DIR`), REPLACE its definition with the `_prompts_dir()` indirection pattern: every function that previously read the constant directly must now call `_prompts_dir()` instead. This is a search-and-replace within the file.

A typical change inside `load_prompt`:

```python
# Before:
def load_prompt(name: str) -> dict:
    path = PROMPTS_DIR / f"{name}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))

# After:
def load_prompt(name: str) -> dict:
    path = _prompts_dir() / f"{name}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))
```

Apply this pattern to every function in the file that reads the prompts directory.

- [ ] **Step 5: Run test — expect pass**

```powershell
cd "C:\Users\APR\OneDrive - Anchor Point Risk (Pty) Ltd\Desktop\VS_CODE_REPOSITORY\credit_paper"
pytest tests/test_prompt_manager_override.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Verify the existing Streamlit pages still work (no live launch — just imports)**

```powershell
python -c "import sys; sys.path.insert(0, '.'); from credit_paper.prompts.prompt_manager import load_prompt, save_prompt, get_version_history, assemble_prompt_text; print('all imports ok')"
```

Expected: `all imports ok`. Confirms the refactor didn't remove or rename any existing public functions.

- [ ] **Step 7: Commit**

```bash
git add prompts/prompt_manager.py tests/test_prompt_manager_override.py tests/__init__.py requirements-dev.txt
git commit -m "feat(prompts): CREDIT_PAPER_PROMPTS_DIR env-var override

Lets external tooling (eval harness) temporarily point credit_paper at
an alternate prompts directory without mutating prompts/current/. Strictly
additive — unset env var preserves the existing hardcoded default."
```

---

### Task 3: Add `credit-paper` as editable dep in `prompt_quality_lab`

**Files:**
- Modify: `prompt_quality_lab/pyproject.toml`

- [ ] **Step 1: Switch to prompt_quality_lab and create the feature branch**

```powershell
cd "C:\Users\APR\OneDrive - Anchor Point Risk (Pty) Ltd\Desktop\VS_CODE_REPOSITORY\prompt_quality_lab"
git status
git checkout -b feat/ab-eval-harness
```

Expected: clean working tree before branch creation.

- [ ] **Step 2: Update `pyproject.toml`**

In `prompt_quality_lab/pyproject.toml`:

1. APPEND `"credit-paper"` to the `dependencies` array (after `"credit-datasets"`).
2. APPEND to the `[tool.uv.sources]` section:

```toml
credit-paper = { path = "../credit_paper", editable = true }
```

3. BUMP `"streamlit>=1.32"` to `"streamlit>=1.40"` (the spec's Detail/Setup views use `st.pdf()` and other widgets that require ≥ 1.40).

Do NOT replace the existing `dependencies` array wholesale — only add `credit-paper` and bump streamlit. Leave every other line untouched.

- [ ] **Step 3: Sync**

```powershell
$env:UV_LINK_MODE = "copy"
uv sync
```

Expected: `credit-paper==0.1.0` resolved from the local path. May also install Gemini / LlamaParse / Firecrawl deps transitively — that's expected (credit_paper depends on them).

- [ ] **Step 4: Smoke import**

```powershell
uv run python -c "from credit_paper.prompts.prompt_manager import load_prompt, _prompts_dir; print('import ok'); print(f'default dir: {_prompts_dir()}')"
```

Expected: `import ok` and a path ending in `\credit_paper\prompts\current`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "deps: add credit-paper editable dep, bump streamlit>=1.40

credit-paper is now importable for the A/B eval harness runner. Streamlit
bumped because the eval results view uses st.pdf() and other widgets that
require 1.40+."
```

---

## Phase B — `eval` Python module

### Task 4: Scaffold the `eval/` package + gitignore

**Files:**
- Create: `prompt_quality_lab/src/prompt_quality_lab/eval/__init__.py` (initially empty)
- Modify: `prompt_quality_lab/.gitignore`

- [ ] **Step 1: Create the package directory + empty init**

```powershell
cd "C:\Users\APR\OneDrive - Anchor Point Risk (Pty) Ltd\Desktop\VS_CODE_REPOSITORY\prompt_quality_lab"
New-Item -ItemType Directory -Path src\prompt_quality_lab\eval -Force | Out-Null
```

`src/prompt_quality_lab/eval/__init__.py`:

```python
"""prompt_quality_lab.eval — A/B prompt evaluation harness.

Public exports filled in by Task 11.
"""
```

- [ ] **Step 2: Add `data/eval_runs/` to gitignore**

Append to `prompt_quality_lab/.gitignore`:

```
# Eval harness run artifacts — local only, OneDrive-backed
data/eval_runs/
```

- [ ] **Step 3: Verify gitignore is effective**

```powershell
New-Item -ItemType Directory -Path data\eval_runs -Force | Out-Null
New-Item -ItemType File -Path data\eval_runs\test.json -Force | Out-Null
git status --short
```

Expected: `data/eval_runs/` should NOT appear in `git status` output. Clean up the test file:

```powershell
Remove-Item data\eval_runs\test.json
Remove-Item data\eval_runs
```

- [ ] **Step 4: Commit**

```bash
git add src/prompt_quality_lab/eval/__init__.py .gitignore
git commit -m "chore(eval): scaffold eval/ package + gitignore data/eval_runs/"
```

---

### Task 5: `eval/schema.py` — Dimension, Rubric, PromptSource, RecordScore, Run

**Files:**
- Create: `prompt_quality_lab/src/prompt_quality_lab/eval/schema.py`
- Create: `prompt_quality_lab/tests/test_eval_schema.py`

- [ ] **Step 1: Write the failing test**

`prompt_quality_lab/tests/test_eval_schema.py`:

```python
from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from datetime import datetime
from pathlib import Path

import pytest

from prompt_quality_lab.eval.schema import (
    Dimension,
    PromptSource,
    RecordScore,
    Rubric,
    Run,
    encode_for_json,
    record_score_to_dict,
    record_score_from_dict,
    run_to_meta_dict,
)


def test_dimension_is_frozen() -> None:
    d = Dimension(name="x", weight=0.5, description="y")
    with pytest.raises(FrozenInstanceError):
        d.name = "z"  # type: ignore[misc]


def test_rubric_weights_must_sum_to_one() -> None:
    # Helper validation lives outside the dataclass — rubrics build manually
    # and we test the validity in test_eval_rubric. Here we just confirm
    # construction works:
    r = Rubric(
        dimensions=[Dimension("a", 0.6, "x"), Dimension("b", 0.4, "y")],
        judge_prompt_template="{dimensions_json}{generated_text}",
    )
    assert len(r.dimensions) == 2


def test_prompt_source_is_frozen() -> None:
    ps = PromptSource(name="current", prompts_dir=Path("/tmp/prompts"))
    with pytest.raises(FrozenInstanceError):
        ps.name = "other"  # type: ignore[misc]


def test_record_score_round_trip() -> None:
    rs = RecordScore(
        record_id="001",
        prompt_source_name="current",
        generated_output="<html>...</html>",
        dimension_scores={"factual_accuracy": 7.5, "completeness": 8.0},
        overall_score=7.75,
        rationale="solid coverage",
        generator_model="gemini-2.5-pro",
        judge_model="claude-opus-4-7",
        duration_seconds=12.34,
        error=None,
    )
    d = record_score_to_dict(rs)
    json_text = json.dumps(d)  # must be JSON-serialisable
    reloaded = record_score_from_dict(json.loads(json_text))
    assert reloaded == rs


def test_record_score_with_error() -> None:
    rs = RecordScore(
        record_id="002",
        prompt_source_name="b",
        generated_output="",
        dimension_scores={},
        overall_score=0.0,
        rationale="",
        generator_model="",
        judge_model="",
        duration_seconds=0.0,
        error="GeminiClient timeout",
    )
    d = record_score_to_dict(rs)
    assert d["error"] == "GeminiClient timeout"
    assert record_score_from_dict(d) == rs


def test_run_meta_dict_excludes_score_arrays() -> None:
    ps = PromptSource(name="current", prompts_dir=Path("/tmp/a"))
    r = Run(
        run_id="run-2026-05-17-foo",
        started_at=datetime(2026, 5, 17, 10, 0, 0),
        finished_at=None,
        record_ids=["001", "002"],
        source_a=ps,
        source_b=ps,
        scores_a=[],
        scores_b=[],
        aggregate_a={},
        aggregate_b={},
        notes="trying tighter conclusions",
        status="running",
    )
    meta = run_to_meta_dict(r)
    assert "scores_a" not in meta
    assert "scores_b" not in meta
    assert meta["run_id"] == "run-2026-05-17-foo"
    assert meta["started_at"] == "2026-05-17T10:00:00"
    assert meta["finished_at"] is None
    assert meta["source_a"] == {"name": "current", "prompts_dir": "/tmp/a"}


def test_encode_for_json_handles_path_and_datetime() -> None:
    assert encode_for_json(Path("/tmp/x")) == "/tmp/x"
    assert encode_for_json(datetime(2026, 5, 17, 10, 0, 0)) == "2026-05-17T10:00:00"
    with pytest.raises(TypeError):
        encode_for_json(object())
```

- [ ] **Step 2: Run — expect failure**

```powershell
cd "C:\Users\APR\OneDrive - Anchor Point Risk (Pty) Ltd\Desktop\VS_CODE_REPOSITORY\prompt_quality_lab"
uv run pytest tests/test_eval_schema.py -v
```

Expected: ImportError on `prompt_quality_lab.eval.schema`.

- [ ] **Step 3: Implement `schema.py`**

`src/prompt_quality_lab/eval/schema.py`:

```python
"""Eval harness data model — pure types, JSON round-trip, no I/O.

Shared by runner, judge, store, and ab modules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Dimension:
    name: str
    weight: float
    description: str


@dataclass(frozen=True)
class Rubric:
    dimensions: list[Dimension]
    judge_prompt_template: str


@dataclass(frozen=True)
class PromptSource:
    name: str
    prompts_dir: Path


@dataclass(frozen=True)
class RecordScore:
    record_id: str
    prompt_source_name: str
    generated_output: str
    dimension_scores: dict[str, float]
    overall_score: float
    rationale: str
    generator_model: str
    judge_model: str
    duration_seconds: float
    error: str | None = None


@dataclass(frozen=True)
class Run:
    run_id: str
    started_at: datetime
    finished_at: datetime | None
    record_ids: list[str]
    source_a: PromptSource
    source_b: PromptSource
    scores_a: list[RecordScore]
    scores_b: list[RecordScore]
    aggregate_a: dict[str, float]
    aggregate_b: dict[str, float]
    notes: str
    status: str  # "running" | "complete" | "cancelled" | "error"


def encode_for_json(obj: Any) -> Any:
    """JSON encoder for Path and datetime; raises TypeError otherwise."""
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serialisable")


def _prompt_source_to_dict(ps: PromptSource) -> dict:
    return {"name": ps.name, "prompts_dir": str(ps.prompts_dir)}


def _prompt_source_from_dict(d: dict) -> PromptSource:
    return PromptSource(name=d["name"], prompts_dir=Path(d["prompts_dir"]))


def record_score_to_dict(rs: RecordScore) -> dict:
    return {
        "record_id": rs.record_id,
        "prompt_source_name": rs.prompt_source_name,
        "generated_output": rs.generated_output,
        "dimension_scores": dict(rs.dimension_scores),
        "overall_score": rs.overall_score,
        "rationale": rs.rationale,
        "generator_model": rs.generator_model,
        "judge_model": rs.judge_model,
        "duration_seconds": rs.duration_seconds,
        "error": rs.error,
    }


def record_score_from_dict(d: dict) -> RecordScore:
    return RecordScore(
        record_id=d["record_id"],
        prompt_source_name=d["prompt_source_name"],
        generated_output=d["generated_output"],
        dimension_scores=dict(d["dimension_scores"]),
        overall_score=d["overall_score"],
        rationale=d["rationale"],
        generator_model=d["generator_model"],
        judge_model=d["judge_model"],
        duration_seconds=d["duration_seconds"],
        error=d.get("error"),
    )


def run_to_meta_dict(r: Run) -> dict:
    """Run minus the per-record score arrays. Stored as meta.json."""
    return {
        "run_id": r.run_id,
        "started_at": r.started_at.isoformat(),
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        "record_ids": list(r.record_ids),
        "source_a": _prompt_source_to_dict(r.source_a),
        "source_b": _prompt_source_to_dict(r.source_b),
        "aggregate_a": dict(r.aggregate_a),
        "aggregate_b": dict(r.aggregate_b),
        "notes": r.notes,
        "status": r.status,
    }


def run_from_meta_dict(d: dict, scores_a: list[RecordScore], scores_b: list[RecordScore]) -> Run:
    """Reverse of run_to_meta_dict; takes loaded scores as separate args."""
    return Run(
        run_id=d["run_id"],
        started_at=datetime.fromisoformat(d["started_at"]),
        finished_at=datetime.fromisoformat(d["finished_at"]) if d["finished_at"] else None,
        record_ids=list(d["record_ids"]),
        source_a=_prompt_source_from_dict(d["source_a"]),
        source_b=_prompt_source_from_dict(d["source_b"]),
        scores_a=scores_a,
        scores_b=scores_b,
        aggregate_a=dict(d["aggregate_a"]),
        aggregate_b=dict(d["aggregate_b"]),
        notes=d["notes"],
        status=d["status"],
    )
```

- [ ] **Step 4: Run — expect pass**

```powershell
uv run pytest tests/test_eval_schema.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add src/prompt_quality_lab/eval/schema.py tests/test_eval_schema.py
git commit -m "feat(eval): schema — dataclasses + JSON round-trip helpers"
```

---

### Task 6: `eval/rubric.py` — CREDIT_RUBRIC constant

**Files:**
- Create: `prompt_quality_lab/src/prompt_quality_lab/eval/rubric.py`
- Create: `prompt_quality_lab/tests/test_eval_rubric.py`

- [ ] **Step 1: Write the failing test**

`prompt_quality_lab/tests/test_eval_rubric.py`:

```python
from __future__ import annotations

import json

from prompt_quality_lab.eval.rubric import CREDIT_RUBRIC


def test_dimension_weights_sum_to_one() -> None:
    total = sum(d.weight for d in CREDIT_RUBRIC.dimensions)
    assert abs(total - 1.0) < 1e-9, f"weights sum to {total}, must be 1.0"


def test_all_dimensions_have_description() -> None:
    for d in CREDIT_RUBRIC.dimensions:
        assert d.description.strip(), f"dimension {d.name} has empty description"


def test_dimension_names_match_spec() -> None:
    names = {d.name for d in CREDIT_RUBRIC.dimensions}
    assert names == {
        "factual_accuracy",
        "completeness",
        "depth_of_analysis",
        "citation_correctness",
        "tone_and_style",
        "absence_of_hallucination",
    }


def test_judge_prompt_template_has_required_placeholders() -> None:
    template = CREDIT_RUBRIC.judge_prompt_template
    assert "{dimensions_json}" in template
    assert "{generated_text}" in template


def test_judge_prompt_template_does_NOT_have_gold_text_placeholder() -> None:
    # The gold PDF is attached as a separate Anthropic content block,
    # not substituted into the template — per spec §5.4.
    assert "{gold_text}" not in CREDIT_RUBRIC.judge_prompt_template


def test_dimensions_json_serialisation() -> None:
    # Verify the rubric can produce the dimensions_json the judge call needs.
    payload = json.dumps([
        {"name": d.name, "description": d.description}
        for d in CREDIT_RUBRIC.dimensions
    ])
    parsed = json.loads(payload)
    assert len(parsed) == len(CREDIT_RUBRIC.dimensions)
```

- [ ] **Step 2: Run — expect failure**

```powershell
uv run pytest tests/test_eval_rubric.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `rubric.py`**

`src/prompt_quality_lab/eval/rubric.py`:

```python
"""Credit-paper scoring rubric — code constant, not a YAML file.

Categories mirror credit_paper's existing prompts/current/audit_criteria.yaml
so the operator's manual audit categories match what the LLM judge scores.

Changing the rubric is a deliberate code change; existing saved runs remain
valid but are not directly comparable to runs scored under the new rubric.
"""
from __future__ import annotations

from prompt_quality_lab.eval.schema import Dimension, Rubric


_JUDGE_PROMPT_TEMPLATE = """You are an expert credit-risk reviewer scoring a generated credit paper against a gold-standard analyst report.

You will be given:
1. The gold analyst report (attached as a PDF document above this message).
2. A candidate generated credit paper (as HTML text, below).

Score the candidate on each of the following dimensions on a 0-10 scale, where 0 is unusable and 10 is indistinguishable from the gold:

{dimensions_json}

You MUST return your scores via the `record_scores` tool. Do not include any other commentary.

The candidate HTML:
<candidate>
{generated_text}
</candidate>

Score now using the record_scores tool."""


CREDIT_RUBRIC = Rubric(
    dimensions=[
        Dimension(
            name="factual_accuracy",
            weight=0.30,
            description="Numbers, dates, names, and claims match the gold report and the underlying AFS. Penalise wrong figures, misattributed ratios, or invented entity names.",
        ),
        Dimension(
            name="completeness",
            weight=0.20,
            description="All sections the gold report covers are present at comparable depth. Penalise missing sections (e.g. no liquidity discussion when gold has one) or visibly truncated content.",
        ),
        Dimension(
            name="depth_of_analysis",
            weight=0.20,
            description="Conclusions are supported by ratio analysis and observation, not just restated. Penalise surface-level commentary that does not use the provided data.",
        ),
        Dimension(
            name="citation_correctness",
            weight=0.15,
            description="Quoted figures correctly attribute their source (AFS year, page, or table). Penalise unsourced numbers or wrong-year attributions.",
        ),
        Dimension(
            name="tone_and_style",
            weight=0.10,
            description="Matches BDO / SARB formal tone. No marketing language, no first-person voice, no emoji, no informal phrasing.",
        ),
        Dimension(
            name="absence_of_hallucination",
            weight=0.05,
            description="No invented entities, dates, ratios, or figures absent from the inputs. Penalise plausible-sounding fabrications harshly.",
        ),
    ],
    judge_prompt_template=_JUDGE_PROMPT_TEMPLATE,
)
```

- [ ] **Step 4: Run — expect pass**

```powershell
uv run pytest tests/test_eval_rubric.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/prompt_quality_lab/eval/rubric.py tests/test_eval_rubric.py
git commit -m "feat(eval): CREDIT_RUBRIC — 6 weighted dimensions + judge prompt"
```

---

### Task 7: `eval/runner.py` — `with_prompts_dir` + `generate()`

**Files:**
- Create: `prompt_quality_lab/src/prompt_quality_lab/eval/runner.py`
- Create: `prompt_quality_lab/tests/test_eval_runner.py`

- [ ] **Step 1: Write the failing test**

`prompt_quality_lab/tests/test_eval_runner.py`:

```python
from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from credit_datasets.schema import AssetClass, QualityGrade, Record, Source
from prompt_quality_lab.eval.runner import (
    GenerationError,
    generate,
    with_prompts_dir,
)


def _make_record(id: str = "001") -> Record:
    return Record(
        id=id,
        company_name="Acme Pty Ltd",
        asset_class=AssetClass.CORPORATE,
        sector="manufacturing",
        afs_years=[2023],
        date_added=date(2026, 5, 17),
        reviewer="test",
        quality_grade=QualityGrade.SILVER,
        source=Source.ANALYST_ORIGINAL,
    )


def test_with_prompts_dir_sets_and_restores(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CREDIT_PAPER_PROMPTS_DIR", raising=False)
    fake = Path("/tmp/fake_prompts")

    with with_prompts_dir(fake):
        assert os.environ["CREDIT_PAPER_PROMPTS_DIR"] == str(fake)

    assert "CREDIT_PAPER_PROMPTS_DIR" not in os.environ


def test_with_prompts_dir_preserves_existing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CREDIT_PAPER_PROMPTS_DIR", "/original")
    fake = Path("/tmp/fake_prompts")

    with with_prompts_dir(fake):
        assert os.environ["CREDIT_PAPER_PROMPTS_DIR"] == str(fake)

    assert os.environ["CREDIT_PAPER_PROMPTS_DIR"] == "/original"


def test_with_prompts_dir_restores_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CREDIT_PAPER_PROMPTS_DIR", raising=False)
    fake = Path("/tmp/fake_prompts")

    with pytest.raises(RuntimeError, match="boom"):
        with with_prompts_dir(fake):
            raise RuntimeError("boom")

    assert "CREDIT_PAPER_PROMPTS_DIR" not in os.environ


def test_generate_invokes_credit_paper_with_overridden_prompts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from prompt_quality_lab.eval.schema import PromptSource

    source = PromptSource(name="current", prompts_dir=tmp_path / "prompts")
    record = _make_record()

    # Stub the credit_paper entry point — must accept the call without exploding,
    # and return a fake HTML string + model id.
    captured_env: dict = {}

    def fake_report_generator(**kwargs):
        captured_env["CREDIT_PAPER_PROMPTS_DIR"] = os.environ.get("CREDIT_PAPER_PROMPTS_DIR")
        return ("<html>generated</html>", "gemini-2.5-pro")

    monkeypatch.setattr(
        "prompt_quality_lab.eval.runner._invoke_credit_paper_stage3",
        fake_report_generator,
    )

    html, model, duration = generate(source, record, dataset_root=tmp_path / "dataset")

    assert html == "<html>generated</html>"
    assert model == "gemini-2.5-pro"
    assert duration >= 0
    assert captured_env["CREDIT_PAPER_PROMPTS_DIR"] == str(source.prompts_dir)
    # After generate returns, env var is restored
    assert "CREDIT_PAPER_PROMPTS_DIR" not in os.environ


def test_generate_wraps_underlying_exception_in_generation_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from prompt_quality_lab.eval.schema import PromptSource

    source = PromptSource(name="current", prompts_dir=tmp_path / "prompts")
    record = _make_record()

    def fake_failing(**kwargs):
        raise ValueError("gemini rate-limited")

    monkeypatch.setattr(
        "prompt_quality_lab.eval.runner._invoke_credit_paper_stage3",
        fake_failing,
    )

    with pytest.raises(GenerationError, match="gemini rate-limited"):
        generate(source, record, dataset_root=tmp_path / "dataset")
```

- [ ] **Step 2: Run — expect failure**

```powershell
uv run pytest tests/test_eval_runner.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `runner.py`**

`src/prompt_quality_lab/eval/runner.py`:

```python
"""Wraps credit_paper's Stage 3 generation so the eval harness can drive it.

Two pieces:
- `with_prompts_dir(...)` — context manager that overrides CREDIT_PAPER_PROMPTS_DIR
  for the duration of a call. Restores prior value even on exception.
- `generate(source, record, dataset_root)` — orchestrates one generation under
  the source's prompts; returns (html, model_id, duration_seconds).

The credit_paper entrypoint call is routed through `_invoke_credit_paper_stage3`
which tests can monkeypatch without touching the real Gemini client.
"""
from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from credit_datasets.schema import Record

from prompt_quality_lab.eval.schema import PromptSource


class GenerationError(Exception):
    """Raised when credit_paper Stage 3 fails (Gemini error, parse error, etc.)."""


@contextmanager
def with_prompts_dir(prompts_dir: Path) -> Iterator[None]:
    """Set CREDIT_PAPER_PROMPTS_DIR for the duration of the block."""
    key = "CREDIT_PAPER_PROMPTS_DIR"
    prev = os.environ.get(key)
    os.environ[key] = str(prompts_dir)
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = prev


def _invoke_credit_paper_stage3(
    *,
    record_dir: Path,
    input_files: list[Path],
) -> tuple[str, str]:
    """Call credit_paper.core.report_generator.generate_report. Returns (html, model_id).

    credit_paper's `generate_report` signature (confirmed against the actual file):

        generate_report(
            target_inputs_dir: Path = None,       # dir with 1 .md ratios + N .pdf AFS
            learning_inputs_dir: Path = None,     # few-shot examples dir (optional)
            output_dir: Path = None,              # where the generated HTML lands
            api_key: str = None,                  # Gemini API key
            model: str = None,                    # Gemini model id
            report_name: str = None,
            log_callback=None,
            prompt_set: str = None,
        ) -> dict                                  # {"success", "output_path", "company_name", "message"}

    It expects a SPECIFIC directory layout: one `.md` ratios file, N `.pdf` AFS files,
    and optionally a `company_business_description.txt`. The generated HTML is written
    to `output_dir` as a file; the function returns metadata referencing the path.

    Implementation:
    1. Stage the record's input files into a temp `target_inputs_dir` matching that layout.
    2. Bail loudly if no `.md` file is present (the eval harness cannot run Stage 1 itself
       — that's LlamaParse-dependent and out of scope for v1; see CAVEAT below).
    3. Call generate_report with target_inputs_dir=temp, output_dir=temp/out.
    4. Read the HTML from result["output_path"] and return (html, model_id).
    5. Use credit_paper's MODELS["report_generation"] constant as the model id since
       generate_report doesn't return it directly.

    CAVEAT — pre-parsed `.md` required: the golden dataset records may contain only `.xlsm`
    + AFS PDFs (per the credit_datasets spec). If so, the eval harness cannot generate;
    the operator must pre-parse the `.xlsm` via credit_paper's Stage 1 (LlamaParse) and
    add the resulting `.md` to the record's `inputs/` folder. The function raises
    `RuntimeError` with a clear message if no `.md` is found. This limitation is
    documented in the harness's README and will be lifted in a follow-up spec if needed.

    Indirected via this function so tests can monkeypatch without importing credit_paper.
    """
    import shutil
    import tempfile

    from credit_paper.core import report_generator as cp_rg  # type: ignore[import-not-found]
    from credit_paper.config.settings import MODELS  # type: ignore[import-not-found]

    md_files = [p for p in input_files if p.suffix.lower() == ".md"]
    pdf_files = [p for p in input_files if p.suffix.lower() == ".pdf"]

    if not md_files:
        raise RuntimeError(
            f"No .md ratios file in record inputs ({[p.name for p in input_files]}). "
            "credit_paper Stage 3 requires a pre-parsed .md; run Stage 1 (LlamaParse) "
            "on the .xlsm first and add the resulting .md to the record's inputs/ folder."
        )

    # Stage files into a temp dir matching credit_paper's expected layout
    tmp_root = Path(tempfile.mkdtemp(prefix="abeval_stage3_"))
    try:
        target_dir = tmp_root / "target"
        output_dir = tmp_root / "out"
        target_dir.mkdir()
        output_dir.mkdir()
        # Only one .md is allowed by generate_report; take the first
        shutil.copy2(md_files[0], target_dir / md_files[0].name)
        for p in pdf_files:
            shutil.copy2(p, target_dir / p.name)
        # company_business_description.txt is optional; copy if present
        for p in input_files:
            if p.name == "company_business_description.txt":
                shutil.copy2(p, target_dir / p.name)

        result = cp_rg.generate_report(
            target_inputs_dir=target_dir,
            output_dir=output_dir,
        )
        if not result.get("success"):
            raise RuntimeError(f"generate_report failed: {result.get('message', 'unknown')}")
        output_path = Path(result["output_path"])
        html = output_path.read_text(encoding="utf-8")
        model_id = MODELS.get("report_generation", "gemini-unknown")
        return html, model_id
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def generate(
    source: PromptSource,
    record: Record,
    dataset_root: Path,
) -> tuple[str, str, float]:
    """Run credit_paper Stage 3 against `record`'s inputs under `source`'s prompts.

    Returns: (generated_html, model_id, duration_seconds).
    Raises: GenerationError on any underlying failure.
    """
    record_dir = record.record_dir(dataset_root)
    input_files = record.input_files(dataset_root)

    start = time.perf_counter()
    try:
        with with_prompts_dir(source.prompts_dir):
            html, model_id = _invoke_credit_paper_stage3(
                record_dir=record_dir,
                input_files=input_files,
            )
    except Exception as e:
        raise GenerationError(str(e)) from e
    duration = time.perf_counter() - start

    return html, model_id, duration
```

- [ ] **Step 4: Run — expect pass**

```powershell
uv run pytest tests/test_eval_runner.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/prompt_quality_lab/eval/runner.py tests/test_eval_runner.py
git commit -m "feat(eval): runner with prompts-dir override + Stage 3 wrapper

_invoke_credit_paper_stage3 is the seam tests monkeypatch. The real
implementation will need adapting once the operator confirms credit_paper's
actual report_generator entry-point signature — see code comments."
```

---

### Task 8: `eval/judge.py` — Claude scoring call

**Files:**
- Create: `prompt_quality_lab/src/prompt_quality_lab/eval/judge.py`
- Create: `prompt_quality_lab/tests/test_eval_judge.py`

- [ ] **Step 1: Write the failing test**

`prompt_quality_lab/tests/test_eval_judge.py`:

```python
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from prompt_quality_lab.eval.judge import JudgeError, score
from prompt_quality_lab.eval.rubric import CREDIT_RUBRIC


def _make_anthropic_client_returning(tool_input: dict) -> MagicMock:
    """Build a MagicMock that mimics Anthropic returning a tool_use response."""
    client = MagicMock()
    # The response shape mimics anthropic.types.Message with one tool_use block
    fake_block = MagicMock()
    fake_block.type = "tool_use"
    fake_block.name = "record_scores"
    fake_block.input = tool_input
    fake_response = MagicMock()
    fake_response.content = [fake_block]
    fake_response.model = "claude-opus-4-7"
    client.messages.create.return_value = fake_response
    return client


def test_score_happy_path(tmp_path: Path) -> None:
    gold_file = tmp_path / "gold.pdf"
    gold_file.write_bytes(b"%PDF-1.4 stub")
    tool_input = {
        "scores": {
            "factual_accuracy": 8.0,
            "completeness": 7.0,
            "depth_of_analysis": 7.5,
            "citation_correctness": 6.5,
            "tone_and_style": 9.0,
            "absence_of_hallucination": 10.0,
        },
        "rationale": "Solid coverage but citations need work.",
    }
    client = _make_anthropic_client_returning(tool_input)

    scores, overall, rationale = score(
        generated_html="<html>candidate</html>",
        gold_file=gold_file,
        rubric=CREDIT_RUBRIC,
        judge_model="claude-opus-4-7",
        anthropic_client=client,
    )

    assert scores["factual_accuracy"] == 8.0
    assert rationale.startswith("Solid coverage")
    # overall = 8.0*0.30 + 7.0*0.20 + 7.5*0.20 + 6.5*0.15 + 9.0*0.10 + 10.0*0.05
    #        = 2.40 + 1.40 + 1.50 + 0.975 + 0.90 + 0.50 = 7.675
    assert abs(overall - 7.675) < 1e-6


def test_score_missing_dimension_in_response_raises(tmp_path: Path) -> None:
    gold_file = tmp_path / "gold.pdf"
    gold_file.write_bytes(b"%PDF-1.4 stub")
    tool_input = {
        "scores": {"factual_accuracy": 8.0},  # missing 5 other dimensions
        "rationale": "incomplete",
    }
    client = _make_anthropic_client_returning(tool_input)

    with pytest.raises(JudgeError, match="missing score"):
        score(
            generated_html="<html/>",
            gold_file=gold_file,
            rubric=CREDIT_RUBRIC,
            anthropic_client=client,
        )


def test_score_no_tool_use_block_raises(tmp_path: Path) -> None:
    gold_file = tmp_path / "gold.pdf"
    gold_file.write_bytes(b"%PDF-1.4 stub")
    client = MagicMock()
    fake_response = MagicMock()
    fake_block = MagicMock()
    fake_block.type = "text"  # not a tool_use block
    fake_response.content = [fake_block]
    fake_response.model = "claude-opus-4-7"
    client.messages.create.return_value = fake_response

    with pytest.raises(JudgeError, match="tool_use"):
        score(
            generated_html="<html/>",
            gold_file=gold_file,
            rubric=CREDIT_RUBRIC,
            anthropic_client=client,
        )


def test_score_api_exception_wrapped(tmp_path: Path) -> None:
    gold_file = tmp_path / "gold.pdf"
    gold_file.write_bytes(b"%PDF-1.4 stub")
    client = MagicMock()
    client.messages.create.side_effect = RuntimeError("api outage")

    with pytest.raises(JudgeError, match="api outage"):
        score(
            generated_html="<html/>",
            gold_file=gold_file,
            rubric=CREDIT_RUBRIC,
            anthropic_client=client,
        )


def test_score_score_out_of_range_clipped(tmp_path: Path) -> None:
    """The judge might return 11 or -1 — the harness must clip to [0, 10]."""
    gold_file = tmp_path / "gold.pdf"
    gold_file.write_bytes(b"%PDF-1.4 stub")
    tool_input = {
        "scores": {
            "factual_accuracy": 11.0,           # over
            "completeness": -1.0,               # under
            "depth_of_analysis": 5.0,
            "citation_correctness": 5.0,
            "tone_and_style": 5.0,
            "absence_of_hallucination": 5.0,
        },
        "rationale": "out-of-range test",
    }
    client = _make_anthropic_client_returning(tool_input)
    scores, _, _ = score(
        generated_html="<html/>",
        gold_file=gold_file,
        rubric=CREDIT_RUBRIC,
        anthropic_client=client,
    )
    assert scores["factual_accuracy"] == 10.0
    assert scores["completeness"] == 0.0
```

- [ ] **Step 2: Run — expect failure**

```powershell
uv run pytest tests/test_eval_judge.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `judge.py`**

`src/prompt_quality_lab/eval/judge.py`:

```python
"""Claude-as-judge scoring for the eval harness.

Builds an Anthropic tool-use call that forces the judge to return a structured
score per dimension plus a free-text rationale. The gold PDF is attached as
a document content block; the candidate HTML is templated into the user message.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

from prompt_quality_lab.eval.schema import Rubric


class JudgeError(Exception):
    """Raised when the Anthropic judge call or its parse fails."""


_TOOL_SCHEMA = {
    "name": "record_scores",
    "description": "Record the per-dimension scores and rationale for the candidate.",
    "input_schema": {
        "type": "object",
        "properties": {
            "scores": {
                "type": "object",
                "description": "Map of dimension name to score in [0, 10].",
                "additionalProperties": {"type": "number"},
            },
            "rationale": {
                "type": "string",
                "description": "2-4 sentences justifying the scores.",
            },
        },
        "required": ["scores", "rationale"],
    },
}


def _clip(score_val: float) -> float:
    if score_val < 0.0:
        return 0.0
    if score_val > 10.0:
        return 10.0
    return float(score_val)


def score(
    generated_html: str,
    gold_file: Path,
    rubric: Rubric,
    judge_model: str = "claude-opus-4-7",
    *,
    anthropic_client: Any | None = None,
    max_tokens: int = 2000,
) -> tuple[dict[str, float], float, str]:
    """Return (per-dimension scores, weighted overall, rationale)."""
    if anthropic_client is None:
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise JudgeError("anthropic package not installed") from e
        anthropic_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    dimensions_json = json.dumps(
        [{"name": d.name, "description": d.description} for d in rubric.dimensions],
        indent=2,
    )
    user_text = rubric.judge_prompt_template.format(
        dimensions_json=dimensions_json,
        generated_text=generated_html,
    )

    gold_b64 = base64.standard_b64encode(gold_file.read_bytes()).decode("ascii")

    try:
        response = anthropic_client.messages.create(
            model=judge_model,
            max_tokens=max_tokens,
            tools=[_TOOL_SCHEMA],
            tool_choice={"type": "tool", "name": "record_scores"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": gold_b64,
                            },
                        },
                        {"type": "text", "text": user_text},
                    ],
                }
            ],
        )
    except Exception as e:
        raise JudgeError(str(e)) from e

    # Find the tool_use block
    tool_block = None
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == "record_scores":
            tool_block = block
            break
    if tool_block is None:
        raise JudgeError("response did not contain a tool_use block named record_scores")

    payload = tool_block.input
    raw_scores = payload.get("scores", {})
    rationale = payload.get("rationale", "")

    # Validate + clip per dimension
    scores: dict[str, float] = {}
    for d in rubric.dimensions:
        if d.name not in raw_scores:
            raise JudgeError(f"missing score for dimension {d.name!r}")
        scores[d.name] = _clip(float(raw_scores[d.name]))

    overall = sum(scores[d.name] * d.weight for d in rubric.dimensions)
    return scores, overall, rationale
```

- [ ] **Step 4: Run — expect pass**

```powershell
uv run pytest tests/test_eval_judge.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/prompt_quality_lab/eval/judge.py tests/test_eval_judge.py
git commit -m "feat(eval): judge — Claude tool-use scoring with rubric"
```

---

### Task 9: `eval/store.py` — JSONL persistence for runs

**Files:**
- Create: `prompt_quality_lab/src/prompt_quality_lab/eval/store.py`
- Create: `prompt_quality_lab/tests/test_eval_store.py`

- [ ] **Step 1: Write the failing test**

`prompt_quality_lab/tests/test_eval_store.py`:

```python
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from prompt_quality_lab.eval.schema import (
    PromptSource,
    RecordScore,
    Run,
)
from prompt_quality_lab.eval.store import (
    eval_runs_root,
    list_runs,
    load_run,
    save_run,
)


def _make_run(
    run_id: str = "run-2026-05-17-test",
    record_count: int = 2,
    status: str = "complete",
) -> Run:
    ps_a = PromptSource(name="current", prompts_dir=Path("/tmp/a"))
    ps_b = PromptSource(name="draft", prompts_dir=Path("/tmp/b"))
    record_ids = [f"{i:03d}" for i in range(1, record_count + 1)]

    def _score(rid: str, source_name: str) -> RecordScore:
        return RecordScore(
            record_id=rid,
            prompt_source_name=source_name,
            generated_output=f"<html>{rid}-{source_name}</html>",
            dimension_scores={"factual_accuracy": 7.0},
            overall_score=7.0,
            rationale="ok",
            generator_model="gemini-2.5-pro",
            judge_model="claude-opus-4-7",
            duration_seconds=1.0,
            error=None,
        )

    return Run(
        run_id=run_id,
        started_at=datetime(2026, 5, 17, 10, 0, 0),
        finished_at=datetime(2026, 5, 17, 10, 30, 0) if status == "complete" else None,
        record_ids=record_ids,
        source_a=ps_a,
        source_b=ps_b,
        scores_a=[_score(rid, "current") for rid in record_ids],
        scores_b=[_score(rid, "draft") for rid in record_ids],
        aggregate_a={"factual_accuracy": 7.0},
        aggregate_b={"factual_accuracy": 7.0},
        notes="test run",
        status=status,
    )


@pytest.fixture
def tmp_eval_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "eval_runs"
    monkeypatch.setenv("PROMPT_QUALITY_LAB_EVAL_RUNS_ROOT", str(root))
    return root


def test_eval_runs_root_creates_dir(tmp_eval_root: Path) -> None:
    r = eval_runs_root()
    assert r == tmp_eval_root
    assert r.exists()


def test_save_then_load_round_trip(tmp_eval_root: Path) -> None:
    run = _make_run()
    save_run(run)
    loaded = load_run(run.run_id)
    assert loaded == run


def test_save_writes_expected_files(tmp_eval_root: Path) -> None:
    run = _make_run(record_count=2)
    save_run(run)
    run_dir = tmp_eval_root / "runs" / run.run_id
    assert (run_dir / "meta.json").exists()
    assert (run_dir / "scores_a.jsonl").exists()
    assert (run_dir / "scores_b.jsonl").exists()
    # 2 records per source
    assert len((run_dir / "scores_a.jsonl").read_text(encoding="utf-8").strip().splitlines()) == 2
    assert len((run_dir / "scores_b.jsonl").read_text(encoding="utf-8").strip().splitlines()) == 2
    # Outputs dir created and populated
    outputs = run_dir / "outputs"
    assert outputs.exists()
    assert (outputs / "001_a.html").exists()
    assert (outputs / "001_b.html").exists()


def test_index_appended_on_save(tmp_eval_root: Path) -> None:
    save_run(_make_run(run_id="run-1"))
    save_run(_make_run(run_id="run-2"))
    save_run(_make_run(run_id="run-3"))

    entries = list_runs()
    # Newest first
    assert [e["run_id"] for e in entries] == ["run-3", "run-2", "run-1"]
    assert all("started_at" in e for e in entries)
    assert all("source_a" in e for e in entries)
    assert all("status" in e for e in entries)


def test_save_overwrites_existing_run(tmp_eval_root: Path) -> None:
    save_run(_make_run(notes="first"))
    save_run(_make_run(notes="second"))
    loaded = load_run("run-2026-05-17-test")
    assert loaded.notes == "second"
    # Index has only one entry for this run_id
    entries = [e for e in list_runs() if e["run_id"] == "run-2026-05-17-test"]
    assert len(entries) == 1
    assert entries[0]["notes"] == "second"


def test_save_partial_run_is_valid(tmp_eval_root: Path) -> None:
    """A run with status=running and fewer scores than record_ids should still save."""
    ps = PromptSource(name="current", prompts_dir=Path("/tmp/a"))
    partial = Run(
        run_id="run-partial",
        started_at=datetime(2026, 5, 17, 10, 0, 0),
        finished_at=None,
        record_ids=["001", "002", "003"],
        source_a=ps,
        source_b=ps,
        scores_a=[],  # nothing scored yet
        scores_b=[],
        aggregate_a={},
        aggregate_b={},
        notes="",
        status="running",
    )
    save_run(partial)
    loaded = load_run("run-partial")
    assert loaded.status == "running"
    assert loaded.scores_a == []
```

- [ ] **Step 2: Run — expect failure**

```powershell
uv run pytest tests/test_eval_store.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `store.py`**

`src/prompt_quality_lab/eval/store.py`:

```python
"""JSONL-on-disk persistence for eval runs.

Layout:
    <root>/
    ├── index.json
    └── runs/
        └── <run_id>/
            ├── meta.json
            ├── scores_a.jsonl
            ├── scores_b.jsonl
            └── outputs/
                ├── <record_id>_a.html
                └── <record_id>_b.html

Atomicity: meta.json writes go through a `.tmp` file + rename. Index updates
read-modify-write the JSON file (single-writer assumption — Streamlit is a
single-user app).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from prompt_quality_lab.eval.schema import (
    Run,
    record_score_from_dict,
    record_score_to_dict,
    run_from_meta_dict,
    run_to_meta_dict,
)


def eval_runs_root() -> Path:
    """Resolve the eval-runs root.

    Order:
    1. $PROMPT_QUALITY_LAB_EVAL_RUNS_ROOT (used by tests)
    2. <package>/../../data/eval_runs (when running from a source checkout)
    """
    env = os.environ.get("PROMPT_QUALITY_LAB_EVAL_RUNS_ROOT")
    if env:
        root = Path(env)
    else:
        root = Path(__file__).parent.parent.parent.parent / "data" / "eval_runs"
    root.mkdir(parents=True, exist_ok=True)
    (root / "runs").mkdir(exist_ok=True)
    return root


def _index_path(root: Path) -> Path:
    return root / "index.json"


def _read_index(root: Path) -> list[dict]:
    p = _index_path(root)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def _write_index(root: Path, entries: list[dict]) -> None:
    p = _index_path(root)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)


def _index_entry(run: Run) -> dict:
    return {
        "run_id": run.run_id,
        "started_at": run.started_at.isoformat(),
        "source_a": run.source_a.name,
        "source_b": run.source_b.name,
        "notes": run.notes,
        "status": run.status,
        "record_count": len(run.record_ids),
    }


def save_run(run: Run, root: Path | None = None) -> None:
    """Persist a Run (meta.json + scores_*.jsonl + outputs/) and update the index.

    Overwrites if run_id already exists. Safe to call repeatedly during a
    partial run (status='running' with incomplete scores arrays).
    """
    r = root if root is not None else eval_runs_root()
    run_dir = r / "runs" / run.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir = run_dir / "outputs"
    outputs_dir.mkdir(exist_ok=True)

    # meta.json (atomic)
    meta = run_to_meta_dict(run)
    meta_path = run_dir / "meta.json"
    meta_tmp = meta_path.with_suffix(meta_path.suffix + ".tmp")
    meta_tmp.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    meta_tmp.replace(meta_path)

    # scores_a.jsonl + scores_b.jsonl
    for label, scores in (("a", run.scores_a), ("b", run.scores_b)):
        path = run_dir / f"scores_{label}.jsonl"
        lines = [json.dumps(record_score_to_dict(s)) for s in scores]
        path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    # outputs/<record_id>_<label>.html
    for label, scores in (("a", run.scores_a), ("b", run.scores_b)):
        for s in scores:
            if s.generated_output:
                (outputs_dir / f"{s.record_id}_{label}.html").write_text(
                    s.generated_output, encoding="utf-8"
                )

    # index
    entries = _read_index(r)
    entries = [e for e in entries if e["run_id"] != run.run_id]
    entries.append(_index_entry(run))
    _write_index(r, entries)


def load_run(run_id: str, root: Path | None = None) -> Run:
    """Reverse of save_run."""
    r = root if root is not None else eval_runs_root()
    run_dir = r / "runs" / run_id
    meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))

    def _read_jsonl(path: Path):
        if not path.exists():
            return []
        return [
            record_score_from_dict(json.loads(line))
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    scores_a = _read_jsonl(run_dir / "scores_a.jsonl")
    scores_b = _read_jsonl(run_dir / "scores_b.jsonl")
    return run_from_meta_dict(meta, scores_a, scores_b)


def list_runs(root: Path | None = None) -> list[dict]:
    """Return all index entries, newest first."""
    r = root if root is not None else eval_runs_root()
    return sorted(_read_index(r), key=lambda e: e["started_at"], reverse=True)
```

- [ ] **Step 4: Run — expect pass**

```powershell
uv run pytest tests/test_eval_store.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/prompt_quality_lab/eval/store.py tests/test_eval_store.py
git commit -m "feat(eval): store — save/load Run + index, atomic meta.json"
```

---

### Task 10: `eval/ab.py` — `run_ab()` orchestrator

**Files:**
- Create: `prompt_quality_lab/src/prompt_quality_lab/eval/ab.py`
- Create: `prompt_quality_lab/tests/test_eval_ab.py`

- [ ] **Step 1: Write the failing test**

`prompt_quality_lab/tests/test_eval_ab.py`:

```python
from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from credit_datasets import store as cd_store
from credit_datasets.schema import AssetClass, QualityGrade, Record, Source
from prompt_quality_lab.eval import ab
from prompt_quality_lab.eval.schema import PromptSource


@pytest.fixture
def tmp_dataset_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A temp credit_datasets root with 3 seeded records."""
    root = tmp_path / "dataset"
    root.mkdir()
    (root / "records").mkdir()
    (root / "manifest.json").write_text('{"version": 1, "records": []}\n', encoding="utf-8")
    monkeypatch.setenv("CREDIT_DATASETS_ROOT", str(root))

    src = tmp_path / "src"
    src.mkdir()
    (src / "in.pdf").write_bytes(b"in")
    (src / "gold.pdf").write_bytes(b"gold")

    for i in range(1, 4):
        rec = Record(
            id=f"{i:03d}",
            company_name=f"Co{i}",
            asset_class=AssetClass.CORPORATE,
            sector="manufacturing",
            afs_years=[2023],
            date_added=date(2026, 5, 17),
            reviewer="x",
            quality_grade=QualityGrade.SILVER,
            source=Source.ANALYST_ORIGINAL,
        )
        cd_store.add_record(rec, [src / "in.pdf"], src / "gold.pdf", root)

    return root


@pytest.fixture
def tmp_eval_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "eval_runs"
    monkeypatch.setenv("PROMPT_QUALITY_LAB_EVAL_RUNS_ROOT", str(root))
    return root


def test_run_ab_happy_path(
    tmp_dataset_root: Path, tmp_eval_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_a = PromptSource("current", tmp_dataset_root / "prompts_a")
    source_b = PromptSource("draft", tmp_dataset_root / "prompts_b")

    # Stub generate + score to return deterministic results
    def fake_generate(source, record, dataset_root):
        return (f"<html>{source.name}-{record.id}</html>", "gemini-2.5-pro", 0.1)

    def fake_score(generated_html, gold_file, rubric, judge_model, **kwargs):
        # Source A scores 7.0, Source B scores 8.0
        base = 8.0 if "draft" in generated_html else 7.0
        scores = {d.name: base for d in rubric.dimensions}
        overall = base
        return scores, overall, f"rationale for {generated_html[:20]}"

    monkeypatch.setattr("prompt_quality_lab.eval.ab.generate", fake_generate)
    monkeypatch.setattr("prompt_quality_lab.eval.ab.score", fake_score)

    run = ab.run_ab(
        source_a=source_a,
        source_b=source_b,
        record_ids=["001", "002", "003"],
        notes="smoke",
    )

    assert run.status == "complete"
    assert len(run.scores_a) == 3
    assert len(run.scores_b) == 3
    # Aggregates
    assert run.aggregate_a["factual_accuracy"] == 7.0
    assert run.aggregate_b["factual_accuracy"] == 8.0
    # Persisted
    from prompt_quality_lab.eval.store import load_run
    reloaded = load_run(run.run_id)
    assert reloaded.status == "complete"


def test_run_ab_handles_per_record_generation_error(
    tmp_dataset_root: Path, tmp_eval_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_a = PromptSource("current", tmp_dataset_root / "prompts_a")
    source_b = PromptSource("draft", tmp_dataset_root / "prompts_b")

    call_log = []

    def flaky_generate(source, record, dataset_root):
        call_log.append((source.name, record.id))
        if record.id == "002" and source.name == "draft":
            from prompt_quality_lab.eval.runner import GenerationError
            raise GenerationError("synthetic failure")
        return (f"<html>{source.name}-{record.id}</html>", "gemini-2.5-pro", 0.1)

    def fake_score(generated_html, gold_file, rubric, judge_model, **kwargs):
        scores = {d.name: 5.0 for d in rubric.dimensions}
        return scores, 5.0, "ok"

    monkeypatch.setattr("prompt_quality_lab.eval.ab.generate", flaky_generate)
    monkeypatch.setattr("prompt_quality_lab.eval.ab.score", fake_score)

    run = ab.run_ab(
        source_a=source_a,
        source_b=source_b,
        record_ids=["001", "002", "003"],
        notes="error test",
    )

    # The errored record's source_b score has error populated
    errored = [s for s in run.scores_b if s.error is not None]
    assert len(errored) == 1
    assert errored[0].record_id == "002"
    assert "synthetic failure" in errored[0].error
    # Run still completes overall (since at least some records succeeded)
    assert run.status == "complete"


def test_run_ab_cancel_check_halts(
    tmp_dataset_root: Path, tmp_eval_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_a = PromptSource("current", tmp_dataset_root / "prompts_a")
    source_b = PromptSource("draft", tmp_dataset_root / "prompts_b")

    def fake_generate(source, record, dataset_root):
        return (f"<html>{source.name}-{record.id}</html>", "gemini", 0.1)

    def fake_score(generated_html, gold_file, rubric, judge_model, **kwargs):
        scores = {d.name: 5.0 for d in rubric.dimensions}
        return scores, 5.0, "ok"

    monkeypatch.setattr("prompt_quality_lab.eval.ab.generate", fake_generate)
    monkeypatch.setattr("prompt_quality_lab.eval.ab.score", fake_score)

    # Cancel after the first record completes
    counter = {"i": 0}
    def cancel_after_one():
        counter["i"] += 1
        return counter["i"] > 1

    run = ab.run_ab(
        source_a=source_a,
        source_b=source_b,
        record_ids=["001", "002", "003"],
        notes="cancel test",
        cancel_check=cancel_after_one,
    )

    assert run.status == "cancelled"
    assert len(run.scores_a) == 1
    assert len(run.scores_b) == 1
    assert run.finished_at is not None


def test_run_ab_progress_callback_invoked(
    tmp_dataset_root: Path, tmp_eval_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_a = PromptSource("current", tmp_dataset_root / "prompts_a")
    source_b = PromptSource("draft", tmp_dataset_root / "prompts_b")

    monkeypatch.setattr(
        "prompt_quality_lab.eval.ab.generate",
        lambda src, rec, root: ("<html/>", "gemini", 0.0),
    )
    monkeypatch.setattr(
        "prompt_quality_lab.eval.ab.score",
        lambda gen, gold, rub, judge, **kw: (
            {d.name: 5.0 for d in rub.dimensions}, 5.0, "ok",
        ),
    )

    calls = []
    def on_progress(current: int, total: int, msg: str) -> None:
        calls.append((current, total, msg))

    ab.run_ab(
        source_a=source_a,
        source_b=source_b,
        record_ids=["001", "002"],
        progress_callback=on_progress,
    )

    # At minimum, one call per completed record
    assert any(c[0] == 1 and c[1] == 2 for c in calls)
    assert any(c[0] == 2 and c[1] == 2 for c in calls)
```

- [ ] **Step 2: Run — expect failure**

```powershell
uv run pytest tests/test_eval_ab.py -v
```

Expected: ImportError on `ab.run_ab`.

- [ ] **Step 3: Implement `ab.py`**

`src/prompt_quality_lab/eval/ab.py`:

```python
"""A/B orchestrator — runs generate + score for each (record × source) pair.

Persists partial state after every record so a crashed/cancelled run is
recoverable.
"""
from __future__ import annotations

import secrets
from datetime import datetime
from pathlib import Path
from typing import Callable

from credit_datasets import get_record
from credit_datasets.schema import Record

from prompt_quality_lab.eval.judge import score
from prompt_quality_lab.eval.rubric import CREDIT_RUBRIC
from prompt_quality_lab.eval.runner import GenerationError, generate
from prompt_quality_lab.eval.schema import (
    PromptSource,
    RecordScore,
    Run,
)
from prompt_quality_lab.eval.store import save_run


def _new_run_id() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    suffix = secrets.token_hex(3)
    return f"run-{today}-{suffix}"


def _aggregate(scores: list[RecordScore]) -> dict[str, float]:
    """Mean dimension scores across successful records (errored records skipped)."""
    successful = [s for s in scores if s.error is None and s.dimension_scores]
    if not successful:
        return {}
    keys = set()
    for s in successful:
        keys.update(s.dimension_scores.keys())
    out: dict[str, float] = {}
    for k in keys:
        vals = [s.dimension_scores.get(k, 0.0) for s in successful if k in s.dimension_scores]
        out[k] = sum(vals) / len(vals) if vals else 0.0
    return out


def _run_one(
    source: PromptSource,
    record: Record,
    dataset_root: Path,
    judge_model: str,
) -> RecordScore:
    """Generate + score for one (source, record). Catches both layer failures."""
    try:
        html, model_id, duration = generate(source, record, dataset_root)
    except GenerationError as e:
        return RecordScore(
            record_id=record.id,
            prompt_source_name=source.name,
            generated_output="",
            dimension_scores={},
            overall_score=0.0,
            rationale="",
            generator_model="",
            judge_model="",
            duration_seconds=0.0,
            error=f"generation: {e}",
        )

    gold_file = record.gold_file(dataset_root)
    if gold_file is None:
        return RecordScore(
            record_id=record.id,
            prompt_source_name=source.name,
            generated_output=html,
            dimension_scores={},
            overall_score=0.0,
            rationale="",
            generator_model=model_id,
            judge_model="",
            duration_seconds=duration,
            error="no gold file for record",
        )

    try:
        scores, overall, rationale = score(
            generated_html=html,
            gold_file=gold_file,
            rubric=CREDIT_RUBRIC,
            judge_model=judge_model,
        )
    except Exception as e:  # JudgeError or unexpected
        return RecordScore(
            record_id=record.id,
            prompt_source_name=source.name,
            generated_output=html,
            dimension_scores={},
            overall_score=0.0,
            rationale="",
            generator_model=model_id,
            judge_model=judge_model,
            duration_seconds=duration,
            error=f"scoring: {e}",
        )

    return RecordScore(
        record_id=record.id,
        prompt_source_name=source.name,
        generated_output=html,
        dimension_scores=scores,
        overall_score=overall,
        rationale=rationale,
        generator_model=model_id,
        judge_model=judge_model,
        duration_seconds=duration,
        error=None,
    )


def run_ab(
    source_a: PromptSource,
    source_b: PromptSource,
    record_ids: list[str],
    *,
    notes: str = "",
    judge_model: str = "claude-opus-4-7",
    parallelism: int = 1,
    progress_callback: Callable[[int, int, str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
    dataset_root: Path | None = None,
) -> Run:
    """Run an A/B comparison: source_a vs source_b across record_ids."""
    from credit_datasets import dataset_root as cds_root
    if dataset_root is None:
        dataset_root = cds_root()

    run = Run(
        run_id=_new_run_id(),
        started_at=datetime.now(),
        finished_at=None,
        record_ids=list(record_ids),
        source_a=source_a,
        source_b=source_b,
        scores_a=[],
        scores_b=[],
        aggregate_a={},
        aggregate_b={},
        notes=notes,
        status="running",
    )
    save_run(run)

    scores_a: list[RecordScore] = []
    scores_b: list[RecordScore] = []
    total = len(record_ids)

    for i, rid in enumerate(record_ids, start=1):
        if cancel_check is not None and cancel_check():
            run = Run(
                run_id=run.run_id,
                started_at=run.started_at,
                finished_at=datetime.now(),
                record_ids=run.record_ids,
                source_a=run.source_a,
                source_b=run.source_b,
                scores_a=scores_a,
                scores_b=scores_b,
                aggregate_a=_aggregate(scores_a),
                aggregate_b=_aggregate(scores_b),
                notes=run.notes,
                status="cancelled",
            )
            save_run(run)
            return run

        record = get_record(rid)

        sa = _run_one(source_a, record, dataset_root, judge_model)
        scores_a.append(sa)
        sb = _run_one(source_b, record, dataset_root, judge_model)
        scores_b.append(sb)

        if progress_callback is not None:
            progress_callback(i, total, f"record {rid}: A={sa.overall_score:.2f} B={sb.overall_score:.2f}")

        # Save partial state after each record
        run = Run(
            run_id=run.run_id,
            started_at=run.started_at,
            finished_at=None,
            record_ids=run.record_ids,
            source_a=run.source_a,
            source_b=run.source_b,
            scores_a=scores_a,
            scores_b=scores_b,
            aggregate_a={},
            aggregate_b={},
            notes=run.notes,
            status="running",
        )
        save_run(run)

    # Done
    all_errored = (
        all(s.error is not None for s in scores_a)
        and all(s.error is not None for s in scores_b)
    )
    final_status = "error" if all_errored else "complete"

    run = Run(
        run_id=run.run_id,
        started_at=run.started_at,
        finished_at=datetime.now(),
        record_ids=run.record_ids,
        source_a=run.source_a,
        source_b=run.source_b,
        scores_a=scores_a,
        scores_b=scores_b,
        aggregate_a=_aggregate(scores_a),
        aggregate_b=_aggregate(scores_b),
        notes=run.notes,
        status=final_status,
    )
    save_run(run)
    return run
```

Note: `parallelism` is accepted in the signature for forward-compat but currently ignored — the loop runs sequentially. Concurrent execution can be added later if rate limits allow.

- [ ] **Step 4: Run — expect pass**

```powershell
uv run pytest tests/test_eval_ab.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/prompt_quality_lab/eval/ab.py tests/test_eval_ab.py
git commit -m "feat(eval): ab.run_ab orchestrator with partial-state persistence"
```

---

### Task 11: `eval/__init__.py` — public exports + importability test

**Files:**
- Modify: `prompt_quality_lab/src/prompt_quality_lab/eval/__init__.py`
- Create: `prompt_quality_lab/tests/test_eval_public_api.py`

- [ ] **Step 1: Replace `__init__.py` with the real public exports**

`src/prompt_quality_lab/eval/__init__.py`:

```python
"""prompt_quality_lab.eval — A/B prompt evaluation harness.

Public API:
    Dimension, PromptSource, RecordScore, Rubric, Run
    CREDIT_RUBRIC
    generate, GenerationError
    score, JudgeError
    save_run, load_run, list_runs, eval_runs_root
    run_ab
"""
from prompt_quality_lab.eval.ab import run_ab
from prompt_quality_lab.eval.judge import JudgeError, score
from prompt_quality_lab.eval.rubric import CREDIT_RUBRIC
from prompt_quality_lab.eval.runner import GenerationError, generate, with_prompts_dir
from prompt_quality_lab.eval.schema import (
    Dimension,
    PromptSource,
    RecordScore,
    Rubric,
    Run,
)
from prompt_quality_lab.eval.store import (
    eval_runs_root,
    list_runs,
    load_run,
    save_run,
)

__all__ = [
    "CREDIT_RUBRIC",
    "Dimension",
    "GenerationError",
    "JudgeError",
    "PromptSource",
    "RecordScore",
    "Rubric",
    "Run",
    "eval_runs_root",
    "generate",
    "list_runs",
    "load_run",
    "run_ab",
    "save_run",
    "score",
    "with_prompts_dir",
]
```

- [ ] **Step 2: Write the importability test**

`prompt_quality_lab/tests/test_eval_public_api.py`:

```python
def test_eval_public_api_imports() -> None:
    import prompt_quality_lab.eval as e

    for name in [
        "CREDIT_RUBRIC", "Dimension", "GenerationError", "JudgeError",
        "PromptSource", "RecordScore", "Rubric", "Run",
        "eval_runs_root", "generate", "list_runs", "load_run",
        "run_ab", "save_run", "score", "with_prompts_dir",
    ]:
        assert hasattr(e, name), f"missing public export: {name}"
```

- [ ] **Step 3: Run — expect pass**

```powershell
uv run pytest tests/test_eval_public_api.py -v
uv run pytest tests/ -v --ignore=tests/test_loaders.py
```

Expected: `test_eval_public_api.py` passes; full suite (minus the pre-existing test_loaders.py failures from sub-project 1) passes — should be ~40+ new eval tests + 5 dataset_manager tests.

- [ ] **Step 4: Commit**

```bash
git add src/prompt_quality_lab/eval/__init__.py tests/test_eval_public_api.py
git commit -m "feat(eval): public API exports + importability test"
```

---

### Task 12: `credit_paper` integration smoke test

**Files:**
- Create: `prompt_quality_lab/tests/test_credit_paper_integration.py`

- [ ] **Step 1: Write the test**

`prompt_quality_lab/tests/test_credit_paper_integration.py`:

```python
"""End-to-end smoke for the credit_paper integration.

Verifies:
- credit_paper.prompts.prompt_manager imports cleanly from prompt_quality_lab's venv.
- The CREDIT_PAPER_PROMPTS_DIR env var is honoured.
- The runner's with_prompts_dir() context manager actually swaps + restores.

No Gemini calls; no LlamaParse calls; just confirms the plumbing.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from prompt_quality_lab.eval.runner import with_prompts_dir


def test_credit_paper_prompt_manager_imports() -> None:
    from credit_paper.prompts import prompt_manager
    assert hasattr(prompt_manager, "_prompts_dir")
    assert hasattr(prompt_manager, "load_prompt")


def test_env_var_swap_is_observable_from_credit_paper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CREDIT_PAPER_PROMPTS_DIR", raising=False)

    fake_dir = tmp_path / "fake_prompts"
    fake_dir.mkdir()
    (fake_dir / "report_instructions.yaml").write_text(
        yaml.safe_dump({"role_definition": "STUB FROM TEST"}),
        encoding="utf-8",
    )

    from credit_paper.prompts import prompt_manager

    # Before swap: default
    assert prompt_manager._prompts_dir().name == "current"

    # During swap: fake
    with with_prompts_dir(fake_dir):
        assert prompt_manager._prompts_dir() == fake_dir
        loaded = prompt_manager.load_prompt("report_instructions")
        assert loaded["role_definition"] == "STUB FROM TEST"

    # After swap: default restored
    assert prompt_manager._prompts_dir().name == "current"
    assert "CREDIT_PAPER_PROMPTS_DIR" not in os.environ
```

- [ ] **Step 2: Run — expect pass**

```powershell
cd "C:\Users\APR\OneDrive - Anchor Point Risk (Pty) Ltd\Desktop\VS_CODE_REPOSITORY\prompt_quality_lab"
uv run pytest tests/test_credit_paper_integration.py -v
```

Expected: 2 passed.

If it fails because `credit_paper/prompts/current/` doesn't exist on disk (the default fallback can't resolve), this means the test's "current" assumption was wrong. Adapt the assertion to whatever `prompt_manager._DEFAULT_PROMPTS_DIR` actually points at in the real credit_paper repo.

- [ ] **Step 3: Commit**

```bash
git add tests/test_credit_paper_integration.py
git commit -m "test: credit_paper env-var override end-to-end smoke"
```

---

## Phase C — `ab_eval` Streamlit page

### Task 13: Scaffold `ab_eval/` + page shim + stub `render()`

**Files:**
- Create: `prompt_quality_lab/src/prompt_quality_lab/ab_eval/__init__.py`
- Create: `prompt_quality_lab/src/prompt_quality_lab/ab_eval/page.py`
- Create: `prompt_quality_lab/pages/2_AB_Eval.py`

- [ ] **Step 1: Create the package + shim files**

```powershell
cd "C:\Users\APR\OneDrive - Anchor Point Risk (Pty) Ltd\Desktop\VS_CODE_REPOSITORY\prompt_quality_lab"
New-Item -ItemType Directory -Path src\prompt_quality_lab\ab_eval -Force | Out-Null
```

`src/prompt_quality_lab/ab_eval/__init__.py`:

```python
```

(empty)

`src/prompt_quality_lab/ab_eval/page.py`:

```python
"""A/B Eval — Streamlit page composition. Real views filled in Tasks 15-17."""
from __future__ import annotations

import streamlit as st


_MODE_SETUP = "Setup"
_MODE_PROGRESS = "Progress"
_MODE_RESULTS = "Results"


def render() -> None:
    st.set_page_config(page_title="A/B Eval", layout="wide")
    st.title("A/B Eval")

    mode = st.radio(
        "Mode",
        options=[_MODE_SETUP, _MODE_PROGRESS, _MODE_RESULTS],
        horizontal=True,
        key="abeval_mode",
    )

    if mode == _MODE_SETUP:
        from prompt_quality_lab.ab_eval.setup_view import render_setup
        render_setup()
    elif mode == _MODE_PROGRESS:
        from prompt_quality_lab.ab_eval.progress_view import render_progress
        render_progress()
    elif mode == _MODE_RESULTS:
        from prompt_quality_lab.ab_eval.results_view import render_results
        render_results()
    else:
        st.error(f"Unknown mode: {mode}")
```

`pages/2_AB_Eval.py`:

```python
"""Streamlit auto-discovered page for the A/B Eval harness."""
from prompt_quality_lab.ab_eval.page import render

render()
```

- [ ] **Step 2: Create placeholder view modules so imports succeed**

`src/prompt_quality_lab/ab_eval/setup_view.py`:

```python
import streamlit as st


def render_setup() -> None:
    st.write("Setup — coming in Task 15.")
```

`src/prompt_quality_lab/ab_eval/progress_view.py`:

```python
import streamlit as st


def render_progress() -> None:
    st.write("Progress — coming in Task 16.")
```

`src/prompt_quality_lab/ab_eval/results_view.py`:

```python
import streamlit as st


def render_results() -> None:
    st.write("Results — coming in Task 17.")
```

- [ ] **Step 3: Smoke import**

```powershell
uv run python -c "from prompt_quality_lab.ab_eval.page import render; from prompt_quality_lab.ab_eval.setup_view import render_setup; from prompt_quality_lab.ab_eval.progress_view import render_progress; from prompt_quality_lab.ab_eval.results_view import render_results; print('all imports ok')"
```

Expected: `all imports ok`.

- [ ] **Step 4: Commit**

```bash
git add pages/2_AB_Eval.py src/prompt_quality_lab/ab_eval/
git commit -m "feat(ab_eval): scaffold page + mode dispatch + stub views"
```

---

### Task 14: `ab_eval/cost.py` — per-call price constants + estimate

**Files:**
- Create: `prompt_quality_lab/src/prompt_quality_lab/ab_eval/cost.py`
- Create: `prompt_quality_lab/tests/test_ab_eval_cost.py`

- [ ] **Step 1: Write the failing test**

`prompt_quality_lab/tests/test_ab_eval_cost.py`:

```python
from __future__ import annotations

import pytest

from prompt_quality_lab.ab_eval.cost import (
    PRICE_PER_CALL_USD,
    estimate_ab_run_cost,
)


def test_all_prices_are_positive() -> None:
    for model, price in PRICE_PER_CALL_USD.items():
        assert price > 0, f"{model} has non-positive price {price}"


def test_estimate_zero_records() -> None:
    assert estimate_ab_run_cost(0, "gemini-2.5-pro", "claude-opus-4-7") == 0.0


def test_estimate_one_record_two_sources() -> None:
    # 1 record × 2 sources × (1 gen + 1 judge) = 2 gens + 2 judges
    # gemini-2.5-pro: 0.05; claude-opus-4-7: 0.06 (from PRICE_PER_CALL_USD)
    expected = 2 * PRICE_PER_CALL_USD["gemini-2.5-pro"] + 2 * PRICE_PER_CALL_USD["claude-opus-4-7"]
    assert estimate_ab_run_cost(1, "gemini-2.5-pro", "claude-opus-4-7") == pytest.approx(expected)


def test_estimate_scales_linearly() -> None:
    one = estimate_ab_run_cost(1, "gemini-2.5-pro", "claude-opus-4-7")
    ten = estimate_ab_run_cost(10, "gemini-2.5-pro", "claude-opus-4-7")
    assert ten == pytest.approx(one * 10)


def test_estimate_unknown_model_raises() -> None:
    with pytest.raises(KeyError):
        estimate_ab_run_cost(1, "unknown-model", "claude-opus-4-7")
```

- [ ] **Step 2: Run — expect failure**

```powershell
uv run pytest tests/test_ab_eval_cost.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `cost.py`**

`src/prompt_quality_lab/ab_eval/cost.py`:

```python
"""Per-call cost estimates for the A/B harness.

Numbers are approximate as of 2026-05; refresh when Anthropic/Google
pricing changes. Used only for upfront cost estimation in the Setup view —
not for actual billing or post-run accounting.
"""
from __future__ import annotations


PRICE_PER_CALL_USD: dict[str, float] = {
    # Generator (Gemini)
    "gemini-2.5-pro": 0.05,
    "gemini-2.5-flash": 0.01,
    # Judge (Anthropic)
    "claude-opus-4-7": 0.06,
    "claude-sonnet-4-6": 0.02,
    "claude-haiku-4-5-20251001": 0.005,
}


def estimate_ab_run_cost(
    record_count: int,
    generator_model: str,
    judge_model: str,
) -> float:
    """Estimate total USD cost for an A/B run.

    Formula: record_count × 2 sources × (price_per_gen + price_per_judge).
    Raises KeyError if either model isn't in PRICE_PER_CALL_USD.
    """
    gen_price = PRICE_PER_CALL_USD[generator_model]
    judge_price = PRICE_PER_CALL_USD[judge_model]
    return record_count * 2 * (gen_price + judge_price)
```

- [ ] **Step 4: Run — expect pass**

```powershell
uv run pytest tests/test_ab_eval_cost.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/prompt_quality_lab/ab_eval/cost.py tests/test_ab_eval_cost.py
git commit -m "feat(ab_eval): per-call cost constants + linear estimate"
```

---

### Task 15: `ab_eval/setup_view.py` — sources, records, launch

**Files:**
- Modify: `prompt_quality_lab/src/prompt_quality_lab/ab_eval/setup_view.py`

Streamlit-heavy. Manual smoke testing in Task 18. Logic kept thin; relies on `eval.run_ab` for the actual work.

- [ ] **Step 1: Replace the stub with the real view**

`src/prompt_quality_lab/ab_eval/setup_view.py`:

```python
"""Setup mode — configure source A, source B, pick records, launch the run."""
from __future__ import annotations

import os
import random
import threading
from pathlib import Path

import streamlit as st

from credit_datasets import load_records
from prompt_quality_lab.ab_eval.cost import (
    PRICE_PER_CALL_USD,
    estimate_ab_run_cost,
)
from prompt_quality_lab.eval import PromptSource, run_ab


_COST_CONFIRM_THRESHOLD_USD = 5.0


def _credit_paper_current_dir() -> Path:
    """Resolve credit_paper/prompts/current/ via the installed credit_paper package."""
    import credit_paper.prompts.prompt_manager as pm
    return pm._DEFAULT_PROMPTS_DIR


def _credit_paper_history_dir() -> Path:
    return _credit_paper_current_dir().parent / "history"


def _list_history_snapshots() -> list[Path]:
    hd = _credit_paper_history_dir()
    if not hd.exists():
        return []
    return sorted(
        [p for p in hd.iterdir() if p.is_dir()],
        reverse=True,  # newest first
    )


def _resolve_source_dir(kind: str, history_pick: str | None, custom_path: str | None) -> Path | None:
    if kind == "current":
        return _credit_paper_current_dir()
    if kind == "history":
        if not history_pick:
            return None
        return _credit_paper_history_dir() / history_pick
    if kind == "custom":
        if not custom_path:
            return None
        p = Path(custom_path)
        return p if p.is_dir() else None
    return None


def _render_source_picker(label: str, state_prefix: str) -> PromptSource | None:
    st.markdown(f"### {label}")
    name = st.text_input(
        "Label (shown in results)",
        value="current" if state_prefix == "a" else "draft",
        key=f"{state_prefix}_name",
    )
    kind = st.radio(
        "Where do the prompts come from?",
        options=["current", "history", "custom"],
        horizontal=True,
        key=f"{state_prefix}_kind",
        format_func=lambda k: {"current": "credit_paper/prompts/current", "history": "history snapshot", "custom": "custom directory"}[k],
    )
    history_pick = None
    custom_path = None
    if kind == "history":
        snapshots = _list_history_snapshots()
        if not snapshots:
            st.warning("No history snapshots in credit_paper/prompts/history/")
        else:
            history_pick = st.selectbox(
                "Snapshot",
                options=[s.name for s in snapshots],
                key=f"{state_prefix}_history",
            )
    elif kind == "custom":
        custom_path = st.text_input(
            "Absolute path to a directory containing the 4 YAML files",
            key=f"{state_prefix}_custom",
        )

    resolved = _resolve_source_dir(kind, history_pick, custom_path)
    if resolved is None:
        return None
    return PromptSource(name=name, prompts_dir=resolved)


def _kick_off_run(
    source_a: PromptSource,
    source_b: PromptSource,
    record_ids: list[str],
    notes: str,
    judge_model: str,
) -> None:
    """Launch run_ab in a background thread. Store handle in session state."""
    st.session_state["abeval_cancel_flag"] = False
    st.session_state["abeval_progress"] = (0, len(record_ids), "starting...")
    st.session_state["abeval_run"] = None
    st.session_state["abeval_running"] = True

    def _on_progress(current: int, total: int, msg: str) -> None:
        st.session_state["abeval_progress"] = (current, total, msg)

    def _cancel_check() -> bool:
        return bool(st.session_state.get("abeval_cancel_flag", False))

    def _worker() -> None:
        try:
            run = run_ab(
                source_a=source_a,
                source_b=source_b,
                record_ids=record_ids,
                notes=notes,
                judge_model=judge_model,
                progress_callback=_on_progress,
                cancel_check=_cancel_check,
            )
            st.session_state["abeval_run"] = run
        except Exception as e:
            st.session_state["abeval_run_error"] = str(e)
        finally:
            st.session_state["abeval_running"] = False

    t = threading.Thread(target=_worker, daemon=True)
    # Attach Streamlit script context so session_state writes work from the thread
    try:
        from streamlit.runtime.scriptrunner import add_script_run_ctx
        add_script_run_ctx(t)
    except ImportError:
        pass  # fall back to non-context-attached thread; writes may be lost
    t.start()


def render_setup() -> None:
    st.subheader("Configure A/B run")

    # Anthropic key guard
    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.error(
            "ANTHROPIC_API_KEY is not set in the environment. The judge cannot run "
            "without it. Add it to your .env or environment before launching a run."
        )

    # Records
    records = load_records()
    if not records:
        st.info("The golden dataset is empty. Add records via the Dataset Manager first.")
        return

    col_a, col_b = st.columns(2)
    with col_a:
        source_a = _render_source_picker("Source A", "a")
    with col_b:
        source_b = _render_source_picker("Source B", "b")

    st.markdown("### Records to evaluate")
    record_options = {r.id: f"{r.id} — {r.company_name}" for r in records}
    selected = st.multiselect(
        "Pick records",
        options=list(record_options.keys()),
        format_func=lambda i: record_options[i],
        key="abeval_records",
    )
    col_sel1, col_sel2, col_sel3 = st.columns(3)
    with col_sel1:
        if st.button("Select all"):
            st.session_state["abeval_records"] = list(record_options.keys())
            st.rerun()
    with col_sel2:
        if st.button("Random 10"):
            ids = list(record_options.keys())
            random.shuffle(ids)
            st.session_state["abeval_records"] = ids[:10]
            st.rerun()
    with col_sel3:
        if st.button("Clear"):
            st.session_state["abeval_records"] = []
            st.rerun()

    st.markdown("### Run options")
    notes = st.text_area(
        "Notes (what is this run testing?)",
        placeholder="e.g. tighter conclusion wording",
        key="abeval_notes",
    )
    judge_model = st.selectbox(
        "Judge model",
        options=[m for m in PRICE_PER_CALL_USD if m.startswith("claude-")],
        index=0,
        key="abeval_judge_model",
    )

    # Cost estimate (assume generator is gemini-2.5-pro — the credit_paper default)
    generator_model = "gemini-2.5-pro"
    cost = estimate_ab_run_cost(len(selected), generator_model, judge_model)
    st.caption(f"Estimated cost: **${cost:.2f}** (≈{len(selected)} records × 2 sources × gen+judge)")

    cost_confirm = True
    if cost > _COST_CONFIRM_THRESHOLD_USD:
        cost_confirm = st.checkbox(
            f"I understand this will cost approximately **${cost:.2f}**",
            key="abeval_cost_confirm",
        )

    can_run = (
        source_a is not None
        and source_b is not None
        and len(selected) >= 1
        and cost_confirm
        and not st.session_state.get("abeval_running", False)
        and bool(os.environ.get("ANTHROPIC_API_KEY"))
    )

    if st.button("Run A/B", type="primary", disabled=not can_run):
        _kick_off_run(source_a, source_b, selected, notes, judge_model)
        # Switch to Progress mode
        st.session_state["abeval_mode"] = "Progress"
        st.rerun()
```

- [ ] **Step 2: Smoke import**

```powershell
uv run python -c "from prompt_quality_lab.ab_eval.setup_view import render_setup; print(callable(render_setup))"
```

Expected: `True`.

- [ ] **Step 3: Commit**

```bash
git add src/prompt_quality_lab/ab_eval/setup_view.py
git commit -m "feat(ab_eval): setup view — source pickers, records, cost guard"
```

---

### Task 16: `ab_eval/progress_view.py` — live progress + cancel

**Files:**
- Modify: `prompt_quality_lab/src/prompt_quality_lab/ab_eval/progress_view.py`

- [ ] **Step 1: Replace the stub**

`src/prompt_quality_lab/ab_eval/progress_view.py`:

```python
"""Progress mode — live progress bar + cancel button."""
from __future__ import annotations

import time

import streamlit as st


_POLL_SECONDS = 2.0


def render_progress() -> None:
    st.subheader("Run in progress")

    running = st.session_state.get("abeval_running", False)
    current, total, msg = st.session_state.get("abeval_progress", (0, 0, ""))

    if total == 0 and not running:
        st.info("No run in progress. Go to Setup to start one.")
        return

    pct = (current / total) if total > 0 else 0.0
    st.progress(pct, text=f"{current} / {total} records — {msg}")

    if "abeval_run_error" in st.session_state:
        st.error(f"Run errored: {st.session_state['abeval_run_error']}")
        if st.button("Dismiss"):
            del st.session_state["abeval_run_error"]
            st.session_state["abeval_mode"] = "Setup"
            st.rerun()
        return

    if running:
        if st.button("Cancel run", type="secondary"):
            st.session_state["abeval_cancel_flag"] = True
            st.info("Cancellation requested — will stop after the current record.")
        # Cooperative poll: wait a beat, then re-run the page so the bar updates
        time.sleep(_POLL_SECONDS)
        st.rerun()
    else:
        # Just finished
        run = st.session_state.get("abeval_run")
        if run is not None:
            status = run.status
            if status == "complete":
                st.success(f"Run complete: {run.run_id}")
            elif status == "cancelled":
                st.warning(f"Run cancelled: {run.run_id}")
            elif status == "error":
                st.error(f"Run errored: {run.run_id}")
            if st.button("View results"):
                st.session_state["abeval_selected_run_id"] = run.run_id
                st.session_state["abeval_mode"] = "Results"
                st.rerun()
```

Note: the `time.sleep(_POLL_SECONDS) + st.rerun()` pattern is a deliberate trade-off. Streamlit doesn't have first-class progress observability across threads; polling-on-rerun is the simplest pattern that works without depending on experimental APIs. The UI may stutter slightly during long runs — acceptable for v1.

- [ ] **Step 2: Smoke import**

```powershell
uv run python -c "from prompt_quality_lab.ab_eval.progress_view import render_progress; print(callable(render_progress))"
```

Expected: `True`.

- [ ] **Step 3: Commit**

```bash
git add src/prompt_quality_lab/ab_eval/progress_view.py
git commit -m "feat(ab_eval): progress view with poll-on-rerun + cancel"
```

---

### Task 17: `ab_eval/results_view.py` — past runs + drill-down + CSV export

**Files:**
- Modify: `prompt_quality_lab/src/prompt_quality_lab/ab_eval/results_view.py`

- [ ] **Step 1: Replace the stub**

`src/prompt_quality_lab/ab_eval/results_view.py`:

```python
"""Results mode — browse past runs + side-by-side drill-down."""
from __future__ import annotations

import csv
import io

import pandas as pd
import streamlit as st

from prompt_quality_lab.eval import list_runs, load_run


def _flatten_for_csv(run) -> list[dict]:
    """One row per (record × source) with score columns."""
    rows: list[dict] = []
    for label, scores in (("A", run.scores_a), ("B", run.scores_b)):
        for s in scores:
            row = {
                "run_id": run.run_id,
                "record_id": s.record_id,
                "source": label,
                "source_name": s.prompt_source_name,
                "overall_score": s.overall_score,
                "rationale": s.rationale,
                "error": s.error or "",
            }
            row.update(s.dimension_scores)
            rows.append(row)
    return rows


def render_results() -> None:
    st.subheader("Past A/B runs")
    entries = list_runs()
    if not entries:
        st.info("No runs yet. Go to Setup to launch one.")
        return

    label_for = {
        e["run_id"]: f"{e['started_at']} — {e['source_a']} vs {e['source_b']} — {e['record_count']} records — {e['status']}"
        for e in entries
    }
    preselect = st.session_state.get("abeval_selected_run_id")
    options = list(label_for.keys())
    default_idx = options.index(preselect) if preselect in options else 0
    selected_id = st.selectbox(
        "Select run",
        options=options,
        index=default_idx,
        format_func=lambda i: label_for[i],
        key="abeval_results_selected",
    )

    run = load_run(selected_id)

    st.markdown(f"### Summary: {run.source_a.name} vs {run.source_b.name}")
    if run.aggregate_a and run.aggregate_b:
        dims = sorted(set(run.aggregate_a) | set(run.aggregate_b))
        summary_rows = []
        for d in dims:
            a = run.aggregate_a.get(d, 0.0)
            b = run.aggregate_b.get(d, 0.0)
            summary_rows.append({"dimension": d, run.source_a.name: a, run.source_b.name: b, "delta": b - a})
        # Overall row
        overall_a = sum(s.overall_score for s in run.scores_a if s.error is None) / max(
            1, sum(1 for s in run.scores_a if s.error is None)
        )
        overall_b = sum(s.overall_score for s in run.scores_b if s.error is None) / max(
            1, sum(1 for s in run.scores_b if s.error is None)
        )
        summary_rows.append(
            {"dimension": "OVERALL", run.source_a.name: overall_a, run.source_b.name: overall_b, "delta": overall_b - overall_a}
        )
        st.dataframe(pd.DataFrame(summary_rows), hide_index=True, width="stretch")
    else:
        st.info("Run has no successful scores yet.")

    st.markdown(f"Notes: _{run.notes or 'none'}_")

    # CSV export
    rows = _flatten_for_csv(run)
    if rows:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        st.download_button(
            "Export to CSV",
            data=buf.getvalue(),
            file_name=f"{run.run_id}.csv",
            mime="text/csv",
        )

    # Per-record drill-down
    st.markdown("### Per-record drill-down")
    scores_by_id_a = {s.record_id: s for s in run.scores_a}
    scores_by_id_b = {s.record_id: s for s in run.scores_b}
    for rid in run.record_ids:
        sa = scores_by_id_a.get(rid)
        sb = scores_by_id_b.get(rid)
        with st.expander(
            f"{rid} — A: {sa.overall_score:.2f} | B: {sb.overall_score:.2f}"
            if sa and sb and sa.error is None and sb.error is None
            else f"{rid} — error or partial"
        ):
            cols = st.columns(2)
            with cols[0]:
                st.markdown(f"**{run.source_a.name}**")
                if sa is None:
                    st.warning("no score recorded")
                elif sa.error:
                    st.error(f"error: {sa.error}")
                else:
                    st.markdown(f"Overall: **{sa.overall_score:.2f}**")
                    st.caption(sa.rationale)
                    st.code(sa.generated_output[:2000] + ("..." if len(sa.generated_output) > 2000 else ""), language="html")
            with cols[1]:
                st.markdown(f"**{run.source_b.name}**")
                if sb is None:
                    st.warning("no score recorded")
                elif sb.error:
                    st.error(f"error: {sb.error}")
                else:
                    st.markdown(f"Overall: **{sb.overall_score:.2f}**")
                    st.caption(sb.rationale)
                    st.code(sb.generated_output[:2000] + ("..." if len(sb.generated_output) > 2000 else ""), language="html")
```

- [ ] **Step 2: Smoke import**

```powershell
uv run python -c "from prompt_quality_lab.ab_eval.results_view import render_results; print(callable(render_results))"
```

Expected: `True`.

- [ ] **Step 3: Commit**

```bash
git add src/prompt_quality_lab/ab_eval/results_view.py
git commit -m "feat(ab_eval): results view — summary, drill-down, CSV export"
```

---

### Task 18: Programmatic end-to-end smoke

**Files:** none (verification only)

- [ ] **Step 1: Run all eval + ab_eval tests in `prompt_quality_lab`**

```powershell
cd "C:\Users\APR\OneDrive - Anchor Point Risk (Pty) Ltd\Desktop\VS_CODE_REPOSITORY\prompt_quality_lab"
$env:UV_LINK_MODE = "copy"
uv run pytest tests/ -v --ignore=tests/test_loaders.py
```

Expected:
- `test_eval_schema.py` — 7 passed
- `test_eval_rubric.py` — 6 passed
- `test_eval_runner.py` — 5 passed
- `test_eval_judge.py` — 5 passed
- `test_eval_store.py` — 6 passed
- `test_eval_ab.py` — 4 passed
- `test_eval_public_api.py` — 1 passed
- `test_ab_eval_cost.py` — 5 passed
- `test_credit_paper_integration.py` — 2 passed
- `test_list_view_filters.py` (from sub-project 1) — 5 passed
- **Total: 46 passed**

If any fail, fix root cause; don't proceed to Step 2 until clean.

- [ ] **Step 2: Programmatic A/B run with stubbed clients**

```powershell
uv run python -c "
import os, tempfile, json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

# Temp roots
tmp = Path(tempfile.mkdtemp(prefix='abeval_smoke_'))
os.environ['CREDIT_DATASETS_ROOT'] = str(tmp / 'dataset')
os.environ['PROMPT_QUALITY_LAB_EVAL_RUNS_ROOT'] = str(tmp / 'eval_runs')
os.environ['ANTHROPIC_API_KEY'] = 'fake-key-for-smoke'

from credit_datasets import Record, AssetClass, QualityGrade, Source, add_record, dataset_root
from prompt_quality_lab.eval import PromptSource, run_ab, list_runs, load_run

# Seed 2 records
src = tmp / 'src'
src.mkdir()
(src / 'in.pdf').write_bytes(b'in')
(src / 'gold.pdf').write_bytes(b'gold')
for i in (1, 2):
    add_record(
        Record(id=f'{i:03d}', company_name=f'Co{i}',
               asset_class=AssetClass.CORPORATE, sector='manufacturing',
               afs_years=[2023], date_added=date.today(), reviewer='smoke',
               quality_grade=QualityGrade.SILVER, source=Source.ANALYST_ORIGINAL),
        [src / 'in.pdf'], src / 'gold.pdf',
    )

# Stub the two LLM seams
with patch('prompt_quality_lab.eval.ab.generate') as fake_gen, \
     patch('prompt_quality_lab.eval.ab.score') as fake_sc:
    fake_gen.side_effect = lambda src, rec, ds: (f'<html>{src.name}-{rec.id}</html>', 'gemini-2.5-pro', 0.1)
    def _score(html, gold, rubric, judge_model, **kw):
        base = 8.0 if 'draft' in html else 7.0
        scores = {d.name: base for d in rubric.dimensions}
        return scores, base, 'rationale'
    fake_sc.side_effect = _score

    run = run_ab(
        source_a=PromptSource('current', tmp / 'prompts_a'),
        source_b=PromptSource('draft', tmp / 'prompts_b'),
        record_ids=['001', '002'],
        notes='smoke',
    )

assert run.status == 'complete'
assert len(run.scores_a) == 2 and len(run.scores_b) == 2
assert run.aggregate_a['factual_accuracy'] == 7.0
assert run.aggregate_b['factual_accuracy'] == 8.0
print(f'run_id: {run.run_id}')
print(f'aggregate A: {run.aggregate_a}')
print(f'aggregate B: {run.aggregate_b}')

# Round-trip via list+load
entries = list_runs()
assert entries[0]['run_id'] == run.run_id
reloaded = load_run(run.run_id)
assert reloaded == run
print('list+load round-trip OK')

import shutil
shutil.rmtree(tmp)
print('SMOKE TEST PASSED')
"
```

Expected last line: `SMOKE TEST PASSED`.

- [ ] **Step 3: Confirm Streamlit app starts (no actual browser interaction)**

```powershell
uv run python -c "import streamlit_app; print('streamlit_app imports clean'); from prompt_quality_lab.ab_eval.page import render; print('ab_eval page imports clean')"
```

Expected: both 'clean' messages, no errors.

- [ ] **Step 4: No commit needed (verification only)**

If anything failed, fix and commit the fix. Otherwise just report results to the controller.

---

## Acceptance criteria recap (from spec §10)

- [ ] `prompt_quality_lab/src/prompt_quality_lab/eval/` exists with all six modules and unit tests covering schema, rubric, runner, judge, store, ab — all passing with mocked LLM clients.
- [ ] `credit_paper/pyproject.toml` exists; `credit_paper.core.report_generator` and `credit_paper.prompts.prompt_manager` are importable from `prompt_quality_lab`.
- [ ] `credit_paper/prompts/prompt_manager.py` honours `CREDIT_PAPER_PROMPTS_DIR` and behaves identically when the var is unset.
- [ ] `prompt_quality_lab/pages/2_AB_Eval.py` is auto-discovered by Streamlit and renders all three modes (Setup, Progress, Results) without errors against the existing gold dataset.
- [ ] `tests/test_credit_paper_integration.py` verifies the env-var override end-to-end.
- [ ] An operator can run a single-record A/B comparison end-to-end (Setup → Run → Progress shows progress → Results shows scores). Confirmed by interactive smoke (run after Task 18).
