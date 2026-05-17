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
