# Prompt Quality Lab

A Streamlit app for testing prompt-optimisation strategies on your own prompts using Anthropic Claude. Four approaches in one UI:

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

The app also supports a specialised credit paper workflow:

- **Credit paper input documents**: upload financial statements, credit reports, or related input files as text-based prompts or documents.
- **Target style example documents**: upload example credit reports in PDF/DOCX/MD to capture the desired output style.

## Extra file support

To enable Excel, Word, and PDF uploads, install the optional dependencies:

```powershell
uv run pip install pandas openpyxl python-docx PyPDF2
```

If you are using `uv sync`, simply run it after updating requirements so the extra packages are installed.

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
