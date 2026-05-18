"""Tests for the dataset bridge — converts credit_datasets Records to prompt dicts."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from credit_datasets.schema import AssetClass, QualityGrade, Record, Source
from prompt_quality_lab.dataset_bridge import record_to_prompt, records_to_prompts


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "records").mkdir()
    return tmp_path


def _record(id_: str = "001", company: str = "Acme") -> Record:
    return Record(
        id=id_,
        company_name=company,
        asset_class=AssetClass.CORPORATE,
        sector="manufacturing",
        afs_years=[2024],
        date_added=date(2026, 1, 1),
        reviewer="henry",
        quality_grade=QualityGrade.GOLD,
        source=Source.ANALYST_ORIGINAL,
    )


def _seed_record_files(root: Path, rec: Record, inputs: dict[str, str], gold: str | None) -> None:
    rec_dir = rec.record_dir(root)
    inputs_dir = rec.inputs_dir(root)
    inputs_dir.mkdir(parents=True)
    for name, content in inputs.items():
        (inputs_dir / name).write_text(content, encoding="utf-8")
    if gold is not None:
        gold_dir = rec.gold_dir(root)
        gold_dir.mkdir(parents=True)
        (gold_dir / "gold.txt").write_text(gold, encoding="utf-8")
    assert rec_dir.exists()


def test_record_with_inputs_and_gold(root: Path):
    rec = _record()
    _seed_record_files(
        root,
        rec,
        inputs={"a.txt": "input one"},
        gold="the expected answer",
    )
    out = record_to_prompt(rec, root)
    assert out == {
        "id": "001",
        "prompt": "input one",
        "expected_output": "the expected answer",
        "source": "dataset:001",
    }


def test_record_concatenates_multiple_input_files(root: Path):
    rec = _record()
    _seed_record_files(
        root,
        rec,
        inputs={"a.txt": "first", "b.txt": "second"},
        gold=None,
    )
    out = record_to_prompt(rec, root)
    assert "first" in out["prompt"]
    assert "second" in out["prompt"]
    assert "---" in out["prompt"]  # separator
    assert out["expected_output"] == ""


def test_record_with_no_gold_leaves_expected_empty(root: Path):
    rec = _record()
    _seed_record_files(root, rec, inputs={"a.txt": "x"}, gold=None)
    out = record_to_prompt(rec, root)
    assert out["expected_output"] == ""


def test_records_to_prompts_drops_records_with_no_input_text(root: Path):
    good = _record(id_="001", company="Has Files")
    empty = _record(id_="002", company="No Files")
    _seed_record_files(root, good, inputs={"a.txt": "content"}, gold=None)
    # empty record: create the record dir but no inputs folder
    empty.record_dir(root).mkdir(parents=True)

    out = records_to_prompts([good, empty], root)
    assert len(out) == 1
    assert out[0]["id"] == "001"
