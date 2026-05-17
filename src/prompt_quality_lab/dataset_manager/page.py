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
