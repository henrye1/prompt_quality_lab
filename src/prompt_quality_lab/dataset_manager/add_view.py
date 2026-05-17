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
