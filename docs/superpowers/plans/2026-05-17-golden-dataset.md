# Golden Labelled Dataset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a shared `credit_datasets` package with a manifest-backed file store, plus a Dataset Manager Streamlit page in `prompt_quality_lab` and a one-shot migration script that seeds ~80 records from `credit_paper/data/fs_learning_inputs/` and `eval_input/`.

**Architecture:** Single source of truth = `manifest.json` + `records/{id-slug}/{inputs,gold}/` folder layout in a new top-level `credit_datasets/` repo. A thin Python package exposes a typed `Record` dataclass and a CRUD `store`. The Streamlit page in `prompt_quality_lab` (converted to multi-page) provides Browse/Detail/Add UX. An interactive CLI seeds existing pairs once.

**Tech Stack:** Python 3.11+, dataclasses + enums, uv, pytest, Streamlit. No new external services.

**Spec:** [2026-05-17-golden-dataset-design.md](../specs/2026-05-17-golden-dataset-design.md)

---

## File Structure

### New repo: `credit_datasets/` (alongside `credit_paper/` and `prompt_quality_lab/`)

| Path | Responsibility |
|---|---|
| `pyproject.toml` | Package metadata, runtime + dev deps, ruff + pytest config |
| `.gitignore` | Ignores `data/` (real client PDFs and PII never enter git) |
| `README.md` | Schema docs + how to add a record |
| `src/credit_datasets/__init__.py` | Public exports |
| `src/credit_datasets/schema.py` | Enums, `Record` dataclass, `ValidationReport` |
| `src/credit_datasets/store.py` | `load_records`, `get_record`, `add_record`, `update_record`, `delete_record`, `next_id`, `validate` |
| `src/credit_datasets/paths.py` | `dataset_root()` resolution |
| `scripts/migrate_from_credit_paper.py` | One-shot interactive CLI |
| `tests/__init__.py` | — |
| `tests/conftest.py` | `tmp_dataset_root` fixture |
| `tests/test_schema.py` | Slugification, enum validation, dataclass behaviour |
| `tests/test_store.py` | CRUD round-trips + validation edge cases |
| `tests/test_migrate.py` | Pairing logic + idempotency |

### Existing repo: `prompt_quality_lab/` (modified)

| Path | Responsibility |
|---|---|
| `pyproject.toml` | Add `credit-datasets` as editable dep |
| `pages/1_Dataset_Manager.py` (new) | Thin Streamlit page shim → calls `dataset_manager.page.render()` |
| `src/prompt_quality_lab/dataset_manager/__init__.py` (new) | Package init |
| `src/prompt_quality_lab/dataset_manager/page.py` (new) | `render()` — mode dispatch + dataset health expander |
| `src/prompt_quality_lab/dataset_manager/list_view.py` (new) | Browse table + filters |
| `src/prompt_quality_lab/dataset_manager/detail_view.py` (new) | View/edit form + file preview |
| `src/prompt_quality_lab/dataset_manager/add_view.py` (new) | Upload + form |

---

## Notes for the implementing engineer

- **Working directories.** Tasks 1–15 happen inside the new `credit_datasets/` repo (which you `git init` in Task 1). Tasks 16–22 happen inside `prompt_quality_lab/`. Always `cd` to the right repo before running commands.
- **OneDrive paths.** The repos live under `C:\Users\APR\OneDrive - Anchor Point Risk (Pty) Ltd\Desktop\VS_CODE_REPOSITORY\`. Quote paths with spaces.
- **Streamlit tests.** Streamlit code is hard to unit-test cleanly. The plan extracts pure functions (filtering, slug formatting) into helpers that *are* unit-tested, and treats `render()`-level functions as integration-tested via manual smoke runs.
- **PII.** Real client AFS PDFs and company names are sensitive. `credit_datasets/data/` is gitignored. The manifest contains real names; never push the dataset to a public remote.
- **Python version.** Use 3.11+ (matches `prompt_quality_lab`). `from __future__ import annotations` not required.

---

## Phase 1 — `credit_datasets` package

### Task 1: Scaffold the `credit_datasets` repo

**Files:**
- Create: `credit_datasets/pyproject.toml`
- Create: `credit_datasets/.gitignore`
- Create: `credit_datasets/README.md` (skeleton — full content in Task 11)
- Create: `credit_datasets/src/credit_datasets/__init__.py`
- Create: `credit_datasets/tests/__init__.py`
- Create: `credit_datasets/tests/conftest.py`
- Create: `credit_datasets/data/.gitkeep`

- [ ] **Step 1: Create the folder + `pyproject.toml`**

```bash
mkdir -p credit_datasets/src/credit_datasets
mkdir -p credit_datasets/tests
mkdir -p credit_datasets/scripts
mkdir -p credit_datasets/data
```

`credit_datasets/pyproject.toml`:

```toml
[project]
name = "credit-datasets"
version = "0.1.0"
description = "Shared golden labelled dataset for credit paper LLM work"
requires-python = ">=3.11"
dependencies = []

[dependency-groups]
dev = [
    "pytest>=8.0",
    "ruff>=0.6",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/credit_datasets"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: `.gitignore`**

`credit_datasets/.gitignore`:

```
# Python
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
.ruff_cache/
dist/
build/
*.egg-info/

# Dataset payload — never in git (real client PDFs + PII)
data/records/
data/manifest.json

# IDE
.vscode/
```

`credit_datasets/data/.gitkeep`:

```

```

- [ ] **Step 3: Skeleton README**

`credit_datasets/README.md`:

```markdown
# credit_datasets

Shared golden labelled dataset of credit-paper inputs and analyst-written outputs.

Used by `credit_paper` (as few-shot examples) and `prompt_quality_lab` (as the evaluation set).

See [`docs/superpowers/specs/2026-05-17-golden-dataset-design.md`](../prompt_quality_lab/docs/superpowers/specs/2026-05-17-golden-dataset-design.md) in `prompt_quality_lab` for the full design.

Full README in Task 11 of the implementation plan.
```

- [ ] **Step 4: Empty package + test scaffolding**

`credit_datasets/src/credit_datasets/__init__.py`:

```python
"""credit_datasets — shared golden labelled dataset."""

__version__ = "0.1.0"
```

`credit_datasets/tests/__init__.py`:

```python
```

`credit_datasets/tests/conftest.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_dataset_root(tmp_path: Path) -> Path:
    """A fresh, empty dataset root with an initial empty manifest."""
    root = tmp_path / "credit_datasets_data"
    root.mkdir()
    (root / "records").mkdir()
    (root / "manifest.json").write_text('{"version": 1, "records": []}\n', encoding="utf-8")
    return root
```

- [ ] **Step 5: Initialise git + install + first commit**

```bash
cd credit_datasets
git init
uv sync
git add .
git commit -m "chore: scaffold credit_datasets package"
```

Expected: `uv sync` succeeds, repo initialised with one commit.

---

### Task 2: `paths.py` and `dataset_root()` resolution

**Files:**
- Create: `credit_datasets/src/credit_datasets/paths.py`
- Create: `credit_datasets/tests/test_paths.py`

- [ ] **Step 1: Write the failing test**

`credit_datasets/tests/test_paths.py`:

```python
from __future__ import annotations

import os
from pathlib import Path

import pytest

from credit_datasets import paths


def test_env_var_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    custom = tmp_path / "custom_root"
    custom.mkdir()
    monkeypatch.setenv("CREDIT_DATASETS_ROOT", str(custom))
    assert paths.dataset_root() == custom


def test_creates_root_if_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    custom = tmp_path / "not_yet"
    monkeypatch.setenv("CREDIT_DATASETS_ROOT", str(custom))
    root = paths.dataset_root()
    assert root.exists()
    assert (root / "records").exists()
    assert (root / "manifest.json").exists()


def test_default_when_env_unset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CREDIT_DATASETS_ROOT", raising=False)
    # Simulate running from a checkout: package_dir/../../data
    fake_pkg = tmp_path / "src" / "credit_datasets"
    fake_pkg.mkdir(parents=True)
    monkeypatch.setattr(paths, "_package_dir", lambda: fake_pkg)
    root = paths.dataset_root()
    assert root == tmp_path / "data"
```

- [ ] **Step 2: Run the test — expect failure**

```bash
uv run pytest tests/test_paths.py -v
```

Expected: ImportError or AttributeError on `paths.dataset_root` / `paths._package_dir`.

- [ ] **Step 3: Implement `paths.py`**

`credit_datasets/src/credit_datasets/paths.py`:

```python
"""Resolve the dataset root directory."""

from __future__ import annotations

import os
from pathlib import Path


def _package_dir() -> Path:
    """Return the directory containing this file. Indirected for test overrides."""
    return Path(__file__).parent


def dataset_root() -> Path:
    """Resolve the dataset root, creating the folder + empty manifest if missing.

    Order of precedence:
    1. $CREDIT_DATASETS_ROOT
    2. <package>/../../data   (when running from a source checkout)
    """
    env = os.environ.get("CREDIT_DATASETS_ROOT")
    root = Path(env).resolve() if env else (_package_dir().parent.parent / "data").resolve()
    root.mkdir(parents=True, exist_ok=True)
    records = root / "records"
    records.mkdir(exist_ok=True)
    manifest = root / "manifest.json"
    if not manifest.exists():
        manifest.write_text('{"version": 1, "records": []}\n', encoding="utf-8")
    return root
```

- [ ] **Step 4: Run the test — expect pass**

```bash
uv run pytest tests/test_paths.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/credit_datasets/paths.py tests/test_paths.py
git commit -m "feat(paths): dataset_root() with env override and auto-create"
```

---

### Task 3: `schema.py` — enums

**Files:**
- Create: `credit_datasets/src/credit_datasets/schema.py`
- Create: `credit_datasets/tests/test_schema.py`

- [ ] **Step 1: Write the failing test**

`credit_datasets/tests/test_schema.py`:

```python
from __future__ import annotations

import pytest

from credit_datasets.schema import AssetClass, QualityGrade, Source


def test_asset_class_values() -> None:
    assert {a.value for a in AssetClass} == {
        "corporate",
        "sme",
        "project_finance",
        "commercial_real_estate",
        "finance_company",
        "sovereign",
        "country",
        "bank",
    }


def test_quality_grade_values() -> None:
    assert {g.value for g in QualityGrade} == {"gold", "silver", "bronze"}


def test_source_values() -> None:
    assert {s.value for s in Source} == {"analyst_original", "analyst_corrected_llm"}


def test_enum_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        AssetClass("crypto")
```

- [ ] **Step 2: Run — expect ImportError**

```bash
uv run pytest tests/test_schema.py -v
```

Expected: ImportError on `credit_datasets.schema`.

- [ ] **Step 3: Implement the enums**

`credit_datasets/src/credit_datasets/schema.py`:

```python
"""Types for the golden labelled dataset."""

from __future__ import annotations

from enum import Enum


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
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run pytest tests/test_schema.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/credit_datasets/schema.py tests/test_schema.py
git commit -m "feat(schema): asset class, quality grade, source enums"
```

---

### Task 4: `Record` dataclass + `folder_name` slugification

**Files:**
- Modify: `credit_datasets/src/credit_datasets/schema.py`
- Modify: `credit_datasets/tests/test_schema.py`

- [ ] **Step 1: Add the failing tests**

Append to `credit_datasets/tests/test_schema.py`:

```python
from dataclasses import FrozenInstanceError
from datetime import date

from credit_datasets.schema import Record


def _make_record(**overrides) -> Record:
    defaults = dict(
        id="001",
        company_name="Acme Pty Ltd",
        asset_class=AssetClass.CORPORATE,
        sector="manufacturing",
        afs_years=[2023, 2022, 2021],
        date_added=date(2026, 5, 17),
        reviewer="henry@anchorpointrisk.co.za",
        quality_grade=QualityGrade.SILVER,
        source=Source.ANALYST_ORIGINAL,
        notes="",
    )
    defaults.update(overrides)
    return Record(**defaults)


def test_folder_name_basic() -> None:
    assert _make_record().folder_name == "001-acme-pty-ltd"


def test_folder_name_strips_punctuation() -> None:
    rec = _make_record(company_name="Tšhwane! Holdings, Inc. (Pty)")
    assert rec.folder_name == "001-tshwane-holdings-inc-pty"


def test_folder_name_collapses_runs_of_separators() -> None:
    rec = _make_record(id="042", company_name="A   B---C")
    assert rec.folder_name == "042-a-b-c"


def test_folder_name_trims_leading_trailing_separators() -> None:
    rec = _make_record(company_name="---X---")
    assert rec.folder_name == "001-x"


def test_record_is_frozen() -> None:
    rec = _make_record()
    with pytest.raises(FrozenInstanceError):
        rec.id = "002"  # type: ignore[misc]


def test_empty_company_name_rejected() -> None:
    with pytest.raises(ValueError, match="company_name"):
        _make_record(company_name="")


def test_id_must_be_zero_padded_digits() -> None:
    with pytest.raises(ValueError, match="id"):
        _make_record(id="1")
    with pytest.raises(ValueError, match="id"):
        _make_record(id="abc")
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run pytest tests/test_schema.py -v
```

Expected: ImportError on `Record`.

- [ ] **Step 3: Implement the dataclass**

Append to `credit_datasets/src/credit_datasets/schema.py`:

```python
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date


_SLUG_RE = re.compile(r"[^a-z0-9]+")
_ID_RE = re.compile(r"^\d{3,}$")


def _slugify(text: str) -> str:
    """Lowercase, strip diacritics, replace non-alphanumeric with '-', collapse, trim."""
    normalised = unicodedata.normalize("NFKD", text)
    ascii_text = normalised.encode("ascii", "ignore").decode("ascii").lower()
    slug = _SLUG_RE.sub("-", ascii_text).strip("-")
    return re.sub(r"-+", "-", slug)


@dataclass(frozen=True)
class Record:
    id: str
    company_name: str
    asset_class: AssetClass
    sector: str
    afs_years: list[int]
    date_added: date
    reviewer: str
    quality_grade: QualityGrade
    source: Source
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.company_name.strip():
            raise ValueError("company_name must not be empty")
        if not _ID_RE.match(self.id):
            raise ValueError(f"id must be zero-padded digits, got {self.id!r}")

    @property
    def folder_name(self) -> str:
        return f"{self.id}-{_slugify(self.company_name)}"
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run pytest tests/test_schema.py -v
```

Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add src/credit_datasets/schema.py tests/test_schema.py
git commit -m "feat(schema): Record dataclass with slugified folder_name"
```

---

### Task 5: `Record` path helpers

**Files:**
- Modify: `credit_datasets/src/credit_datasets/schema.py`
- Modify: `credit_datasets/tests/test_schema.py`

- [ ] **Step 1: Add the failing tests**

Append to `credit_datasets/tests/test_schema.py`:

```python
from pathlib import Path


def test_inputs_and_gold_dirs(tmp_dataset_root: Path) -> None:
    rec = _make_record()
    assert rec.inputs_dir(tmp_dataset_root) == tmp_dataset_root / "records" / "001-acme-pty-ltd" / "inputs"
    assert rec.gold_dir(tmp_dataset_root) == tmp_dataset_root / "records" / "001-acme-pty-ltd" / "gold"


def test_input_files_lists_files_only(tmp_dataset_root: Path) -> None:
    rec = _make_record()
    rec.inputs_dir(tmp_dataset_root).mkdir(parents=True)
    (rec.inputs_dir(tmp_dataset_root) / "afs_2023.pdf").write_bytes(b"x")
    (rec.inputs_dir(tmp_dataset_root) / "risk_suite.xlsm").write_bytes(b"y")
    files = sorted(p.name for p in rec.input_files(tmp_dataset_root))
    assert files == ["afs_2023.pdf", "risk_suite.xlsm"]


def test_input_files_empty_when_missing(tmp_dataset_root: Path) -> None:
    rec = _make_record()
    assert rec.input_files(tmp_dataset_root) == []


def test_gold_file_returns_single_pdf(tmp_dataset_root: Path) -> None:
    rec = _make_record()
    rec.gold_dir(tmp_dataset_root).mkdir(parents=True)
    target = rec.gold_dir(tmp_dataset_root) / "analyst_report.pdf"
    target.write_bytes(b"z")
    assert rec.gold_file(tmp_dataset_root) == target


def test_gold_file_returns_none_when_missing(tmp_dataset_root: Path) -> None:
    rec = _make_record()
    assert rec.gold_file(tmp_dataset_root) is None
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run pytest tests/test_schema.py -v
```

Expected: AttributeError on `inputs_dir`.

- [ ] **Step 3: Add the helpers**

Append to the `Record` class in `credit_datasets/src/credit_datasets/schema.py`:

```python
    def record_dir(self, root: Path) -> Path:
        return root / "records" / self.folder_name

    def inputs_dir(self, root: Path) -> Path:
        return self.record_dir(root) / "inputs"

    def gold_dir(self, root: Path) -> Path:
        return self.record_dir(root) / "gold"

    def input_files(self, root: Path) -> list[Path]:
        d = self.inputs_dir(root)
        if not d.exists():
            return []
        return [p for p in sorted(d.iterdir()) if p.is_file()]

    def gold_file(self, root: Path) -> Path | None:
        d = self.gold_dir(root)
        if not d.exists():
            return None
        files = [p for p in d.iterdir() if p.is_file()]
        return files[0] if len(files) == 1 else None
```

Also add `from pathlib import Path` to the imports at the top of `schema.py`.

- [ ] **Step 4: Run — expect pass**

```bash
uv run pytest tests/test_schema.py -v
```

Expected: 16 passed.

- [ ] **Step 5: Commit**

```bash
git add src/credit_datasets/schema.py tests/test_schema.py
git commit -m "feat(schema): Record path helpers"
```

---

### Task 6: `store.py` — `load_records`, `get_record`, `next_id`

**Files:**
- Create: `credit_datasets/src/credit_datasets/store.py`
- Create: `credit_datasets/tests/test_store.py`

- [ ] **Step 1: Write the failing tests**

`credit_datasets/tests/test_store.py`:

```python
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from credit_datasets import store
from credit_datasets.schema import AssetClass, QualityGrade, Record, Source


def _write_manifest(root: Path, records: list[dict]) -> None:
    (root / "manifest.json").write_text(
        json.dumps({"version": 1, "records": records}, indent=2),
        encoding="utf-8",
    )


def _sample_metadata(id: str = "001", company: str = "Acme Pty Ltd") -> dict:
    return {
        "id": id,
        "company_name": company,
        "asset_class": "corporate",
        "sector": "manufacturing",
        "afs_years": [2023, 2022, 2021],
        "date_added": "2026-05-17",
        "reviewer": "henry@anchorpointrisk.co.za",
        "quality_grade": "silver",
        "source": "analyst_original",
        "notes": "",
    }


def test_load_records_empty(tmp_dataset_root: Path) -> None:
    assert store.load_records(tmp_dataset_root) == []


def test_load_records_single(tmp_dataset_root: Path) -> None:
    _write_manifest(tmp_dataset_root, [_sample_metadata()])
    records = store.load_records(tmp_dataset_root)
    assert len(records) == 1
    assert records[0].id == "001"
    assert records[0].asset_class is AssetClass.CORPORATE
    assert records[0].quality_grade is QualityGrade.SILVER
    assert records[0].source is Source.ANALYST_ORIGINAL
    assert records[0].date_added == date(2026, 5, 17)


def test_get_record_found(tmp_dataset_root: Path) -> None:
    _write_manifest(tmp_dataset_root, [_sample_metadata(id="042")])
    rec = store.get_record("042", tmp_dataset_root)
    assert rec.id == "042"


def test_get_record_missing(tmp_dataset_root: Path) -> None:
    with pytest.raises(KeyError, match="999"):
        store.get_record("999", tmp_dataset_root)


def test_next_id_empty(tmp_dataset_root: Path) -> None:
    assert store.next_id(tmp_dataset_root) == "001"


def test_next_id_increments(tmp_dataset_root: Path) -> None:
    _write_manifest(
        tmp_dataset_root,
        [_sample_metadata(id="001"), _sample_metadata(id="012"), _sample_metadata(id="005")],
    )
    assert store.next_id(tmp_dataset_root) == "013"
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run pytest tests/test_store.py -v
```

Expected: ImportError on `credit_datasets.store`.

- [ ] **Step 3: Implement read-only store functions**

`credit_datasets/src/credit_datasets/store.py`:

```python
"""Manifest-backed CRUD over the dataset folder."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from credit_datasets import paths
from credit_datasets.schema import AssetClass, QualityGrade, Record, Source


def _resolve_root(root: Path | None) -> Path:
    return root if root is not None else paths.dataset_root()


def _manifest_path(root: Path) -> Path:
    return root / "manifest.json"


def _read_manifest(root: Path) -> dict:
    return json.loads(_manifest_path(root).read_text(encoding="utf-8"))


def _record_from_dict(d: dict) -> Record:
    return Record(
        id=d["id"],
        company_name=d["company_name"],
        asset_class=AssetClass(d["asset_class"]),
        sector=d["sector"],
        afs_years=list(d["afs_years"]),
        date_added=date.fromisoformat(d["date_added"]),
        reviewer=d["reviewer"],
        quality_grade=QualityGrade(d["quality_grade"]),
        source=Source(d["source"]),
        notes=d.get("notes", ""),
    )


def load_records(root: Path | None = None) -> list[Record]:
    """Read every record in the manifest, in insertion order."""
    r = _resolve_root(root)
    return [_record_from_dict(d) for d in _read_manifest(r)["records"]]


def get_record(id: str, root: Path | None = None) -> Record:
    """Return the record with the given id; raise KeyError if absent."""
    for rec in load_records(root):
        if rec.id == id:
            return rec
    raise KeyError(f"No record with id {id!r}")


def next_id(root: Path | None = None) -> str:
    """Return the next free zero-padded id (3 digits min)."""
    existing = [int(r.id) for r in load_records(root)]
    n = (max(existing) + 1) if existing else 1
    return f"{n:03d}"
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run pytest tests/test_store.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/credit_datasets/store.py tests/test_store.py
git commit -m "feat(store): load_records, get_record, next_id"
```

---

### Task 7: `store.add_record`

**Files:**
- Modify: `credit_datasets/src/credit_datasets/store.py`
- Modify: `credit_datasets/tests/test_store.py`

- [ ] **Step 1: Write the failing test**

Append to `credit_datasets/tests/test_store.py`:

```python
def _build_record(id: str = "001", company: str = "Acme Pty Ltd") -> Record:
    return Record(
        id=id,
        company_name=company,
        asset_class=AssetClass.CORPORATE,
        sector="manufacturing",
        afs_years=[2023, 2022, 2021],
        date_added=date(2026, 5, 17),
        reviewer="henry@anchorpointrisk.co.za",
        quality_grade=QualityGrade.SILVER,
        source=Source.ANALYST_ORIGINAL,
        notes="",
    )


def _seed_files(tmp_path: Path) -> tuple[list[Path], Path]:
    src = tmp_path / "src_files"
    src.mkdir()
    afs1 = src / "afs_2023.pdf"
    afs1.write_bytes(b"afs1")
    afs2 = src / "afs_2022.pdf"
    afs2.write_bytes(b"afs2")
    risk = src / "risk_suite.xlsm"
    risk.write_bytes(b"risk")
    gold = src / "analyst_report.pdf"
    gold.write_bytes(b"gold")
    return [afs1, afs2, risk], gold


def test_add_record_copies_files_and_writes_manifest(
    tmp_dataset_root: Path, tmp_path: Path
) -> None:
    inputs, gold = _seed_files(tmp_path)
    rec = _build_record()

    saved = store.add_record(rec, inputs, gold, tmp_dataset_root)

    assert saved == rec
    # Files copied
    input_names = sorted(p.name for p in rec.input_files(tmp_dataset_root))
    assert input_names == ["afs_2022.pdf", "afs_2023.pdf", "risk_suite.xlsm"]
    assert rec.gold_file(tmp_dataset_root) is not None
    assert rec.gold_file(tmp_dataset_root).read_bytes() == b"gold"
    # Manifest entry
    loaded = store.load_records(tmp_dataset_root)
    assert len(loaded) == 1
    assert loaded[0].id == "001"


def test_add_record_rejects_duplicate_id(tmp_dataset_root: Path, tmp_path: Path) -> None:
    inputs, gold = _seed_files(tmp_path)
    store.add_record(_build_record(), inputs, gold, tmp_dataset_root)
    with pytest.raises(ValueError, match="already exists"):
        store.add_record(_build_record(), inputs, gold, tmp_dataset_root)


def test_add_record_appends_in_order(tmp_dataset_root: Path, tmp_path: Path) -> None:
    inputs, gold = _seed_files(tmp_path)
    store.add_record(_build_record(id="001"), inputs, gold, tmp_dataset_root)
    store.add_record(_build_record(id="002", company="Beta"), inputs, gold, tmp_dataset_root)
    ids = [r.id for r in store.load_records(tmp_dataset_root)]
    assert ids == ["001", "002"]
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run pytest tests/test_store.py -v
```

Expected: AttributeError on `store.add_record`.

- [ ] **Step 3: Implement `add_record`**

Append to `credit_datasets/src/credit_datasets/store.py`:

```python
import shutil


def _record_to_dict(rec: Record) -> dict:
    return {
        "id": rec.id,
        "company_name": rec.company_name,
        "asset_class": rec.asset_class.value,
        "sector": rec.sector,
        "afs_years": list(rec.afs_years),
        "date_added": rec.date_added.isoformat(),
        "reviewer": rec.reviewer,
        "quality_grade": rec.quality_grade.value,
        "source": rec.source.value,
        "notes": rec.notes,
    }


def _write_manifest(root: Path, manifest: dict) -> None:
    _manifest_path(root).write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )


def add_record(
    record: Record,
    input_files: list[Path],
    gold_file: Path,
    root: Path | None = None,
) -> Record:
    """Create the record folder, copy files, append to manifest."""
    r = _resolve_root(root)
    manifest = _read_manifest(r)
    if any(entry["id"] == record.id for entry in manifest["records"]):
        raise ValueError(f"Record {record.id!r} already exists")

    inputs_dir = record.inputs_dir(r)
    gold_dir = record.gold_dir(r)
    inputs_dir.mkdir(parents=True, exist_ok=False)
    gold_dir.mkdir(parents=True, exist_ok=False)

    for src in input_files:
        shutil.copy2(src, inputs_dir / src.name)
    shutil.copy2(gold_file, gold_dir / gold_file.name)

    manifest["records"].append(_record_to_dict(record))
    _write_manifest(r, manifest)
    return record
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run pytest tests/test_store.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add src/credit_datasets/store.py tests/test_store.py
git commit -m "feat(store): add_record copies files and updates manifest"
```

---

### Task 8: `store.update_record`

**Files:**
- Modify: `credit_datasets/src/credit_datasets/store.py`
- Modify: `credit_datasets/tests/test_store.py`

- [ ] **Step 1: Write the failing test**

Append to `credit_datasets/tests/test_store.py`:

```python
def test_update_record_changes_metadata(tmp_dataset_root: Path, tmp_path: Path) -> None:
    inputs, gold = _seed_files(tmp_path)
    store.add_record(_build_record(), inputs, gold, tmp_dataset_root)

    updated = store.update_record(
        "001",
        tmp_dataset_root,
        quality_grade=QualityGrade.GOLD,
        notes="reviewed by HE",
    )

    assert updated.quality_grade is QualityGrade.GOLD
    assert updated.notes == "reviewed by HE"
    # Persisted
    reloaded = store.get_record("001", tmp_dataset_root)
    assert reloaded.quality_grade is QualityGrade.GOLD
    assert reloaded.notes == "reviewed by HE"


def test_update_record_rejects_unknown_field(tmp_dataset_root: Path, tmp_path: Path) -> None:
    inputs, gold = _seed_files(tmp_path)
    store.add_record(_build_record(), inputs, gold, tmp_dataset_root)
    with pytest.raises(ValueError, match="unknown field"):
        store.update_record("001", tmp_dataset_root, bogus="x")


def test_update_record_missing_id(tmp_dataset_root: Path) -> None:
    with pytest.raises(KeyError, match="999"):
        store.update_record("999", tmp_dataset_root, notes="x")
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run pytest tests/test_store.py -v
```

Expected: AttributeError on `update_record`.

- [ ] **Step 3: Implement `update_record`**

Append to `credit_datasets/src/credit_datasets/store.py`:

```python
import dataclasses

_RECORD_FIELDS: frozenset[str] = frozenset(f.name for f in dataclasses.fields(Record))


def update_record(id: str, root: Path | None = None, **fields) -> Record:
    """Update metadata for a record. File contents are not touched."""
    unknown = set(fields) - _RECORD_FIELDS
    if unknown:
        raise ValueError(f"unknown field(s): {sorted(unknown)}")
    if "id" in fields and fields["id"] != id:
        raise ValueError("id is immutable")

    r = _resolve_root(root)
    manifest = _read_manifest(r)
    for i, entry in enumerate(manifest["records"]):
        if entry["id"] == id:
            current = _record_from_dict(entry)
            new = dataclasses.replace(current, **fields)
            manifest["records"][i] = _record_to_dict(new)
            _write_manifest(r, manifest)
            return new
    raise KeyError(f"No record with id {id!r}")
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run pytest tests/test_store.py -v
```

Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add src/credit_datasets/store.py tests/test_store.py
git commit -m "feat(store): update_record for metadata edits"
```

---

### Task 9: `store.delete_record`

**Files:**
- Modify: `credit_datasets/src/credit_datasets/store.py`
- Modify: `credit_datasets/tests/test_store.py`

- [ ] **Step 1: Write the failing test**

Append to `credit_datasets/tests/test_store.py`:

```python
def test_delete_record_removes_folder_and_manifest_entry(
    tmp_dataset_root: Path, tmp_path: Path
) -> None:
    inputs, gold = _seed_files(tmp_path)
    rec = _build_record()
    store.add_record(rec, inputs, gold, tmp_dataset_root)
    assert rec.record_dir(tmp_dataset_root).exists()

    store.delete_record("001", tmp_dataset_root)

    assert not rec.record_dir(tmp_dataset_root).exists()
    assert store.load_records(tmp_dataset_root) == []


def test_delete_record_missing_id(tmp_dataset_root: Path) -> None:
    with pytest.raises(KeyError, match="999"):
        store.delete_record("999", tmp_dataset_root)
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run pytest tests/test_store.py -v
```

Expected: AttributeError on `delete_record`.

- [ ] **Step 3: Implement `delete_record`**

Append to `credit_datasets/src/credit_datasets/store.py`:

```python
def delete_record(id: str, root: Path | None = None) -> None:
    """Remove the record folder and its manifest entry."""
    r = _resolve_root(root)
    manifest = _read_manifest(r)
    for i, entry in enumerate(manifest["records"]):
        if entry["id"] == id:
            rec = _record_from_dict(entry)
            folder = rec.record_dir(r)
            if folder.exists():
                shutil.rmtree(folder)
            del manifest["records"][i]
            _write_manifest(r, manifest)
            return
    raise KeyError(f"No record with id {id!r}")
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run pytest tests/test_store.py -v
```

Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add src/credit_datasets/store.py tests/test_store.py
git commit -m "feat(store): delete_record removes folder and manifest entry"
```

---

### Task 10: `store.validate` + `ValidationReport`

**Files:**
- Modify: `credit_datasets/src/credit_datasets/schema.py`
- Modify: `credit_datasets/src/credit_datasets/store.py`
- Modify: `credit_datasets/tests/test_store.py`

- [ ] **Step 1: Write the failing test**

Append to `credit_datasets/tests/test_store.py`:

```python
def test_validate_clean(tmp_dataset_root: Path, tmp_path: Path) -> None:
    inputs, gold = _seed_files(tmp_path)
    store.add_record(_build_record(), inputs, gold, tmp_dataset_root)
    report = store.validate(tmp_dataset_root)
    assert report.is_clean
    assert report.issues == []


def test_validate_missing_folder(tmp_dataset_root: Path, tmp_path: Path) -> None:
    inputs, gold = _seed_files(tmp_path)
    rec = _build_record()
    store.add_record(rec, inputs, gold, tmp_dataset_root)
    shutil.rmtree(rec.record_dir(tmp_dataset_root))
    report = store.validate(tmp_dataset_root)
    assert not report.is_clean
    assert any("missing folder" in i.lower() and "001" in i for i in report.issues)


def test_validate_orphan_folder(tmp_dataset_root: Path) -> None:
    (tmp_dataset_root / "records" / "999-rogue").mkdir(parents=True)
    report = store.validate(tmp_dataset_root)
    assert any("orphan" in i.lower() and "999-rogue" in i for i in report.issues)


def test_validate_missing_input_files(tmp_dataset_root: Path, tmp_path: Path) -> None:
    inputs, gold = _seed_files(tmp_path)
    rec = _build_record()
    store.add_record(rec, inputs, gold, tmp_dataset_root)
    for p in rec.input_files(tmp_dataset_root):
        p.unlink()
    report = store.validate(tmp_dataset_root)
    assert any("no input files" in i.lower() and "001" in i for i in report.issues)


def test_validate_missing_gold(tmp_dataset_root: Path, tmp_path: Path) -> None:
    inputs, gold = _seed_files(tmp_path)
    rec = _build_record()
    store.add_record(rec, inputs, gold, tmp_dataset_root)
    rec.gold_file(tmp_dataset_root).unlink()
    report = store.validate(tmp_dataset_root)
    assert any("missing gold" in i.lower() and "001" in i for i in report.issues)


def test_validate_duplicate_id(tmp_dataset_root: Path, tmp_path: Path) -> None:
    inputs, gold = _seed_files(tmp_path)
    store.add_record(_build_record(), inputs, gold, tmp_dataset_root)
    # Manually corrupt manifest to add a duplicate
    raw = json.loads((tmp_dataset_root / "manifest.json").read_text(encoding="utf-8"))
    raw["records"].append(dict(raw["records"][0]))
    (tmp_dataset_root / "manifest.json").write_text(json.dumps(raw, indent=2), encoding="utf-8")
    report = store.validate(tmp_dataset_root)
    assert any("duplicate id" in i.lower() and "001" in i for i in report.issues)
```

Also add `import shutil` at the top of `test_store.py` if not already present.

- [ ] **Step 2: Run — expect failure**

```bash
uv run pytest tests/test_store.py -v
```

Expected: AttributeError on `store.validate`.

- [ ] **Step 3: Define `ValidationReport` in `schema.py`**

Append to `credit_datasets/src/credit_datasets/schema.py`:

```python
@dataclass(frozen=True)
class ValidationReport:
    issues: list[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return not self.issues
```

- [ ] **Step 4: Implement `validate` in `store.py`**

Append to `credit_datasets/src/credit_datasets/store.py`:

```python
from credit_datasets.schema import ValidationReport


def validate(root: Path | None = None) -> ValidationReport:
    """Reconcile manifest against folder layout. Returns a list of issues."""
    r = _resolve_root(root)
    manifest = _read_manifest(r)
    issues: list[str] = []

    # Duplicate ids
    ids = [entry["id"] for entry in manifest["records"]]
    seen: set[str] = set()
    for i in ids:
        if i in seen:
            issues.append(f"Duplicate id in manifest: {i}")
        seen.add(i)

    manifest_folders: set[str] = set()
    for entry in manifest["records"]:
        try:
            rec = _record_from_dict(entry)
        except Exception as e:
            issues.append(f"Malformed manifest entry id={entry.get('id', '?')}: {e}")
            continue
        manifest_folders.add(rec.folder_name)
        folder = rec.record_dir(r)
        if not folder.exists():
            issues.append(f"Record {rec.id}: missing folder {folder}")
            continue
        if not rec.input_files(r):
            issues.append(f"Record {rec.id}: no input files")
        if rec.gold_file(r) is None:
            issues.append(f"Record {rec.id}: missing gold file (expected exactly one)")

    # Orphan folders
    records_dir = r / "records"
    if records_dir.exists():
        for p in records_dir.iterdir():
            if p.is_dir() and p.name not in manifest_folders:
                issues.append(f"Orphan folder (not in manifest): {p.name}")

    return ValidationReport(issues=issues)
```

- [ ] **Step 5: Run — expect pass**

```bash
uv run pytest tests/test_store.py -v
```

Expected: 20 passed.

- [ ] **Step 6: Commit**

```bash
git add src/credit_datasets/schema.py src/credit_datasets/store.py tests/test_store.py
git commit -m "feat(store): validate() reconciles manifest with disk"
```

---

### Task 11: Public exports + full README

**Files:**
- Modify: `credit_datasets/src/credit_datasets/__init__.py`
- Modify: `credit_datasets/README.md`

- [ ] **Step 1: Define public exports**

Replace `credit_datasets/src/credit_datasets/__init__.py`:

```python
"""credit_datasets — shared golden labelled dataset.

Public API:
    Record, AssetClass, QualityGrade, Source, ValidationReport
    load_records, get_record, add_record, update_record, delete_record
    next_id, validate
    dataset_root
"""

from credit_datasets.paths import dataset_root
from credit_datasets.schema import (
    AssetClass,
    QualityGrade,
    Record,
    Source,
    ValidationReport,
)
from credit_datasets.store import (
    add_record,
    delete_record,
    get_record,
    load_records,
    next_id,
    update_record,
    validate,
)

__version__ = "0.1.0"

__all__ = [
    "AssetClass",
    "QualityGrade",
    "Record",
    "Source",
    "ValidationReport",
    "add_record",
    "dataset_root",
    "delete_record",
    "get_record",
    "load_records",
    "next_id",
    "update_record",
    "validate",
    "__version__",
]
```

- [ ] **Step 2: Add an importability test**

Create `credit_datasets/tests/test_public_api.py`:

```python
def test_public_api_imports() -> None:
    import credit_datasets as cd

    assert cd.Record is not None
    assert cd.load_records is not None
    assert cd.add_record is not None
    assert cd.validate is not None
    assert cd.dataset_root is not None
```

- [ ] **Step 3: Run all tests**

```bash
uv run pytest -v
```

Expected: all tests pass (21 + 16 + 3 = ~40 tests).

- [ ] **Step 4: Write the full README**

Replace `credit_datasets/README.md`:

````markdown
# credit_datasets

Shared golden labelled dataset of credit-paper input → output pairs. Consumed by `credit_paper` (for few-shot examples) and `prompt_quality_lab` (for evaluation).

## Record layout

```
credit_datasets/data/
├── manifest.json
└── records/
    └── 001-acme-pty-ltd/
        ├── inputs/
        │   ├── afs_2023.pdf
        │   ├── afs_2022.pdf
        │   └── risk_suite.xlsm
        └── gold/
            └── analyst_report.pdf
```

`data/` is gitignored. OneDrive provides backup and sync.

## Manifest schema

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
      "quality_grade": "silver",
      "source": "analyst_original",
      "notes": ""
    }
  ]
}
```

Enum values:

| Field | Allowed values |
|---|---|
| `asset_class` | `corporate`, `sme`, `project_finance`, `commercial_real_estate`, `finance_company`, `sovereign`, `country`, `bank` |
| `quality_grade` | `gold`, `silver`, `bronze` |
| `source` | `analyst_original`, `analyst_corrected_llm` |

`sector` is free text. `afs_years` is a list of integers.

## Programmatic use

```python
from credit_datasets import load_records, add_record, validate

records = load_records()
report = validate()
assert report.is_clean
```

## Maintenance

Use the Dataset Manager Streamlit page in `prompt_quality_lab` (sidebar → Dataset Manager) for ongoing adds, edits, and deletes.

For the initial bulk seed from `credit_paper`, run:

```bash
uv run python scripts/migrate_from_credit_paper.py
```

## Configuration

`$CREDIT_DATASETS_ROOT` — override the dataset root path. Defaults to `<repo>/data/`.

## Dev

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format .
```
````

- [ ] **Step 5: Commit**

```bash
git add src/credit_datasets/__init__.py tests/test_public_api.py README.md
git commit -m "feat: public API + README"
```

---

## Phase 2 — Migration script

### Task 12: Migration pairing logic (pure)

**Files:**
- Create: `credit_datasets/scripts/__init__.py`
- Create: `credit_datasets/scripts/migrate_from_credit_paper.py`
- Create: `credit_datasets/tests/test_migrate.py`

- [ ] **Step 1: Write the failing test**

`credit_datasets/scripts/__init__.py`:

```python
```

`credit_datasets/tests/test_migrate.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.migrate_from_credit_paper import (
    Pair,
    discover_pairs,
    find_matching_inputs,
    is_already_migrated,
    parse_filename,
)
from credit_datasets import load_records, schema, store
from credit_datasets.schema import AssetClass, QualityGrade, Source


def test_parse_filename_basic() -> None:
    assert parse_filename("34. Acme Pty Ltd.pdf") == (34, "Acme Pty Ltd", "pdf")


def test_parse_filename_md() -> None:
    assert parse_filename("7. Beta Co.md") == (7, "Beta Co", "md")


def test_parse_filename_no_prefix() -> None:
    assert parse_filename("Just A Report.pdf") is None


def test_parse_filename_no_extension_we_care_about() -> None:
    assert parse_filename("34. Acme.txt") is None


def test_discover_pairs_finds_matched_pairs(tmp_path: Path) -> None:
    fs = tmp_path / "fs_learning_inputs"
    fs.mkdir()
    (fs / "1. Alpha.md").write_text("ratios")
    (fs / "1. Alpha.pdf").write_bytes(b"report")
    (fs / "2. Beta.md").write_text("ratios")
    # No pair for 2 (no pdf)
    (fs / "3. Gamma.pdf").write_bytes(b"report")
    # No pair for 3 (no md)

    pairs = discover_pairs(fs)

    assert len(pairs) == 1
    assert pairs[0].prefix == 1
    assert pairs[0].company_name == "Alpha"
    assert pairs[0].md_path.name == "1. Alpha.md"
    assert pairs[0].pdf_path.name == "1. Alpha.pdf"


def test_find_matching_inputs_locates_xlsm_and_pdfs(tmp_path: Path) -> None:
    report_inputs = tmp_path / "report_inputs"
    report_inputs.mkdir()
    (report_inputs / "Alpha Ratios.xlsm").write_bytes(b"x")
    (report_inputs / "Alpha AFS 2023.pdf").write_bytes(b"p")
    (report_inputs / "Alpha AFS 2022.pdf").write_bytes(b"p")
    (report_inputs / "Beta Ratios.xlsm").write_bytes(b"x")

    matches = find_matching_inputs("Alpha", report_inputs)

    names = sorted(p.name for p in matches)
    assert "Alpha Ratios.xlsm" in names
    assert "Alpha AFS 2023.pdf" in names
    assert "Alpha AFS 2022.pdf" in names
    assert all("Beta" not in n for n in names)


def test_is_already_migrated_true(tmp_dataset_root: Path, tmp_path: Path) -> None:
    from datetime import date

    rec = schema.Record(
        id="001",
        company_name="Alpha",
        asset_class=AssetClass.CORPORATE,
        sector="manufacturing",
        afs_years=[2023],
        date_added=date(2026, 5, 17),
        reviewer="x",
        quality_grade=QualityGrade.SILVER,
        source=Source.ANALYST_ORIGINAL,
    )
    src = tmp_path / "src"
    src.mkdir()
    inp = src / "in.pdf"
    inp.write_bytes(b"x")
    gold = src / "gold.pdf"
    gold.write_bytes(b"x")
    store.add_record(rec, [inp], gold, tmp_dataset_root)
    assert is_already_migrated("Alpha", tmp_dataset_root) is True


def test_is_already_migrated_false(tmp_dataset_root: Path) -> None:
    assert is_already_migrated("Alpha", tmp_dataset_root) is False
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run pytest tests/test_migrate.py -v
```

Expected: ImportError on `scripts.migrate_from_credit_paper`.

- [ ] **Step 3: Implement the pure helpers**

`credit_datasets/scripts/migrate_from_credit_paper.py`:

```python
"""Seed credit_datasets from credit_paper's existing fs_learning_inputs/ and report_inputs/."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from credit_datasets import load_records


_FILENAME_RE = re.compile(r"^(?P<prefix>\d+)\.\s+(?P<company>.+)\.(?P<ext>md|pdf)$", re.IGNORECASE)


@dataclass(frozen=True)
class Pair:
    prefix: int
    company_name: str
    md_path: Path
    pdf_path: Path


def parse_filename(name: str) -> tuple[int, str, str] | None:
    """Parse `34. Acme Pty Ltd.pdf` into (34, 'Acme Pty Ltd', 'pdf'). Returns None if no match."""
    m = _FILENAME_RE.match(name)
    if not m:
        return None
    return int(m.group("prefix")), m.group("company").strip(), m.group("ext").lower()


def discover_pairs(fs_learning_inputs: Path) -> list[Pair]:
    """Return matched (md, pdf) pairs from fs_learning_inputs/."""
    md: dict[int, tuple[str, Path]] = {}
    pdf: dict[int, tuple[str, Path]] = {}
    for p in sorted(fs_learning_inputs.iterdir()):
        if not p.is_file():
            continue
        parsed = parse_filename(p.name)
        if parsed is None:
            continue
        prefix, company, ext = parsed
        if ext == "md":
            md[prefix] = (company, p)
        elif ext == "pdf":
            pdf[prefix] = (company, p)
    pairs: list[Pair] = []
    for prefix in sorted(set(md) & set(pdf)):
        md_company, md_path = md[prefix]
        _, pdf_path = pdf[prefix]
        pairs.append(Pair(prefix=prefix, company_name=md_company, md_path=md_path, pdf_path=pdf_path))
    return pairs


def find_matching_inputs(company_name: str, report_inputs: Path) -> list[Path]:
    """Return files in report_inputs whose name starts (case-insensitively) with company_name."""
    if not report_inputs.exists():
        return []
    key = company_name.lower()
    matches: list[Path] = []
    for p in sorted(report_inputs.iterdir()):
        if not p.is_file():
            continue
        if p.suffix.lower() not in {".xlsm", ".xlsx", ".pdf"}:
            continue
        if p.name.lower().startswith(key):
            matches.append(p)
    return matches


def is_already_migrated(company_name: str, root: Path | None = None) -> bool:
    """True if a record with this company_name (case-insensitive) is already in the dataset."""
    key = company_name.strip().lower()
    return any(r.company_name.strip().lower() == key for r in load_records(root))
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run pytest tests/test_migrate.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/__init__.py scripts/migrate_from_credit_paper.py tests/test_migrate.py
git commit -m "feat(migrate): pure pairing + lookup helpers"
```

---

### Task 13: Migration script — interactive CLI driver

**Files:**
- Modify: `credit_datasets/scripts/migrate_from_credit_paper.py`
- Modify: `credit_datasets/tests/test_migrate.py`

- [ ] **Step 1: Write the failing tests**

Append to `credit_datasets/tests/test_migrate.py`:

```python
from io import StringIO

from scripts.migrate_from_credit_paper import migrate_pair


def test_migrate_pair_creates_record(tmp_dataset_root: Path, tmp_path: Path) -> None:
    fs = tmp_path / "fs_learning_inputs"
    fs.mkdir()
    md = fs / "1. Alpha.md"
    md.write_text("ratios")
    pdf = fs / "1. Alpha.pdf"
    pdf.write_bytes(b"gold")
    report_inputs = tmp_path / "report_inputs"
    report_inputs.mkdir()
    xlsm = report_inputs / "Alpha Ratios.xlsm"
    xlsm.write_bytes(b"x")
    afs = report_inputs / "Alpha AFS 2023.pdf"
    afs.write_bytes(b"a")

    pair = Pair(prefix=1, company_name="Alpha", md_path=md, pdf_path=pdf)
    answers = iter(["corporate", "manufacturing", "2023, 2022"])

    rec = migrate_pair(
        pair,
        report_inputs=report_inputs,
        root=tmp_dataset_root,
        reviewer="henry@anchorpointrisk.co.za",
        ask=lambda _prompt: next(answers),
    )

    assert rec.id == "001"
    assert rec.company_name == "Alpha"
    assert rec.asset_class == AssetClass.CORPORATE
    assert rec.sector == "manufacturing"
    assert rec.afs_years == [2023, 2022]
    assert rec.quality_grade == QualityGrade.SILVER  # migration default
    assert rec.source == Source.ANALYST_ORIGINAL

    # Files copied: xlsm + afs into inputs/, pdf into gold/
    inputs = sorted(p.name for p in rec.input_files(tmp_dataset_root))
    assert "Alpha Ratios.xlsm" in inputs
    assert "Alpha AFS 2023.pdf" in inputs
    assert rec.gold_file(tmp_dataset_root).read_bytes() == b"gold"


def test_migrate_pair_falls_back_to_md_when_no_xlsm(
    tmp_dataset_root: Path, tmp_path: Path
) -> None:
    fs = tmp_path / "fs_learning_inputs"
    fs.mkdir()
    md = fs / "1. Alpha.md"
    md.write_text("ratios")
    pdf = fs / "1. Alpha.pdf"
    pdf.write_bytes(b"gold")
    report_inputs = tmp_path / "report_inputs"  # empty
    report_inputs.mkdir()

    pair = Pair(prefix=1, company_name="Alpha", md_path=md, pdf_path=pdf)
    answers = iter(["sme", "retail", "2023"])

    rec = migrate_pair(
        pair,
        report_inputs=report_inputs,
        root=tmp_dataset_root,
        reviewer="henry@anchorpointrisk.co.za",
        ask=lambda _prompt: next(answers),
    )

    assert rec.notes.startswith("Inputs derived from parsed markdown")
    inputs = [p.name for p in rec.input_files(tmp_dataset_root)]
    assert "1. Alpha.md" in inputs


def test_migrate_pair_idempotent(tmp_dataset_root: Path, tmp_path: Path) -> None:
    fs = tmp_path / "fs_learning_inputs"
    fs.mkdir()
    md = fs / "1. Alpha.md"
    md.write_text("r")
    pdf = fs / "1. Alpha.pdf"
    pdf.write_bytes(b"g")
    report_inputs = tmp_path / "report_inputs"
    report_inputs.mkdir()

    pair = Pair(prefix=1, company_name="Alpha", md_path=md, pdf_path=pdf)
    answers = iter(["corporate", "manufacturing", "2023"])
    migrate_pair(pair, report_inputs=report_inputs, root=tmp_dataset_root,
                 reviewer="x", ask=lambda _p: next(answers))

    # Second run with no new answers — should detect existing and return None
    result = migrate_pair(pair, report_inputs=report_inputs, root=tmp_dataset_root,
                          reviewer="x", ask=lambda _p: pytest.fail("should not prompt"))
    assert result is None
    assert len(load_records(tmp_dataset_root)) == 1
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run pytest tests/test_migrate.py -v
```

Expected: ImportError on `migrate_pair`.

- [ ] **Step 3: Implement `migrate_pair` + entry point**

Append to `credit_datasets/scripts/migrate_from_credit_paper.py`:

```python
import argparse
import shutil
from datetime import date
from typing import Callable

from credit_datasets import schema, store
from credit_datasets.schema import AssetClass, QualityGrade, Record, Source


PromptFn = Callable[[str], str]


def _ask_asset_class(ask: PromptFn) -> AssetClass:
    valid = ", ".join(a.value for a in AssetClass)
    while True:
        raw = ask(f"Asset class ({valid}): ").strip().lower()
        try:
            return AssetClass(raw)
        except ValueError:
            print(f"  not recognised; try one of {valid}")


def _ask_sector(ask: PromptFn) -> str:
    while True:
        raw = ask("Sector (free text, e.g. manufacturing): ").strip()
        if raw:
            return raw
        print("  cannot be empty")


def _ask_afs_years(ask: PromptFn) -> list[int]:
    while True:
        raw = ask("AFS years (comma-separated, e.g. 2023, 2022, 2021): ").strip()
        try:
            years = [int(p.strip()) for p in raw.split(",") if p.strip()]
            if years and all(1900 <= y <= 2100 for y in years):
                return years
        except ValueError:
            pass
        print("  please give comma-separated 4-digit years")


def migrate_pair(
    pair: Pair,
    *,
    report_inputs: Path,
    root: Path | None,
    reviewer: str,
    ask: PromptFn,
) -> Record | None:
    """Migrate one pair. Returns the new Record, or None if already migrated."""
    if is_already_migrated(pair.company_name, root):
        return None

    print(f"\n--- {pair.prefix}. {pair.company_name} ---")
    asset_class = _ask_asset_class(ask)
    sector = _ask_sector(ask)
    afs_years = _ask_afs_years(ask)

    matched = find_matching_inputs(pair.company_name, report_inputs)
    if matched:
        input_files = matched
        notes = ""
    else:
        input_files = [pair.md_path]
        notes = "Inputs derived from parsed markdown; original .xlsm not available"

    rec = Record(
        id=store.next_id(root),
        company_name=pair.company_name,
        asset_class=asset_class,
        sector=sector,
        afs_years=afs_years,
        date_added=date.today(),
        reviewer=reviewer,
        quality_grade=QualityGrade.SILVER,
        source=Source.ANALYST_ORIGINAL,
        notes=notes,
    )
    return store.add_record(rec, input_files, pair.pdf_path, root)


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed credit_datasets from credit_paper.")
    parser.add_argument(
        "--credit-paper",
        type=Path,
        required=True,
        help="Path to the credit_paper repo root",
    )
    parser.add_argument(
        "--reviewer",
        default="henry@anchorpointrisk.co.za",
        help="Reviewer email recorded on each new record",
    )
    args = parser.parse_args()

    fs = args.credit_paper / "data" / "fs_learning_inputs"
    report_inputs = args.credit_paper / "data" / "report_inputs"
    if not fs.exists():
        print(f"ERROR: not found: {fs}")
        return 1

    pairs = discover_pairs(fs)
    print(f"Found {len(pairs)} pairs in {fs}")

    created = 0
    skipped = 0
    for pair in pairs:
        result = migrate_pair(
            pair,
            report_inputs=report_inputs,
            root=None,  # use default dataset_root()
            reviewer=args.reviewer,
            ask=input,
        )
        if result is None:
            skipped += 1
            print(f"  skipped (already in dataset): {pair.company_name}")
        else:
            created += 1
            print(f"  added id={result.id}: {pair.company_name}")

    report = store.validate()
    print(f"\nDone. Created {created}, skipped {skipped}. Validation issues: {len(report.issues)}")
    for issue in report.issues:
        print(f"  - {issue}")
    return 0 if report.is_clean else 2


if __name__ == "__main__":
    raise SystemExit(main())
```

Note: `migrate_pair`'s `root` parameter is `Path | None` so the test can pass a `tmp_dataset_root` while `main()` passes `None` (which `_resolve_root` interprets as the package default). The signature shown above is the one to use — do not change it.

- [ ] **Step 4: Run — expect pass**

```bash
uv run pytest tests/test_migrate.py -v
```

Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/migrate_from_credit_paper.py tests/test_migrate.py
git commit -m "feat(migrate): interactive CLI for seeding the dataset"
```

---

### Task 14: Migration script — `eval_input/` extension

Per spec §8.1 row 2, the migration also walks `credit_paper/data/eval_input/`. Each file there is an analyst-written report used by the Stage 5 comparator. If the company name (derived from the filename) is already in the dataset (case-insensitive match), skip it as a duplicate. Otherwise port it as a new Record, sourcing inputs from `report_inputs/` via the existing `find_matching_inputs` helper.

**Files:**
- Modify: `credit_datasets/scripts/migrate_from_credit_paper.py`
- Modify: `credit_datasets/tests/test_migrate.py`

- [ ] **Step 1: Write the failing tests**

Append to `credit_datasets/tests/test_migrate.py`:

```python
from scripts.migrate_from_credit_paper import (
    discover_eval_input_reports,
    eval_filename_to_company,
    migrate_eval_input,
)


def test_eval_filename_to_company_strips_extension_and_prefix() -> None:
    assert eval_filename_to_company("Alpha Report.pdf") == "Alpha Report"
    assert eval_filename_to_company("12. Beta.pdf") == "Beta"
    assert eval_filename_to_company("Gamma.docx") == "Gamma"


def test_discover_eval_input_reports(tmp_path: Path) -> None:
    eval_dir = tmp_path / "eval_input"
    eval_dir.mkdir()
    (eval_dir / "Alpha Report.pdf").write_bytes(b"a")
    (eval_dir / "Beta.docx").write_bytes(b"b")
    (eval_dir / "Notes.txt").write_text("skip me")  # not a report extension
    reports = discover_eval_input_reports(eval_dir)
    names = sorted(p.name for p in reports)
    assert names == ["Alpha Report.pdf", "Beta.docx"]


def test_migrate_eval_input_skips_when_already_migrated(
    tmp_dataset_root: Path, tmp_path: Path
) -> None:
    # Seed an existing record for "Alpha"
    from datetime import date

    rec = schema.Record(
        id="001",
        company_name="Alpha",
        asset_class=AssetClass.CORPORATE,
        sector="manufacturing",
        afs_years=[2023],
        date_added=date(2026, 5, 17),
        reviewer="x",
        quality_grade=QualityGrade.SILVER,
        source=Source.ANALYST_ORIGINAL,
    )
    src = tmp_path / "src"
    src.mkdir()
    (src / "in.pdf").write_bytes(b"x")
    (src / "gold.pdf").write_bytes(b"x")
    store.add_record(rec, [src / "in.pdf"], src / "gold.pdf", tmp_dataset_root)

    eval_dir = tmp_path / "eval_input"
    eval_dir.mkdir()
    report = eval_dir / "Alpha Report.pdf"
    report.write_bytes(b"new gold")

    result = migrate_eval_input(
        report,
        report_inputs=tmp_path / "report_inputs",
        root=tmp_dataset_root,
        reviewer="x",
        ask=lambda _p: pytest.fail("should not prompt"),
    )
    assert result is None
    assert len(load_records(tmp_dataset_root)) == 1


def test_migrate_eval_input_creates_new_record(
    tmp_dataset_root: Path, tmp_path: Path
) -> None:
    eval_dir = tmp_path / "eval_input"
    eval_dir.mkdir()
    report = eval_dir / "Gamma Report.pdf"
    report.write_bytes(b"gold")
    report_inputs = tmp_path / "report_inputs"
    report_inputs.mkdir()
    (report_inputs / "Gamma Ratios.xlsm").write_bytes(b"x")
    (report_inputs / "Gamma AFS 2023.pdf").write_bytes(b"a")

    # ask returns: confirm-company, asset_class, sector, afs_years
    answers = iter(["Gamma", "corporate", "retail", "2023"])
    rec = migrate_eval_input(
        report,
        report_inputs=report_inputs,
        root=tmp_dataset_root,
        reviewer="henry@anchorpointrisk.co.za",
        ask=lambda _p: next(answers),
    )
    assert rec is not None
    assert rec.company_name == "Gamma"
    assert rec.sector == "retail"
    inputs = sorted(p.name for p in rec.input_files(tmp_dataset_root))
    assert "Gamma Ratios.xlsm" in inputs
    assert rec.gold_file(tmp_dataset_root).read_bytes() == b"gold"
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run pytest tests/test_migrate.py -v
```

Expected: ImportError on `discover_eval_input_reports` / `eval_filename_to_company` / `migrate_eval_input`.

- [ ] **Step 3: Implement the helpers and CLI extension**

Append to `credit_datasets/scripts/migrate_from_credit_paper.py`:

```python
_EVAL_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".docx"})
_NUMERIC_PREFIX_RE = re.compile(r"^\d+\.\s+")


def eval_filename_to_company(name: str) -> str:
    """Strip a numeric prefix (`12. `) and the extension. Returns the candidate company name."""
    stem = Path(name).stem
    return _NUMERIC_PREFIX_RE.sub("", stem).strip()


def discover_eval_input_reports(eval_input: Path) -> list[Path]:
    """List analyst reports under eval_input/ — files with .pdf or .docx extensions only."""
    if not eval_input.exists():
        return []
    return sorted(
        p for p in eval_input.iterdir()
        if p.is_file() and p.suffix.lower() in _EVAL_EXTENSIONS
    )


def migrate_eval_input(
    report_path: Path,
    *,
    report_inputs: Path,
    root: Path | None,
    reviewer: str,
    ask: PromptFn,
) -> Record | None:
    """Migrate one eval_input/ report. Returns the new Record, or None if duplicate."""
    candidate = eval_filename_to_company(report_path.name)
    if is_already_migrated(candidate, root):
        return None

    print(f"\n--- eval_input: {report_path.name} ---")
    confirmed_name = ask(f"Company name [{candidate}]: ").strip() or candidate
    if is_already_migrated(confirmed_name, root):
        return None

    asset_class = _ask_asset_class(ask)
    sector = _ask_sector(ask)
    afs_years = _ask_afs_years(ask)

    matched = find_matching_inputs(confirmed_name, report_inputs)
    if matched:
        input_files = matched
        notes = "Sourced from eval_input/"
    else:
        # No matching inputs found — the operator may want to skip this one.
        print(f"  WARNING: no input files matched {confirmed_name!r} in {report_inputs}")
        proceed = ask("Proceed anyway with only the gold report? (y/N): ").strip().lower()
        if proceed != "y":
            return None
        input_files = []
        notes = "Sourced from eval_input/ — no matching inputs found"

    rec = Record(
        id=store.next_id(root),
        company_name=confirmed_name,
        asset_class=asset_class,
        sector=sector,
        afs_years=afs_years,
        date_added=date.today(),
        reviewer=reviewer,
        quality_grade=QualityGrade.SILVER,
        source=Source.ANALYST_ORIGINAL,
        notes=notes,
    )
    # add_record requires at least one input file to construct a valid record folder.
    # If input_files is empty, write the report itself as a placeholder input note.
    if not input_files:
        placeholder = report_path.parent / f"{rec.folder_name}_no_inputs.txt"
        placeholder.write_text("No input files were available at migration time.", encoding="utf-8")
        input_files = [placeholder]
    return store.add_record(rec, input_files, report_path, root)
```

Update `main()` to walk `eval_input/` after `fs_learning_inputs/`. Replace the existing `main()` with:

```python
def main() -> int:
    parser = argparse.ArgumentParser(description="Seed credit_datasets from credit_paper.")
    parser.add_argument(
        "--credit-paper",
        type=Path,
        required=True,
        help="Path to the credit_paper repo root",
    )
    parser.add_argument(
        "--reviewer",
        default="henry@anchorpointrisk.co.za",
        help="Reviewer email recorded on each new record",
    )
    args = parser.parse_args()

    fs = args.credit_paper / "data" / "fs_learning_inputs"
    eval_dir = args.credit_paper / "data" / "eval_input"
    report_inputs = args.credit_paper / "data" / "report_inputs"
    if not fs.exists():
        print(f"ERROR: not found: {fs}")
        return 1

    pairs = discover_pairs(fs)
    print(f"Found {len(pairs)} pairs in {fs}")

    created = 0
    skipped = 0
    for pair in pairs:
        result = migrate_pair(
            pair,
            report_inputs=report_inputs,
            root=None,
            reviewer=args.reviewer,
            ask=input,
        )
        if result is None:
            skipped += 1
            print(f"  skipped (already in dataset): {pair.company_name}")
        else:
            created += 1
            print(f"  added id={result.id}: {pair.company_name}")

    eval_reports = discover_eval_input_reports(eval_dir)
    print(f"\nFound {len(eval_reports)} reports in {eval_dir}")
    for report in eval_reports:
        result = migrate_eval_input(
            report,
            report_inputs=report_inputs,
            root=None,
            reviewer=args.reviewer,
            ask=input,
        )
        if result is None:
            skipped += 1
            print(f"  skipped: {report.name}")
        else:
            created += 1
            print(f"  added id={result.id}: {result.company_name}")

    report = store.validate()
    print(f"\nDone. Created {created}, skipped {skipped}. Validation issues: {len(report.issues)}")
    for issue in report.issues:
        print(f"  - {issue}")
    return 0 if report.is_clean else 2
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run pytest tests/test_migrate.py -v
```

Expected: 15 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/migrate_from_credit_paper.py tests/test_migrate.py
git commit -m "feat(migrate): handle eval_input/ reports + duplicate detection"
```

---

### Task 15: Run the migration end-to-end (operator task)

This task is not code — it is the operator running the seeding script against real data. Skip it during automated execution; the human operator runs it at a sensible time.

**Files:** none

- [ ] **Step 1: Back up current `credit_paper/data/` before running**

```powershell
Copy-Item -Recurse "C:\Users\APR\OneDrive - Anchor Point Risk (Pty) Ltd\Desktop\VS_CODE_REPOSITORY\credit_paper\data" "$env:USERPROFILE\Desktop\credit_paper_data_backup_2026-05-17"
```

- [ ] **Step 2: Run the migration**

```powershell
cd "C:\Users\APR\OneDrive - Anchor Point Risk (Pty) Ltd\Desktop\VS_CODE_REPOSITORY\credit_datasets"
uv run python scripts/migrate_from_credit_paper.py --credit-paper "..\credit_paper"
```

Expected: prompts for each pair; you fill in asset_class / sector / afs_years interactively. ~80 prompts.

- [ ] **Step 3: Verify**

```powershell
uv run python -c "from credit_datasets import load_records, validate; print(len(load_records())); print(validate())"
```

Expected: record count ≈ 80, validation report has zero issues (or only `notes`-flagged records with the markdown-fallback caveat).

- [ ] **Step 4: Commit nothing (data is gitignored)**

No git commit. OneDrive picks up the new files automatically.

---

## Phase 3 — `prompt_quality_lab` Dataset Manager page

### Task 16: Add `credit-datasets` as an editable dependency

**Files:**
- Modify: `prompt_quality_lab/pyproject.toml`

- [ ] **Step 1: Add the dep**

In `prompt_quality_lab/pyproject.toml`, add `"credit-datasets"` to `dependencies`:

```toml
dependencies = [
    "streamlit>=1.32",
    "anthropic>=0.40",
    "langchain>=0.3",
    "langchain-core>=0.3",
    "langchain-anthropic>=0.3",
    "python-dotenv>=1.0",
    "credit-datasets",
]

[tool.uv.sources]
credit-datasets = { path = "../credit_datasets", editable = true }
```

- [ ] **Step 2: Sync**

```bash
cd "C:\Users\APR\OneDrive - Anchor Point Risk (Pty) Ltd\Desktop\VS_CODE_REPOSITORY\prompt_quality_lab"
uv sync
```

Expected: `credit-datasets` resolved from the local path.

- [ ] **Step 3: Smoke-test the import**

```bash
uv run python -c "import credit_datasets as cd; print(cd.__version__)"
```

Expected: prints `0.1.0`.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "deps: add credit-datasets as editable local dep"
```

---

### Task 17: Convert `prompt_quality_lab` to multi-page

Streamlit auto-discovers `pages/`. Adding the directory and one file is enough; existing `streamlit_app.py` becomes the implicit home page.

**Files:**
- Create: `prompt_quality_lab/pages/1_Dataset_Manager.py`

- [ ] **Step 1: Create the page shim**

`prompt_quality_lab/pages/1_Dataset_Manager.py`:

```python
"""Streamlit auto-discovered page for the Dataset Manager."""

from prompt_quality_lab.dataset_manager.page import render

render()
```

- [ ] **Step 2: Create an empty dataset_manager package (stub `render`)**

`prompt_quality_lab/src/prompt_quality_lab/dataset_manager/__init__.py`:

```python
```

`prompt_quality_lab/src/prompt_quality_lab/dataset_manager/page.py`:

```python
"""Dataset Manager — Streamlit page composition."""

from __future__ import annotations

import streamlit as st


def render() -> None:
    st.set_page_config(page_title="Dataset Manager", layout="wide")
    st.title("Dataset Manager")
    st.info("Coming up in Task 18.")
```

- [ ] **Step 3: Smoke-test (manual)**

```bash
uv run streamlit run streamlit_app.py
```

Open `http://localhost:8501`. Verify:
- The home page (existing app) renders as before.
- The sidebar shows a "Dataset Manager" link.
- Clicking it shows the title + the "Coming up" info banner.

Stop the server (`Ctrl+C`).

- [ ] **Step 4: Commit**

```bash
git add pages/1_Dataset_Manager.py src/prompt_quality_lab/dataset_manager/__init__.py src/prompt_quality_lab/dataset_manager/page.py
git commit -m "feat(ui): scaffold Dataset Manager page (stub)"
```

---

### Task 18: Mode dispatch + dataset health expander

**Files:**
- Modify: `prompt_quality_lab/src/prompt_quality_lab/dataset_manager/page.py`

- [ ] **Step 1: Implement mode dispatch**

Replace `prompt_quality_lab/src/prompt_quality_lab/dataset_manager/page.py`:

```python
"""Dataset Manager — Streamlit page composition."""

from __future__ import annotations

import streamlit as st

from credit_datasets import validate


_MODE_BROWSE = "Browse"
_MODE_DETAIL = "Detail"
_MODE_ADD = "Add new record"


def _dataset_health() -> None:
    report = validate()
    label = "Dataset health" if report.is_clean else f"⚠ Dataset health ({len(report.issues)} issues)"
    with st.expander(label, expanded=not report.is_clean):
        if report.is_clean:
            st.success("No issues.")
        else:
            for issue in report.issues:
                st.write(f"- {issue}")


def render() -> None:
    st.set_page_config(page_title="Dataset Manager", layout="wide")
    st.title("Dataset Manager")

    _dataset_health()

    mode = st.radio(
        "Mode",
        options=[_MODE_BROWSE, _MODE_DETAIL, _MODE_ADD],
        horizontal=True,
        key="dm_mode",
    )

    if mode == _MODE_BROWSE:
        from prompt_quality_lab.dataset_manager.list_view import render_list
        render_list()
    elif mode == _MODE_DETAIL:
        from prompt_quality_lab.dataset_manager.detail_view import render_detail
        render_detail()
    elif mode == _MODE_ADD:
        from prompt_quality_lab.dataset_manager.add_view import render_add
        render_add()
```

Create placeholder modules so imports don't blow up:

`prompt_quality_lab/src/prompt_quality_lab/dataset_manager/list_view.py`:

```python
import streamlit as st


def render_list() -> None:
    st.write("Browse — coming in Task 19.")
```

`prompt_quality_lab/src/prompt_quality_lab/dataset_manager/detail_view.py`:

```python
import streamlit as st


def render_detail() -> None:
    st.write("Detail — coming in Task 20.")
```

`prompt_quality_lab/src/prompt_quality_lab/dataset_manager/add_view.py`:

```python
import streamlit as st


def render_add() -> None:
    st.write("Add — coming in Task 21.")
```

- [ ] **Step 2: Smoke test**

```bash
uv run streamlit run streamlit_app.py
```

Verify:
- Dataset health expander appears at top, showing "No issues" (or the issues, in red, if any exist).
- Radio with Browse / Detail / Add. Each selection shows its placeholder text.

- [ ] **Step 3: Commit**

```bash
git add src/prompt_quality_lab/dataset_manager/
git commit -m "feat(ui): mode dispatch + dataset health expander"
```

---

### Task 19: Browse view — table + filters

**Files:**
- Modify: `prompt_quality_lab/src/prompt_quality_lab/dataset_manager/list_view.py`
- Create: `prompt_quality_lab/tests/test_list_view_filters.py`

- [ ] **Step 1: Write the failing test for the pure filter helper**

`prompt_quality_lab/tests/test_list_view_filters.py`:

```python
from __future__ import annotations

from datetime import date

from credit_datasets.schema import AssetClass, QualityGrade, Record, Source

from prompt_quality_lab.dataset_manager.list_view import filter_records


def _r(**over) -> Record:
    base = dict(
        id="001",
        company_name="Acme Pty Ltd",
        asset_class=AssetClass.CORPORATE,
        sector="manufacturing",
        afs_years=[2023],
        date_added=date(2026, 5, 17),
        reviewer="x",
        quality_grade=QualityGrade.SILVER,
        source=Source.ANALYST_ORIGINAL,
        notes="",
    )
    base.update(over)
    return Record(**base)


def test_filter_no_criteria_returns_all() -> None:
    recs = [_r(id="001"), _r(id="002", company_name="Beta")]
    assert filter_records(recs, asset_classes=None, grades=None, search="") == recs


def test_filter_by_asset_class() -> None:
    recs = [
        _r(id="001", asset_class=AssetClass.CORPORATE),
        _r(id="002", asset_class=AssetClass.SME),
    ]
    result = filter_records(recs, asset_classes={AssetClass.SME}, grades=None, search="")
    assert [r.id for r in result] == ["002"]


def test_filter_by_grade() -> None:
    recs = [
        _r(id="001", quality_grade=QualityGrade.GOLD),
        _r(id="002", quality_grade=QualityGrade.SILVER),
    ]
    result = filter_records(recs, asset_classes=None, grades={QualityGrade.GOLD}, search="")
    assert [r.id for r in result] == ["001"]


def test_filter_by_search_company_case_insensitive() -> None:
    recs = [_r(id="001", company_name="Acme Pty"), _r(id="002", company_name="Beta")]
    assert [r.id for r in filter_records(recs, None, None, "ACME")] == ["001"]


def test_filter_by_search_sector_or_notes() -> None:
    recs = [
        _r(id="001", sector="manufacturing"),
        _r(id="002", sector="retail", notes="check ratios"),
    ]
    assert [r.id for r in filter_records(recs, None, None, "ratios")] == ["002"]
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run pytest tests/test_list_view_filters.py -v
```

Expected: ImportError on `filter_records`.

- [ ] **Step 3: Implement the filter helper + the view**

Replace `prompt_quality_lab/src/prompt_quality_lab/dataset_manager/list_view.py`:

```python
"""Browse view — table + filters."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from credit_datasets import load_records
from credit_datasets.schema import AssetClass, QualityGrade, Record


def filter_records(
    records: list[Record],
    asset_classes: set[AssetClass] | None,
    grades: set[QualityGrade] | None,
    search: str,
) -> list[Record]:
    """Pure filter — testable without Streamlit."""
    key = (search or "").strip().lower()
    out: list[Record] = []
    for r in records:
        if asset_classes and r.asset_class not in asset_classes:
            continue
        if grades and r.quality_grade not in grades:
            continue
        if key:
            haystack = " ".join([r.company_name, r.sector, r.notes]).lower()
            if key not in haystack:
                continue
        out.append(r)
    return out


def _to_dataframe(records: list[Record]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": r.id,
                "company_name": r.company_name,
                "asset_class": r.asset_class.value,
                "sector": r.sector,
                "quality_grade": r.quality_grade.value,
                "date_added": r.date_added.isoformat(),
                "reviewer": r.reviewer,
            }
            for r in records
        ]
    )


def render_list() -> None:
    st.subheader("Browse records")
    records = load_records()
    if not records:
        st.info("No records yet. Use the 'Add new record' mode to create one.")
        return

    col1, col2, col3 = st.columns([2, 2, 3])
    with col1:
        ac = st.multiselect(
            "Asset class",
            options=list(AssetClass),
            format_func=lambda a: a.value,
        )
    with col2:
        gr = st.multiselect(
            "Quality grade",
            options=list(QualityGrade),
            format_func=lambda g: g.value,
        )
    with col3:
        q = st.text_input("Search (company / sector / notes)")

    filtered = filter_records(
        records,
        asset_classes=set(ac) if ac else None,
        grades=set(gr) if gr else None,
        search=q,
    )
    st.caption(f"{len(filtered)} of {len(records)} records")
    st.dataframe(_to_dataframe(filtered), use_container_width=True, hide_index=True)
```

Note: this view does not implement "click row → switch to Detail mode" because Streamlit's basic `st.dataframe` doesn't expose click events cleanly. Detail mode (Task 20) uses a record-ID selector instead. Document this UX choice in the page if asked — it keeps the implementation simple and avoids `streamlit-aggrid`.

- [ ] **Step 4: Run pytest, then smoke**

```bash
uv run pytest tests/test_list_view_filters.py -v
uv run streamlit run streamlit_app.py
```

Expected: 5 tests pass. In the browser, Browse shows the empty-state message until a record is added.

- [ ] **Step 5: Commit**

```bash
git add src/prompt_quality_lab/dataset_manager/list_view.py tests/test_list_view_filters.py
git commit -m "feat(ui): browse view with filters and pure filter helper"
```

---

### Task 20: Detail view — view/edit form + file previews

**Files:**
- Modify: `prompt_quality_lab/src/prompt_quality_lab/dataset_manager/detail_view.py`

Streamlit-heavy module. No unit tests; covered by manual smoke.

- [ ] **Step 1: Implement the view**

Replace `prompt_quality_lab/src/prompt_quality_lab/dataset_manager/detail_view.py`:

```python
"""Detail view — view/edit a single record + file previews."""

from __future__ import annotations

from datetime import date

import streamlit as st

from credit_datasets import (
    dataset_root,
    delete_record,
    get_record,
    load_records,
    update_record,
)
from credit_datasets.schema import AssetClass, QualityGrade, Source


def render_detail() -> None:
    st.subheader("Record detail")
    records = load_records()
    if not records:
        st.info("No records yet.")
        return

    ids = [r.id for r in records]
    labels = {r.id: f"{r.id} — {r.company_name}" for r in records}
    selected_id = st.selectbox("Select record", options=ids, format_func=lambda i: labels[i])
    rec = get_record(selected_id)
    root = dataset_root()

    with st.form("edit_record"):
        company_name = st.text_input("Company name", value=rec.company_name)
        asset_class = st.selectbox(
            "Asset class",
            options=list(AssetClass),
            format_func=lambda a: a.value,
            index=list(AssetClass).index(rec.asset_class),
        )
        sector = st.text_input("Sector", value=rec.sector)
        afs_years_raw = st.text_input(
            "AFS years (comma-separated)",
            value=", ".join(str(y) for y in rec.afs_years),
        )
        date_added = st.date_input("Date added", value=rec.date_added)
        reviewer = st.text_input("Reviewer", value=rec.reviewer)
        quality_grade = st.selectbox(
            "Quality grade",
            options=list(QualityGrade),
            format_func=lambda g: g.value,
            index=list(QualityGrade).index(rec.quality_grade),
        )
        source = st.selectbox(
            "Source",
            options=list(Source),
            format_func=lambda s: s.value,
            index=list(Source).index(rec.source),
        )
        notes = st.text_area("Notes", value=rec.notes)
        confirm_save = st.checkbox("Confirm save")
        submitted = st.form_submit_button("Save changes", disabled=not confirm_save)

        if submitted:
            try:
                years = [int(y.strip()) for y in afs_years_raw.split(",") if y.strip()]
            except ValueError:
                st.error("AFS years must be comma-separated integers.")
            else:
                if isinstance(date_added, date):
                    update_record(
                        selected_id,
                        company_name=company_name,
                        asset_class=asset_class,
                        sector=sector,
                        afs_years=years,
                        date_added=date_added,
                        reviewer=reviewer,
                        quality_grade=quality_grade,
                        source=source,
                        notes=notes,
                    )
                    st.success(f"Saved {selected_id}")
                    st.rerun()

    st.divider()
    st.markdown("### Input files")
    for f in rec.input_files(root):
        col_a, col_b = st.columns([3, 1])
        col_a.write(f.name)
        col_b.download_button(
            "Download",
            data=f.read_bytes(),
            file_name=f.name,
            key=f"in_{f.name}",
        )

    st.markdown("### Gold report")
    gold = rec.gold_file(root)
    if gold is not None:
        st.download_button(
            "Download gold report",
            data=gold.read_bytes(),
            file_name=gold.name,
        )
        if gold.suffix.lower() == ".pdf":
            st.pdf(str(gold))  # Streamlit ≥ 1.40
    else:
        st.warning("No gold file found.")

    st.divider()
    st.markdown("### Delete")
    confirm_delete = st.checkbox(f"Confirm delete of {selected_id}")
    if st.button("Delete record", disabled=not confirm_delete, type="primary"):
        delete_record(selected_id)
        st.success(f"Deleted {selected_id}")
        st.rerun()
```

Note: `st.pdf` is available in Streamlit ≥ 1.40. If your installed version is older, fall back to a download-only experience (omit the `st.pdf` call) — bump `streamlit>=1.40` in `pyproject.toml` if you want the inline preview.

- [ ] **Step 2: Smoke test**

After completing Task 21 (Add) so there is a record to view, return here and exercise:
- selecting a record
- editing notes + quality_grade, ticking confirm save, saving
- downloading input files
- viewing gold PDF inline
- deleting a record with confirm checkbox

- [ ] **Step 3: Commit**

```bash
git add src/prompt_quality_lab/dataset_manager/detail_view.py
git commit -m "feat(ui): detail view with editable form + file preview"
```

---

### Task 21: Add view — upload + form

**Files:**
- Modify: `prompt_quality_lab/src/prompt_quality_lab/dataset_manager/add_view.py`

- [ ] **Step 1: Implement the view**

Replace `prompt_quality_lab/src/prompt_quality_lab/dataset_manager/add_view.py`:

```python
"""Add view — upload files and create a new record."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

import streamlit as st

from credit_datasets import add_record, dataset_root, next_id
from credit_datasets.schema import AssetClass, QualityGrade, Record, Source


def render_add() -> None:
    st.subheader("Add new record")

    suggested = next_id()
    new_id = st.text_input("ID (auto-suggested)", value=suggested)
    company_name = st.text_input("Company name")
    asset_class = st.selectbox(
        "Asset class",
        options=list(AssetClass),
        format_func=lambda a: a.value,
    )
    sector = st.text_input("Sector", placeholder="manufacturing")
    afs_years_raw = st.text_input("AFS years (comma-separated)", placeholder="2023, 2022, 2021")
    date_added = st.date_input("Date added", value=date.today())
    reviewer = st.text_input("Reviewer", value="henry@anchorpointrisk.co.za")
    quality_grade = st.selectbox(
        "Quality grade",
        options=list(QualityGrade),
        format_func=lambda g: g.value,
        index=list(QualityGrade).index(QualityGrade.SILVER),
    )
    source = st.selectbox(
        "Source",
        options=list(Source),
        format_func=lambda s: s.value,
    )
    notes = st.text_area("Notes")

    st.markdown("#### Files")
    input_uploads = st.file_uploader(
        "Input files (AFS PDFs + risk suite .xlsm)",
        type=["pdf", "xlsm", "xlsx"],
        accept_multiple_files=True,
    )
    gold_upload = st.file_uploader("Gold report (analyst PDF)", type=["pdf"])

    confirm = st.checkbox("Confirm create")
    if st.button("Save record", disabled=not confirm):
        # Validation
        errs: list[str] = []
        if not company_name.strip():
            errs.append("company_name is required")
        if not sector.strip():
            errs.append("sector is required")
        try:
            years = [int(y.strip()) for y in afs_years_raw.split(",") if y.strip()]
        except ValueError:
            years = []
            errs.append("AFS years must be comma-separated integers")
        if not input_uploads:
            errs.append("at least one input file is required")
        if gold_upload is None:
            errs.append("gold report is required")

        if errs:
            for e in errs:
                st.error(e)
            return

        # Write uploads to a temp dir so add_record can copy from real paths
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_paths: list[Path] = []
            for u in input_uploads:
                p = tmp_path / u.name
                p.write_bytes(u.getbuffer())
                input_paths.append(p)
            gold_path = tmp_path / gold_upload.name
            gold_path.write_bytes(gold_upload.getbuffer())

            rec = Record(
                id=new_id.strip(),
                company_name=company_name.strip(),
                asset_class=asset_class,
                sector=sector.strip(),
                afs_years=years,
                date_added=date_added if isinstance(date_added, date) else date.today(),
                reviewer=reviewer.strip(),
                quality_grade=quality_grade,
                source=source,
                notes=notes.strip(),
            )
            try:
                add_record(rec, input_paths, gold_path)
            except (ValueError, FileExistsError) as e:
                st.error(f"Could not save: {e}")
                return

        st.success(f"Created record {rec.id}: {rec.company_name}")
        st.rerun()
```

- [ ] **Step 2: Smoke test**

```bash
uv run streamlit run streamlit_app.py
```

Add a synthetic test record using small dummy PDFs. Verify it appears in Browse mode after refresh.

- [ ] **Step 3: Commit**

```bash
git add src/prompt_quality_lab/dataset_manager/add_view.py
git commit -m "feat(ui): add view with file uploads and validation"
```

---

### Task 22: End-to-end smoke verification

**Files:** none

- [ ] **Step 1: Start the app**

```bash
cd "C:\Users\APR\OneDrive - Anchor Point Risk (Pty) Ltd\Desktop\VS_CODE_REPOSITORY\prompt_quality_lab"
uv run streamlit run streamlit_app.py
```

- [ ] **Step 2: Exercise each mode against the migrated dataset**

Assuming Task 15 ran successfully:

- **Browse:** confirm ~80 records render. Apply each filter type. Confirm count caption updates.
- **Detail:** select a record. Confirm metadata form pre-fills correctly. Edit `notes`, tick "Confirm save", save. Re-select the same record and confirm the change persisted. Download an input file and the gold PDF. If on Streamlit ≥ 1.40, confirm the inline PDF preview renders.
- **Add:** create a synthetic record with throwaway PDFs. Confirm it appears in Browse. Switch to Detail, select it, tick "Confirm delete", delete. Confirm it's gone from Browse.

- [ ] **Step 3: Confirm dataset health stays clean**

The "Dataset health" expander at the top of the page should say "No issues" throughout. If it flags issues, investigate before declaring done.

- [ ] **Step 4: Final commit (only if there is anything to commit)**

```bash
cd "C:\Users\APR\OneDrive - Anchor Point Risk (Pty) Ltd\Desktop\VS_CODE_REPOSITORY\prompt_quality_lab"
git status
```

If clean, no commit needed. If there are minor fixups from smoke testing, commit them with `git commit -m "fix(ui): smoke-test follow-ups"`.

---

## Acceptance criteria recap (from spec §10)

- [ ] `credit_datasets/` exists with all listed files; `uv pip install -e .` clean; all unit tests pass (~40 tests across schema, store, paths, migrate, public_api).
- [ ] `prompt_quality_lab` has a working Dataset Manager page accessible from the sidebar; Browse, Detail, and Add modes all exercised end-to-end.
- [ ] Migration script has been run against `credit_paper/data/`; `manifest.json` has ≈80 records; `validate()` reports zero issues.
- [ ] Both `prompt_quality_lab` and (in a follow-up) `credit_paper` can import `credit_datasets` and read records.
