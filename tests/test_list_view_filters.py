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
