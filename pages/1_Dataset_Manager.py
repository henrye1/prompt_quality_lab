"""Streamlit auto-discovered page for the Dataset Manager."""

import streamlit as st

try:
    from prompt_quality_lab.dataset_manager.page import render
except ImportError as e:
    st.set_page_config(page_title="Dataset Manager", page_icon="📚", layout="wide")
    st.title("📚 Dataset Manager")
    st.warning(
        "The Dataset Manager requires the optional **`credit-datasets`** package, "
        "which is not installed in this deployment.\n\n"
        "To enable it locally, run:\n\n"
        "```\nuv sync --extra dataset-manager\n```"
    )
    with st.expander("Technical details"):
        st.code(str(e))
    st.stop()

render()
