"""Manifest-backed CRUD over the dataset folder."""

from __future__ import annotations

import dataclasses
import json
import shutil
from datetime import date
from pathlib import Path

from credit_datasets import paths
from credit_datasets.schema import AssetClass, QualityGrade, Record, Source, ValidationReport


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
