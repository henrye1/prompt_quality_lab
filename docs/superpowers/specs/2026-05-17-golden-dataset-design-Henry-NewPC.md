# Golden Labelled Dataset — Design

**Date:** 2026-05-17
**Status:** Approved (brainstorming complete)
**Author:** Henry + Claude (Opus 4.7)
**Related repos:** `credit_paper`, `prompt_quality_lab`, new `credit_datasets`

## 1. Purpose

Build a shared, versioned golden dataset of credit-paper input→output pairs, with a small Python package for read/write access and a Streamlit page (hosted in `prompt_quality_lab`) for management.

Today, gold examples sit implicitly in `credit_paper/data/fs_learning_inputs/` (few-shot pairs) and `credit_paper/data/eval_input/` (human reports for comparison). Without a formal structure, we cannot:

- Reliably evaluate prompt variants against a stable benchmark.
- Extend to other asset classes without ad-hoc folder copying.
- Monitor output quality over time.

This dataset is the foundation everything else hangs off.

## 2. Scope

**This spec covers:**

1. Folder layout, manifest schema, and ID conventions for the dataset.
2. The `credit_datasets` Python package — types, validation, and CRUD API.
3. The Dataset Manager Streamlit page added to `prompt_quality_lab`.
4. One-shot migration from existing `credit_paper` data to seed ~80 records.

**This spec deliberately does NOT cover:**

- Eval harness (running prompts against the dataset and scoring outputs) — separate spec.
- Multi-asset-class prompt refactor in `credit_paper` — separate spec.
- Prompt-improvement workflow wiring `prompt_quality_lab` optimisers to the dataset — separate spec.
- Monitoring / drift detection — separate spec.
- `credit_paper` switching `fs_learning_inputs/` over to read from the shared dataset — follow-up change in the `credit_paper` repo, not blocked by this spec but built on top of it.

## 3. Record shape

Each record represents one credit-paper case. The unit of a record is:

- **Inputs:** N PDFs of audited financial statements (typically 2–3 years) plus one `.xlsx`/`.xlsm` risk-suite credit report.
- **Gold output:** one PDF report written by a credit rating analyst.

Existing scale to seed: ~80 records.

## 4. Folder structure

New top-level folder, alongside `credit_paper/` and `prompt_quality_lab/`:

```
credit_datasets/
├── pyproject.toml              # installable as `credit-datasets`
├── README.md                   # schema docs + how to add a record
├── src/
│   └── credit_datasets/
│       ├── __init__.py
│       ├── schema.py           # dataclasses + enums + validation
│       ├── store.py            # load_records, get_record, add_record, ...
│       └── paths.py            # resolves DATASET_ROOT
├── scripts/
│   └── migrate_from_credit_paper.py
├── tests/
│   ├── test_schema.py
│   └── test_store.py
└── data/                       # the actual dataset
    ├── manifest.json
    └── records/
        ├── 001-acme-pty-ltd/
        │   ├── inputs/
        │   │   ├── afs_2023.pdf
        │   │   ├── afs_2022.pdf
        │   │   └── risk_suite.xlsm
        │   └── gold/
        │       └── analyst_report.pdf
        └── 002-…/
```

**ID scheme:** zero-padded sequential (`001`, `002`, …). Folder name = `{id}-{slug-of-company-name}`. Slug is lowercased, non-alphanumeric characters → `-`, collapsed runs of `-`, trimmed. The numeric prefix matches the convention already used in `credit_paper/data/fs_learning_inputs/`.

## 5. Manifest schema

Single `manifest.json` at `credit_datasets/data/manifest.json` (not per-record) — 80 records is small enough that one file is easier to diff, inspect, and version-control.

```json
{
  "version": 1,
  "records": [
    {
      "id": "001",
      "company_name": "Acme Pty Ltd",
      "asset_class": "corporate",
      "sector": "manufacturing",
      "afs_years": [2023, 2022, 2021],
      "date_added": "2026-05-17",
      "reviewer": "henry@anchorpointrisk.co.za",
      "quality_grade": "gold",
      "source": "analyst_original",
      "notes": ""
    }
  ]
}
```

**Source of truth split:**

- Folder layout on disk = source of truth for *which files exist*.
- Manifest = source of truth for *metadata about records*.
- `validate()` reconciles the two and flags drift.

**Enum values** (defined in `schema.py`, extendable later):

| Field | Allowed values |
|---|---|
| `asset_class` | `corporate`, `sme`, `project_finance`, `commercial_real_estate`, `finance_company`, `sovereign`, `country`, `bank` |
| `quality_grade` | `gold`, `silver`, `bronze` |
| `source` | `analyst_original`, `analyst_corrected_llm` |

`sector` is free text (e.g. `"manufacturing"`, `"retail"`); not enumerated.

`country` and `sovereign` are intentionally distinct asset classes — sovereign refers to government debt rating; country refers to country-level macro/political risk papers.

## 6. The `credit_datasets` Python package

Three small modules. Thin layer over the manifest and folders — not a framework.

### 6.1 `schema.py` — types and validation, no I/O

```python
class AssetClass(str, Enum):
    CORPORATE = "corporate"
    SME = "sme"
    PROJECT_FINANCE = "project_finance"
    COMMERCIAL_REAL_ESTATE = "commercial_real_estate"
    FINANCE_COMPANY = "finance_company"
    SOVEREIGN = "sovereign"
    COUNTRY = "country"
    BANK = "bank"

class QualityGrade(str, Enum):
    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"

class Source(str, Enum):
    ANALYST_ORIGINAL = "analyst_original"
    ANALYST_CORRECTED_LLM = "analyst_corrected_llm"

@dataclass(frozen=True)
class Record:
    id: str                    # "001"
    company_name: str
    asset_class: AssetClass
    sector: str
    afs_years: list[int]
    date_added: date
    reviewer: str
    quality_grade: QualityGrade
    source: Source
    notes: str = ""

    @property
    def folder_name(self) -> str:               # "001-acme-pty-ltd"
        ...
    def inputs_dir(self, root: Path) -> Path:
        ...
    def gold_dir(self, root: Path) -> Path:
        ...
    def input_files(self, root: Path) -> list[Path]:
        ...
    def gold_file(self, root: Path) -> Path:
        ...
```

### 6.2 `store.py` — read/write manifest and folders

```python
def load_records(root: Path | None = None) -> list[Record]
def get_record(id: str, root: Path | None = None) -> Record
def add_record(
    record: Record,
    input_files: list[Path],
    gold_file: Path,
    root: Path | None = None,
) -> Record
    # creates the record folder, copies files into inputs/ and gold/,
    # appends the metadata to manifest.json
def update_record(id: str, root: Path | None = None, **fields) -> Record
    # metadata edits only — does not move files
def delete_record(id: str, root: Path | None = None) -> None
    # removes the folder and the manifest entry
def next_id(root: Path | None = None) -> str
    # "045" if 044 is the highest existing id
def validate(root: Path | None = None) -> ValidationReport
```

`ValidationReport` flags:

- Records in manifest with no folder on disk.
- Folders on disk with no manifest entry.
- Records with empty `inputs/` directory.
- Records with missing or multiple files in `gold/`.
- Duplicate IDs in the manifest.

### 6.3 `paths.py` — resolve the dataset root

```python
def dataset_root() -> Path:
    # Order of precedence:
    # 1. $CREDIT_DATASETS_ROOT environment variable
    # 2. <package install location>/../data (when running from a checkout)
    # 3. <CWD>/../credit_datasets/data (sibling-folder fallback)
```

### 6.4 Consumers

- `prompt_quality_lab` adds `credit-datasets @ file:../credit_datasets` to its `pyproject.toml` as an editable dependency and imports from `credit_datasets`.
- `credit_paper` does the same when it's ready to switch `fs_learning_inputs/` over to reading from the shared dataset. That switch is a follow-up, not part of this spec.

### 6.5 Tests

Pure logic only. No Streamlit, no network. Filesystem I/O is constrained to `tmp_path` fixtures.

- `test_schema.py` — folder name slugification, enum rejection, dataclass field types, edge cases (empty company name, unicode characters).
- `test_store.py` — `tmp_path`-based fake dataset roots; covers add / get / update / delete / `validate` round-trips, plus the missing-folder, orphan-folder, missing-input-files, missing-gold-file, and duplicate-id cases.

## 7. Dataset Manager Streamlit page

Lives in `prompt_quality_lab`. The current app is a single tabbed UI; adding a page means a small structural change.

### 7.1 Structural change to `prompt_quality_lab`

Convert the existing tabbed UI into Streamlit's multi-page layout (mirroring `credit_paper`'s pattern):

```
prompt_quality_lab/
├── streamlit_app.py            # already exists — becomes the home page
└── pages/                      # NEW
    └── 1_Dataset_Manager.py    # NEW — thin wrapper that delegates to the package
```

The four existing optimisers stay on the home page (no UI change for them). The Dataset Manager appears at `/Dataset_Manager` in the Streamlit sidebar.

### 7.2 Page module layout (real logic in the package, not the page file)

```
src/prompt_quality_lab/dataset_manager/
├── __init__.py
├── page.py          # render() — top-level Streamlit composition
├── list_view.py     # browse + filter records
├── detail_view.py   # view/edit one record's metadata, preview files
└── add_view.py      # upload files + fill form to create a new record
```

### 7.3 Modes

Top-level radio / segmented control picks the mode.

**Browse**

- Table of all records (`id`, `company_name`, `asset_class`, `sector`, `quality_grade`, `date_added`, `reviewer`).
- Filters above the table: `asset_class` multiselect, `quality_grade` multiselect, free-text search across company / sector / notes.
- Click a row → switch to Detail mode for that record.

**Detail**

- Selected record's metadata in an editable form (all 10 fields; enums rendered as selectboxes).
- Below the form: list of input files with download buttons; the gold file with download button and inline PDF preview via Streamlit's built-in viewer.
- Buttons: **Save changes**, **Delete record** (delete requires a confirm checkbox).

**Add new record**

- Metadata fields (id auto-suggested via `next_id()`, editable if the user wants a custom number).
- File uploaders:
  - "Input files (AFS PDFs + risk suite .xlsm)" — multi-file.
  - "Gold report (analyst PDF)" — single file.
- **Save** calls `store.add_record()`, which copies the uploaded files into the new record's folder and appends to the manifest.

### 7.4 Dataset health surface

Top of every mode: a small expander labelled "Dataset health" that runs `store.validate()` and shows any `ValidationReport` issues (with a red icon if any exist). This is how validation problems surface without a separate "fix" UI.

### 7.5 Destructive-action confirmation

Delete and overwrite-on-save both require a confirm checkbox tick before the action button enables.

### 7.6 Out of scope for the page (deferred)

- Bulk upload (CSV of metadata + zip of files).
- Per-record audit log of who edited what when.
- Diff view between two records.
- A tagging UI (tags are not in the schema yet).

## 8. Migration from existing data

One-shot script to seed the dataset from `credit_paper`'s existing folders. Not an ongoing sync.

### 8.1 Sources

| Existing location | Contents | Maps to |
|---|---|---|
| `credit_paper/data/fs_learning_inputs/` | `NN. Company Name.md` (parsed ratios) + `NN. Company Name.pdf` (analyst report), linked by numeric prefix | One Record per pair. The `.md` is a parsed view; the `.pdf` becomes the gold file. |
| `credit_paper/data/eval_input/` | Human-written reports used by the Stage 5 comparator | If the filename matches a company already imported from `fs_learning_inputs/` (case-insensitive, ignoring numeric prefixes and extension), skip — assume duplicate. Otherwise port as a new Record (the operator confirms the company name during the interactive prompt). |
| `credit_paper/data/report_inputs/` | Original `.xlsx`/`.xlsm` ratio files + AFS PDFs from prior runs | Where the original `.xlsm` for a record can be located, copy it into the new `inputs/` folder so the canonical source is preserved (not just the parsed `.md`). |

### 8.2 Script behaviour — `credit_datasets/scripts/migrate_from_credit_paper.py`

Interactive CLI, run once to seed the dataset. The interactive CLI exists *in addition to* the Streamlit Dataset Manager page: the CLI is the right shape for the one-off bulk seeding (operator sits at a terminal answering metadata prompts for ~80 records in a row), while the Streamlit page is the right shape for ongoing per-record maintenance.

Idempotent: re-running on an already-migrated record is a no-op.

1. Scan `fs_learning_inputs/` for `NN. CompanyName.{md,pdf}` pairs. Extract `NN` and `CompanyName`.
2. For each pair, construct a `Record` with what's known. Prompt the operator (CLI) for unknown metadata: `asset_class`, `sector`, `afs_years`, `quality_grade`. Default the rest:
   - `source = "analyst_original"`
   - `reviewer = "henry@anchorpointrisk.co.za"`
   - `date_added = today`
   - `notes = ""`
3. Look in `report_inputs/` for a matching `.xlsm` and AFS PDFs by company name; copy them into the new `inputs/` folder. If not found, copy the `.md` as a fallback and add a note: `"Inputs derived from parsed markdown; original .xlsm not available"`.
4. Copy the analyst PDF into `gold/`.
5. Append to `manifest.json` via `store.add_record()`.

### 8.3 Known gaps the migration will surface

- Existing pairs may not have the original `.xlsm` retained — only the parsed `.md`. Such records get the fallback note above.
- Most existing records will be missing `asset_class`, `sector`, and `afs_years`. The script cannot infer these; the operator fills them in interactively. Expect a 1–2 hour seeding session.
- Do not auto-assume `quality_grade = "gold"` for everything. Migration defaults to `silver`; the operator upgrades records to `gold` later via the Dataset Manager page once they've been re-reviewed.

### 8.4 Verification after migration

- `validate()` reports zero issues.
- `load_records()` returns exactly the expected count (≈80).
- The migration script prints both at the end.

## 9. Out of scope (deferred)

All deliberate — listed so we do not creep into them, and so follow-on specs have a clean starting point.

- **Eval harness** — running prompts against the golden set and scoring outputs.
- **Multi-asset-class prompt refactor** in `credit_paper`.
- **Prompt-improvement workflow** — wiring `prompt_quality_lab` optimisers to consume the dataset and write candidate prompts back.
- **Monitoring dashboard** — observing production runs over time, drift detection, regression alerts.
- **`credit_paper` switching `fs_learning_inputs/` to read from the shared dataset** — straightforward but separate change in the `credit_paper` repo, lands after this spec.
- **Bulk upload (CSV + zip)**, **tags**, **per-record audit log**, **diff between records**, **PII / anonymisation policy** — noted, deferred until a real need surfaces.
- **Authentication on the Dataset Manager page** — single-user app on a local machine, no auth needed today. Revisit if it ever runs on a shared server.
- **Git versioning / backup beyond OneDrive** — OneDrive provides versioning and sync. Revisit if the dataset grows past what OneDrive comfortably handles.

## 10. Acceptance criteria

This spec is considered delivered when:

1. The `credit_datasets/` package exists at the path described, installs cleanly (`uv pip install -e .`), and has passing tests covering the cases listed in §6.5.
2. `prompt_quality_lab` has a working Dataset Manager page accessible from the sidebar, exercising all three modes (Browse, Detail, Add).
3. The migration script has run end-to-end against `credit_paper/data/`, populating `credit_datasets/data/manifest.json` with ≈80 records, and `validate()` reports zero issues.
4. Both `prompt_quality_lab` and (in a follow-up change) `credit_paper` can import `credit_datasets` and read records.
