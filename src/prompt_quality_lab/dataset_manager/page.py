"""Dataset Manager — Streamlit page composition."""

from __future__ import annotations

import streamlit as st


def render() -> None:
    st.set_page_config(page_title="Dataset Manager", layout="wide")
    st.title("Dataset Manager")
    st.info("Coming up in Task 18.")
