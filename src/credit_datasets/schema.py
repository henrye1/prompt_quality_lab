"""Types for the golden labelled dataset."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path


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


@dataclass(frozen=True)
class ValidationReport:
    issues: list[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return not self.issues

