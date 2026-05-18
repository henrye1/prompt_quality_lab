# A/B Eval Harness — Design

**Date:** 2026-05-17
**Status:** Approved (brainstorming complete)
**Author:** Henry + Claude (Opus 4.7)
**Related repos:** `prompt_quality_lab`, `credit_paper`, `credit_datasets`
**Sub-project:** #2 of 5 from the original brainstorming decomposition (foundation: golden dataset — already shipped).

## 1. Purpose

Build an A/B prompt-evaluation harness inside `prompt_quality_lab`. Two prompt sources × N gold records → side-by-side scored comparison.

The golden dataset (`credit_datasets`) was shipped in the prior spec. Without an eval harness, you have no way to use it for its core purpose — answering "is my prompt change actually better?" Every prompt iteration today is a guess. The harness closes that loop.

## 2. Scope

**This spec covers:**

1. A pure-Python `prompt_quality_lab.eval` module: runs `credit_paper`'s production Stage 3 with a chosen prompt source against gold records, scores each output with Claude-as-judge against a credit-specific rubric, persists the run.
2. A new Streamlit page "A/B Eval" in the existing multi-page `prompt_quality_lab` app, with three modes (Setup, Progress, Results).
3. JSONL storage for run artifacts in `prompt_quality_lab/data/eval_runs/`, with a small `index.json` for run discovery.
4. The minimal `credit_paper` changes required to make it importable as a package and let its prompt directory be overridden at runtime.

**This spec deliberately does NOT cover:**

- Prompt-improvement workflow (sub-project #4) — wiring `prompt_quality_lab`'s optimisers to generate candidate prompts, eval them, promote winners.
- Continuous monitoring / drift detection (sub-project #5).
- Multi-asset-class prompt refactor in `credit_paper` (sub-project #3).
- Human-override scoring UI on top of the LLM judge.
- Embedding-similarity scoring as a second signal.
- Caching of generated outputs across runs.
- Streaming generation to the UI.
- A "promote to current" PR-style approval flow.
- Multi-user or shared-run support.
- Token/dollar cost tracking beyond an upfront estimate.

## 3. Architecture

```
prompt_quality_lab/
├── src/prompt_quality_lab/
│   ├── eval/                       # pure Python library (testable)
│   │   ├── __init__.py
│   │   ├── schema.py
│   │   ├── runner.py
│   │   ├── judge.py
│   │   ├── rubric.py
│   │   ├── store.py
│   │   └── ab.py
│   └── ab_eval/                    # Streamlit UI over eval/
│       ├── __init__.py
│       ├── page.py
│       ├── setup_view.py
│       ├── progress_view.py
│       └── results_view.py
├── pages/
│   └── 2_AB_Eval.py                # new auto-discovered page shim
└── data/
    └── eval_runs/                  # gitignored; OneDrive-backed
        ├── index.json
        └── runs/
            └── run-2026-05-17-foo/
                ├── meta.json
                ├── scores_a.jsonl
                ├── scores_b.jsonl
                └── outputs/

credit_paper/
├── pyproject.toml                  # NEW — makes credit_paper installable
└── prompts/
    └── prompt_manager.py           # MODIFIED — env-var override of prompts dir
```

`eval/` is pure code that can be tested without Streamlit and without real LLM calls. `ab_eval/` is the thin Streamlit layer over it. This split mirrors how `credit_datasets` (logic) and `dataset_manager` (UI) are separated in the prior spec.

## 4. Data model

Three concepts. All JSON-serialisable. No database — JSONL files only.

### 4.1 `PromptSource`

Points at a set of YAML prompts. Lives in `eval/schema.py`.

```python
@dataclass(frozen=True)
class PromptSource:
    name: str                # human label, e.g. "current" or "history/2026-04-12T10:30"
    prompts_dir: Path        # absolute path to the directory containing the 4 YAML files
```

A `PromptSource` can refer to:

- `credit_paper/prompts/current/` — the live production version.
- `credit_paper/prompts/history/<timestamp>/` — a historical snapshot.
- Any user-supplied directory — e.g. a draft edit prepared off to the side.

### 4.2 `RecordScore`

One record evaluated against gold under one `PromptSource`.

```python
@dataclass(frozen=True)
class RecordScore:
    record_id: str                       # gold record id, e.g. "001"
    prompt_source_name: str
    generated_output: str                # raw HTML from Stage 3
    dimension_scores: dict[str, float]   # e.g. {"factual_accuracy": 7.5, ...}
    overall_score: float                 # weighted average, 0-10
    rationale: str                       # judge's free-text justification
    generator_model: str                 # e.g. "gemini-2.5-pro"
    judge_model: str                     # e.g. "claude-opus-4-7"
    duration_seconds: float
    error: str | None                    # populated if generation or judging failed
```

### 4.3 `Run`

One A/B experiment: two `PromptSource`s × N gold records.

```python
@dataclass(frozen=True)
class Run:
    run_id: str                          # "run-{YYYY-MM-DD}-{short-slug}"
    started_at: datetime
    finished_at: datetime | None
    record_ids: list[str]
    source_a: PromptSource
    source_b: PromptSource
    scores_a: list[RecordScore]
    scores_b: list[RecordScore]
    aggregate_a: dict[str, float]        # mean dimension scores across records
    aggregate_b: dict[str, float]
    notes: str
    status: str                          # "running" | "complete" | "cancelled" | "error"
```

### 4.4 Storage layout

```
prompt_quality_lab/data/eval_runs/
├── index.json                          # array of {run_id, started_at, source_a.name, source_b.name, notes, status}
└── runs/
    └── run-2026-05-17-tighter-conclusions/
        ├── meta.json                   # Run dataclass minus the scores arrays
        ├── scores_a.jsonl              # one RecordScore per line
        ├── scores_b.jsonl
        └── outputs/                    # raw HTML for inspection
            ├── 001_a.html
            ├── 001_b.html
            └── ...
```

`data/eval_runs/` is gitignored; OneDrive handles backup, mirroring how `credit_datasets/data/` works.

## 5. The `eval` Python module

Six modules, each with one responsibility. All purely callable from Python; no Streamlit imports allowed.

### 5.1 `schema.py`

`PromptSource`, `RecordScore`, `Run`, plus the `Dimension` and `Rubric` types used in §5.4. Frozen dataclasses, JSON encoders for `Path` and `datetime`.

### 5.2 `runner.py` — invoke credit_paper Stage 3

```python
class GenerationError(Exception):
    pass


def generate(
    source: PromptSource,
    record: Record,                     # from credit_datasets
    dataset_root: Path,
) -> tuple[str, str, float]:
    """Run credit_paper Stage 3 with `source`'s prompts against `record`'s inputs.

    Returns: (generated_html, model_id, duration_seconds).
    Raises GenerationError on Gemini/parsing failure.
    """
```

Implementation:

1. Resolve the record's input bundle (`record.input_files(dataset_root)`) and gold output (for verification only — not passed to Stage 3).
2. Enter a `with_prompts_dir(source.prompts_dir)` context manager that sets `CREDIT_PAPER_PROMPTS_DIR` to `source.prompts_dir` and restores the prior value on exit.
3. Inside the context, import `credit_paper.core.report_generator` and call its top-level entrypoint. The entrypoint is the same function the Quick Assessment / Run Assessment pages already call in production.
4. Capture the HTML, the model id from Gemini's response, and `time.perf_counter()` delta.
5. Wrap any exception in `GenerationError`, preserving the cause via `raise ... from`.

The context manager pattern keeps the production prompt directory untouched. Concurrent calls from different threads/processes would race on the env var; `parallelism` in `ab.run_ab` defaults to 1 for this reason.

### 5.3 `rubric.py` — the credit-specific rubric

```python
@dataclass(frozen=True)
class Dimension:
    name: str
    weight: float                       # 0..1
    description: str                    # shown to the judge

@dataclass(frozen=True)
class Rubric:
    dimensions: list[Dimension]
    judge_prompt_template: str          # has {gold_text}, {generated_text}, {dimensions_json} placeholders


CREDIT_RUBRIC = Rubric(
    dimensions=[
        Dimension("factual_accuracy", 0.30,
            "Numbers, dates, names, and claims match the gold report and the underlying AFS."),
        Dimension("completeness", 0.20,
            "All sections the gold report covers are present and at a comparable depth."),
        Dimension("depth_of_analysis", 0.20,
            "Conclusions are supported by ratio analysis and observations, not just restated."),
        Dimension("citation_correctness", 0.15,
            "Quoted figures correctly attribute their source (AFS year, page, table)."),
        Dimension("tone_and_style", 0.10,
            "Matches BDO/SARB formal tone; no marketing language, no first-person voice."),
        Dimension("absence_of_hallucination", 0.05,
            "No invented entities, dates, or figures absent from the inputs."),
    ],
    judge_prompt_template="""You are an expert credit-risk reviewer scoring a generated credit paper against a gold-standard analyst report.

You will be given:
1. The gold analyst report (as a PDF document).
2. A candidate generated credit paper (as HTML text).

Score the candidate on each of the following dimensions on a 0-10 scale, where 0 is unusable and 10 is indistinguishable from the gold:

{dimensions_json}

Return ONLY a JSON object with this shape:
{{
  "scores": {{ "<dimension_name>": <float 0-10>, ... }},
  "rationale": "<2-4 sentences explaining the scores, calling out the largest gap from gold>"
}}

The candidate HTML:
<candidate>
{generated_text}
</candidate>

Score now.""",
)
```

`{gold_text}` is NOT a string substitution — the gold PDF is attached as a separate Anthropic message content block (see §5.4 implementation). The template substitutes only `{dimensions_json}` and `{generated_text}`.

Dimensions are drawn from `credit_paper`'s existing `prompts/current/audit_criteria.yaml` so the categories match what the operator already reviews manually during Stage 4 audits. Weights sum to 1.0.

The rubric is a code constant, not a YAML file. Changes to it should be deliberate code changes that go through review and a re-run of every saved A/B comparison.

### 5.4 `judge.py` — Claude scoring call

```python
class JudgeError(Exception):
    pass


def score(
    generated_html: str,
    gold_file: Path,                    # the analyst's gold PDF
    rubric: Rubric,
    judge_model: str = "claude-opus-4-7",
    *,
    anthropic_client: Anthropic | None = None,
) -> tuple[dict[str, float], float, str]:
    """Return (per-dimension scores, weighted overall, rationale)."""
```

Implementation:

1. Read the gold PDF as bytes.
2. Build the Anthropic message with two content blocks: a `document` block with base64-encoded gold PDF (`media_type: application/pdf`), followed by a `text` block with the rendered template from `rubric.judge_prompt_template`. The template substitutes only `{dimensions_json}` (JSON-encoded list of `{name, description}` for each dimension) and `{generated_text}` (the candidate HTML). The gold PDF is referenced implicitly as "the gold analyst report" in the template body.
3. Use Anthropic tool-use to force structured JSON output: define a single tool `record_scores` whose input schema mirrors `{"scores": {dim_name: number}, "rationale": str}`, and set `tool_choice={"type": "tool", "name": "record_scores"}`.
4. Parse the tool-use response. Compute `overall_score = sum(scores[d.name] * d.weight for d in rubric.dimensions)`.
5. Wrap parse / API errors in `JudgeError` with the cause attached.

`anthropic_client` is an injectable dependency. Tests pass a `MagicMock` configured to return a canned JSON response. Production callers omit it and the function constructs a default client from the `ANTHROPIC_API_KEY` env var.

### 5.5 `store.py` — JSONL persistence

```python
def save_run(run: Run, root: Path | None = None) -> None
def load_run(run_id: str, root: Path | None = None) -> Run
def list_runs(root: Path | None = None) -> list[dict]   # the index entries, newest first
def get_index(root: Path | None = None) -> Path         # the index.json path
```

`save_run` writes `meta.json`, `scores_a.jsonl`, `scores_b.jsonl`, and the `outputs/` HTML files; then appends/updates the entry in `index.json`. Atomicity: write into a temp folder beside `runs/` first, then `os.replace()` the folder name. If a `Run` is partial (`status="running"` or `"cancelled"`), `save_run` is still safe to call — `scores_a.jsonl` and `scores_b.jsonl` may have fewer lines than `record_ids`.

`root` defaults to `prompt_quality_lab/data/eval_runs/`, resolved at module import time. Override via `$PROMPT_QUALITY_LAB_EVAL_RUNS_ROOT` for tests.

### 5.6 `ab.py` — orchestrator

```python
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
    root: Path | None = None,
) -> Run:
```

Algorithm:

1. Build the `Run` skeleton with `status="running"`, `scores_a=[]`, `scores_b=[]`, `started_at=now`. Save via `store.save_run` immediately so partial state is recoverable.
2. For each record id:
   - Load the `Record` via `credit_datasets.get_record(record_id)`.
   - Generate with source A → `RecordScore`. Append to `scores_a`. Save partial state.
   - Generate with source B → `RecordScore`. Append to `scores_b`. Save partial state.
   - Score both. Update both `RecordScore`s. Save partial state.
   - Invoke `progress_callback(current=i+1, total=len(record_ids), message=...)`.
   - Check `cancel_check()` between records (not within). If `True`, mark `status="cancelled"`, set `finished_at=now`, save, return.
3. On loop completion: compute `aggregate_a` and `aggregate_b` (per-dimension means over successful `RecordScore`s; errored records skipped). Mark `status="complete"`, set `finished_at=now`, save, return.

Failures in `generate` or `score` for a single record are captured in `RecordScore.error` and the loop continues. A run is `status="error"` only if every record errored.

### 5.7 `__init__.py` — public exports

```python
from prompt_quality_lab.eval.schema import (
    Dimension,
    PromptSource,
    Record,        # re-export from credit_datasets for convenience
    RecordScore,
    Rubric,
    Run,
)
from prompt_quality_lab.eval.ab import run_ab
from prompt_quality_lab.eval.judge import JudgeError, score
from prompt_quality_lab.eval.rubric import CREDIT_RUBRIC
from prompt_quality_lab.eval.runner import GenerationError, generate
from prompt_quality_lab.eval.store import get_index, list_runs, load_run, save_run
```

### 5.8 Tests

Pure logic. No Streamlit, no real LLM calls. File I/O constrained to `tmp_path`.

- `test_schema.py` — JSON round-trip for `PromptSource`, `RecordScore`, `Run`.
- `test_rubric.py` — weights sum to 1.0, all dimensions have a description, `judge_prompt_template` includes all required placeholders.
- `test_judge.py` — uses an injected mock `Anthropic` client returning canned JSON; verifies score parsing, weighted overall calculation, malformed-response handling (raises `JudgeError`).
- `test_runner.py` — uses a stub `credit_paper.core.report_generator` (`monkeypatch.setattr`); verifies `with_prompts_dir` correctly sets/unsets the env var even on exception.
- `test_store.py` — round-trip of a `Run` with N records through `save_run` / `load_run`. Verifies atomicity (no half-written `index.json` on a simulated mid-write crash).
- `test_ab.py` — uses stubbed `generate` and `score` (returning deterministic outputs); verifies the loop produces correct aggregates, that errors in single records don't crash the run, and that `cancel_check` returning `True` halts cleanly with `status="cancelled"`.

## 6. The Streamlit page

### 6.1 Auto-discovered page shim

`prompt_quality_lab/pages/2_AB_Eval.py`:

```python
from prompt_quality_lab.ab_eval.page import render

render()
```

### 6.2 Module layout

```
src/prompt_quality_lab/ab_eval/
├── __init__.py
├── page.py           # render() — set_page_config, title, mode dispatch
├── setup_view.py     # configure source A, source B, pick records, launch
├── progress_view.py  # live progress during a run
└── results_view.py   # browse past runs + drill-down
```

Pattern mirrors `dataset_manager/` in the prior spec.

### 6.3 Mode dispatch

`page.py` renders the page title, then a top-level `st.radio` with `["Setup", "Progress", "Results"]`. Defaults to Setup. A run in progress auto-switches the radio to Progress (via `st.session_state`).

### 6.4 Setup mode

Three top-level expanders, each rendering one piece of state:

**Prompt source A**

- Radio: `current` / `history snapshot` / `custom directory`
- If history: `st.selectbox` of timestamps discovered from `credit_paper/prompts/history/`
- If custom: `st.text_input` for an absolute directory path; validates that all 4 expected YAML files exist when the user tabs out.

**Prompt source B** — same widgets, separate session-state keys.

**Records to evaluate** — multiselect of gold record ids (`load_records()` from credit_datasets, formatted as `"001 — Acme Pty Ltd"`). Shortcut buttons: `Select all`, `Random sample of 10`, `Random sample of 20`.

Below the expanders:

- "Notes" — `st.text_area` describing what's being tested.
- "Judge model" — `st.selectbox` (`claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`). Default `claude-opus-4-7`.
- "Parallelism" — `st.number_input` (1-3). Default 1.
- "Estimated cost" — text rendered from `(records × 2 generate + records × 2 judge) × per-call estimate`. Per-call estimates baked in as constants in `ab_eval/cost.py`. Refreshes whenever records or models change.
- If estimated cost > $5: a "I understand this will cost ~$N" confirm checkbox is required to enable the Run button.
- "Run A/B" button — disabled until both sources resolve to valid directories, at least 1 record is selected, and the cost confirm (if shown) is ticked.

On click: writes a `Run` skeleton to session state, switches to Progress mode, launches `eval.ab.run_ab` in a background `threading.Thread`. The thread writes intermediate state to a `Queue` (not `st.session_state` directly — Streamlit's session state is not thread-safe). The Progress mode reads from the queue on each rerun.

**Threading risk acknowledged:** Streamlit's threading model is fragile. The alternative implementation strategies, in order of preference, are:
1. Use `add_script_run_ctx` from `streamlit.runtime.scripts` to attach the worker thread to the current script context (officially supported as of Streamlit 1.27+).
2. Fall back to running synchronously inside the Streamlit script with periodic `st.empty().rerun()` between records — the page becomes unresponsive during generation but the implementation is bulletproof.
3. Use `streamlit_extras` or `streamlit-async` if neither above works.

The plan should try option 1 first and downgrade to option 2 if it doesn't behave. Either option is acceptable for v1 — the harness is operator-driven and a brief UI freeze is tolerable for a long-running A/B.

### 6.5 Progress mode

- Progress bar `st.progress(current/total)`.
- Status line `Generating source B for record 007 of 80…`.
- Below: a log of completed records (id, source A overall, source B overall, error if any).
- "Cancel" button. Sets `st.session_state["ab_cancel"] = True`. The `run_ab` `cancel_check` lambda reads this. The page polls (`st.rerun()` every 2s via `time.sleep` + `st.empty()`) until the worker thread reports `status != "running"`.

When the run finishes: shows a "View results" button that switches to Results mode and selects the just-finished run.

### 6.6 Results mode

- `st.selectbox` of past runs — `list_runs()`, newest first. Format: `2026-05-17 16:42 — current vs history/2026-04-12T10:30 — 20 records — Δ=+0.4`.
- Selected run renders three blocks:

**Summary table** (top):

| Dimension | Source A | Source B | Δ |
|---|---|---|---|
| factual_accuracy | 7.8 | 8.2 | +0.4 |
| completeness | 7.2 | 7.0 | -0.2 |
| ... | | | |
| **Overall** | **7.45** | **7.55** | **+0.10** |

**Per-record drill-down**:

`st.expander` per record. Inside: two columns (or stacked on narrow widths) showing rendered HTML of output A and B side-by-side. Below the columns: judge rationales for each source. Inline download button for the gold PDF.

**Export to CSV**: button that streams a flat table — one row per (record × source) with columns `record_id`, `company_name`, `source`, `factual_accuracy`, `completeness`, ..., `overall_score`, `error`. Filename `run-{run_id}.csv`. The operator opens this in Excel for ad-hoc analysis.

### 6.7 Page-level guards

- Empty-dataset guard: if `load_records()` returns `[]`, all modes show an info message linking back to the Dataset Manager. No silent crash.
- Missing API key guard: Setup mode checks `os.environ.get("ANTHROPIC_API_KEY")` and shows an error if absent.
- Out-of-date dependency guard: imports `credit_paper.core.report_generator` lazily inside `runner.generate`; surfacing the import error to Setup mode if it fails (e.g., credit_paper not installed as a dep yet).

## 7. Migration / wiring changes

### 7.1 `prompt_quality_lab/pyproject.toml`

Append `credit-paper` to dependencies and to `[tool.uv.sources]`:

```toml
dependencies = [
    ...,
    "credit-datasets",
    "credit-paper",
]

[tool.uv.sources]
credit-datasets = { path = "../credit_datasets", editable = true }
credit-paper = { path = "../credit_paper", editable = true }
```

### 7.2 `credit_paper/pyproject.toml` (NEW)

`credit_paper` currently has `requirements.txt` but no `pyproject.toml`. Add a minimal one:

```toml
[project]
name = "credit-paper"
version = "0.1.0"
description = "Credit Paper Assessment Agent"
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
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["core", "config", "prompts"]
```

This is a flat-layout package — no `src/` reshuffle. Imports become:

```python
from credit_paper.core.report_generator import generate_report
from credit_paper.prompts.prompt_manager import assemble_prompt_text
```

**Caveat — credit_paper needs a top-level `__init__.py`** at `credit_paper/__init__.py` so it's importable as a package (not just as a Streamlit project). The migration step creates this empty file. `core/`, `config/`, and `prompts/` already have `__init__.py` per the existing project layout.

Existing `credit_paper` Streamlit pages keep working because Streamlit launches from the project root; the `credit_paper.` package import path is purely additive.

### 7.3 `credit_paper/prompts/prompt_manager.py` — env-var override

Today it reads from a hardcoded relative path. Change:

```python
def _prompts_dir() -> Path:
    env = os.environ.get("CREDIT_PAPER_PROMPTS_DIR")
    return Path(env) if env else _DEFAULT_PROMPTS_DIR
```

Every existing `prompt_manager` function that previously read `_DEFAULT_PROMPTS_DIR` now calls `_prompts_dir()` instead. This is a strict superset of current behaviour — when the env var is unset, the function falls back to the existing path. Production credit_paper pages keep working unchanged.

The runner's context manager:

```python
@contextmanager
def with_prompts_dir(prompts_dir: Path):
    prev = os.environ.get("CREDIT_PAPER_PROMPTS_DIR")
    os.environ["CREDIT_PAPER_PROMPTS_DIR"] = str(prompts_dir)
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop("CREDIT_PAPER_PROMPTS_DIR", None)
        else:
            os.environ["CREDIT_PAPER_PROMPTS_DIR"] = prev
```

### 7.4 Integration smoke test

`prompt_quality_lab/tests/test_credit_paper_integration.py`:

- Verifies `credit_paper.core.report_generator` and `credit_paper.prompts.prompt_manager` import cleanly.
- Creates a `tmp_path` directory with stub YAML files matching the 4 expected names.
- Uses `with_prompts_dir(tmp_path)` and calls `prompt_manager.assemble_prompt_text("report_instructions")`, confirming it reads from the tempdir.
- No actual Gemini calls.

## 8. Cost guardrails

Per-call cost estimates baked into `ab_eval/cost.py` as a dict (USD, approximate, refresh as Anthropic/Google pricing changes):

```python
PRICE_PER_CALL_USD = {
    "gemini-2.5-pro": 0.05,          # generation per record
    "claude-opus-4-7": 0.06,         # judge per record
    "claude-sonnet-4-6": 0.02,
    "claude-haiku-4-5-20251001": 0.005,
}
```

Estimate formula: `len(records) × (PRICE_PER_CALL_USD[generator] + PRICE_PER_CALL_USD[judge]) × 2`. The `× 2` reflects two sources.

If estimated > $5, the cost-confirm checkbox is required to enable the Run button.

The estimate is shown verbatim in the run's `notes` field at start — so even if pricing changes later, the historical run records what was expected.

## 9. Out of scope (deferred)

- **Prompt-improvement workflow** (sub-project #4) — use harness to evaluate variants produced by `prompt_quality_lab`'s optimisers.
- **Continuous monitoring** (sub-project #5) — scheduled re-runs, drift, regression alerts.
- **Multi-asset-class prompt refactor in `credit_paper`** (sub-project #3) — uses harness for regression checks.
- **Human-override scoring** — Section 5.4 picks pure LLM-judge for v1.
- **Embedding-similarity second signal**.
- **Per-record caching** to skip re-runs when (record, prompts) is unchanged.
- **Streaming generation to the UI**.
- **PR-style "promote winning source" approval flow**.
- **Multi-user / shared state**.
- **Actual token-cost recording** (only an upfront estimate is shown today).

## 10. Acceptance criteria

This spec is delivered when:

1. `prompt_quality_lab/src/prompt_quality_lab/eval/` exists with all six modules and passing tests covering the cases in §5.8 — purely mock-driven, no live LLM calls.
2. `credit_paper/pyproject.toml` exists; `credit_paper.core.report_generator` and `credit_paper.prompts.prompt_manager` are importable from `prompt_quality_lab`.
3. `credit_paper/prompts/prompt_manager.py` honours `CREDIT_PAPER_PROMPTS_DIR` and behaves identically when the var is unset.
4. `prompt_quality_lab/pages/2_AB_Eval.py` is auto-discovered by Streamlit and renders all three modes (Setup, Progress, Results) without errors against the existing gold dataset.
5. A `tests/test_credit_paper_integration.py` smoke verifies the env-var override end-to-end.
6. The operator can run a single-record A/B comparison end-to-end (Setup → click Run → Progress shows ≥1 step → Results shows scores). Confirmed by an operator-driven smoke test, recorded in the operator-actions list.
