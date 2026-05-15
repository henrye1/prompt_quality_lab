# Prompt Quality Lab — Project Scaffold

**Date:** 2026-05-15
**Status:** Approved (brainstorming complete)
**Author:** Henry + Claude (Opus 4.7)

## 1. Purpose

Convert the existing single-file Streamlit app (`prompt_quality_lab.py`, 482 lines) into a structured, multi-module Python project that is comfortable to refine in VS Code. The application's behavior — four prompt-optimisation tabs powered by Anthropic Claude — must be preserved exactly. This is a restructure, not a feature change.

## 2. Goals

1. Split the monolith into small, focused modules with one clear purpose each.
2. Make pure logic (file loaders, DSPy-style bootstrap formatting) trivially unit-testable without an Anthropic API key.
3. Provide a one-command dev workflow via `uv`.
4. Provide VS Code workspace settings so F5 launches the Streamlit app under a debugger and formatter runs on save.
5. Keep secrets out of the repo via `.env`.

## 3. Non-goals

- No new optimisation strategies.
- No UI rework — same four tabs, same sidebar, same labels.
- No CI/CD, no Docker, no pre-commit hooks (can be added later).
- No git initialisation (user has opted to handle versioning themselves).
- No mypy / strict type checking (out of scope for the initial scaffold).

## 4. Target Layout

```
prompt_quality_lab/
├── .env.example              # ANTHROPIC_API_KEY=
├── .gitignore                # .venv, __pycache__, .env, .pytest_cache, .ruff_cache, dist/, build/
├── .python-version           # 3.11
├── .vscode/
│   ├── launch.json           # "Streamlit: Run app" debug config
│   ├── settings.json         # interpreter, ruff format-on-save, pytest config
│   └── extensions.json       # recommends ms-python.python + charliermarsh.ruff
├── pyproject.toml            # uv project metadata, runtime + dev deps, ruff + pytest config
├── README.md                 # quick start + dev workflow
├── streamlit_app.py          # 3-line entry: from prompt_quality_lab.app import main; main()
├── src/
│   └── prompt_quality_lab/
│       ├── __init__.py
│       ├── app.py                       # Streamlit UI: page setup, sidebar, tabs
│       ├── config.py                    # AVAILABLE_MODELS, DEFAULT_MODEL, dotenv load
│       ├── loaders.py                   # _coerce_row, load_prompts (pure, no API)
│       ├── anthropic_client.py          # call_claude, evaluate_against_expected
│       └── optimisers/
│           ├── __init__.py
│           ├── prompt_improver.py       # anthropic_prompt_improver
│           ├── dspy_bootstrap.py        # dspy_style_bootstrap (pure)
│           ├── variants.py              # generate_variants
│           └── langchain_template.py    # LangChain PromptTemplate runner
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_loaders.py
    ├── test_dspy_bootstrap.py
    └── test_anthropic_client.py
```

## 5. Module Responsibilities

| Module | Contents | Pure / Side-effects |
| --- | --- | --- |
| `config.py` | `AVAILABLE_MODELS`, `DEFAULT_MODEL`, `load_env()` (calls `dotenv.load_dotenv` once at import) | Side-effect on import (reads `.env`) |
| `loaders.py` | `_coerce_row`, `load_prompts` | Pure — operates on uploaded file objects, returns list[dict] |
| `anthropic_client.py` | `call_claude(client, prompt, ...)`, `evaluate_against_expected(client, prompt, expected, ...)` | Calls Anthropic API |
| `optimisers/prompt_improver.py` | `anthropic_prompt_improver(client, prompt, model)` | Calls Anthropic |
| `optimisers/dspy_bootstrap.py` | `dspy_style_bootstrap(target_prompt, examples)` | **Pure** — just string formatting |
| `optimisers/variants.py` | `generate_variants(client, prompt, n, model)` | Calls Anthropic |
| `optimisers/langchain_template.py` | Helper that builds a `PromptTemplate` and a `ChatAnthropic` runner; raises `ImportError` cleanly if langchain not installed | Calls Anthropic via LangChain |
| `app.py` | `main()` — `set_page_config`, sidebar, four tabs. Imports from the modules above. | Streamlit UI |

`anthropic_client.py` is the single seam for mocking the Anthropic SDK in tests.

## 6. Tooling

### 6.1 `pyproject.toml`

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

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

### 6.2 `.vscode/settings.json`

- `python.defaultInterpreterPath`: `.venv/Scripts/python.exe` (Windows)
- `[python] editor.defaultFormatter`: `charliermarsh.ruff`
- `editor.formatOnSave`: `true`
- `python.testing.pytestEnabled`: `true`
- `python.testing.pytestArgs`: `["tests"]`

### 6.3 `.vscode/launch.json`

One configuration:
- **"Streamlit: Run app"** — `module: streamlit`, `args: ["run", "streamlit_app.py"]`, `justMyCode: false` so breakpoints work into the package.

### 6.4 `.vscode/extensions.json`

Recommends `ms-python.python` and `charliermarsh.ruff`.

## 7. Environment Variables

`.env.example`:
```
ANTHROPIC_API_KEY=
```

`.env` is gitignored. `config.py` calls `dotenv.load_dotenv()` so the existing sidebar input (`os.environ.get("ANTHROPIC_API_KEY", "")`) picks it up automatically — no UI change required.

## 8. Tests

Three starter test files. None require an API key.

- **`test_loaders.py`** — feeds in-memory CSV / JSON / .txt content (wrapped in a minimal fake-uploaded-file class with `.name` and `.read()`), asserts `load_prompts` returns the right records and ignores malformed input.
- **`test_dspy_bootstrap.py`** — verifies `dspy_style_bootstrap` returns the target prompt unchanged when no labelled examples are supplied, and formats the few-shot block correctly when they are.
- **`test_anthropic_client.py`** — uses `unittest.mock.MagicMock` as the `Anthropic` client; asserts `call_claude` builds a `messages.create` call with the right model, messages, and system. For `evaluate_against_expected`, asserts the score parser handles `"7"`, `"7.5"`, `"7.5."`, and `"not a number"` cases.

These prove the test harness works; the user adds more as they refine the app.

## 9. Behavior Changes (Tracked Explicitly)

This restructure preserves all existing behavior **except**:

1. **Model ID update:** `claude-opus-4-6` → `claude-opus-4-7` in `AVAILABLE_MODELS`. (User-approved.) The other two IDs (`claude-sonnet-4-6`, `claude-haiku-4-5-20251001`) are already current.
2. **Default `.env` loading:** `config.py` calls `load_dotenv()` once on import so the API key sidebar field is pre-filled when `.env` exists. The existing fallback (manual paste in sidebar) still works.

Every other line of behavior is preserved verbatim.

## 10. Dev Workflow After Scaffold

```powershell
uv sync                                    # installs runtime + dev deps into .venv
uv run streamlit run streamlit_app.py      # run the app
uv run pytest                              # run tests
uv run ruff check .                        # lint
uv run ruff format .                       # format
```

Or in VS Code: open the folder, accept extension recommendations, hit F5 to launch with debugger attached.

## 11. Out of Scope (Future Work)

- Caching (`@st.cache_data` on Claude calls) to make iteration cheaper
- Session-state result persistence across reruns
- Concurrent API calls for variant comparison
- Export-to-CSV of scored results
- A "best variant wins" promotion flow
- CI workflow (GitHub Actions)
- pre-commit hooks
- mypy / strict typing

These are deliberate omissions, not oversights — call them out as separate spec topics when ready.
