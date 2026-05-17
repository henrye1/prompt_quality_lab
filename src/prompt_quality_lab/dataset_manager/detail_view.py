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
