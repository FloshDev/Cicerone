"""Pagina report: generazione e download del report finale markdown."""
from __future__ import annotations

import streamlit as st

from cicerone.ui._pages._shared import (
    CHIAVI_RESET,
    llm_guard,
    llm_report,
    spinner_cicerone,
    wizard_header,
)


def pagina_report() -> None:
    assessment_id = st.session_state.assessment_id
    wizard_header("report")

    if st.session_state.report_markdown is None:
        with llm_guard(), spinner_cicerone(
            "Sto preparando il report finale, possono volerci 20-30 secondi..."
        ):
            st.session_state.report_markdown = llm_report.genera_report(assessment_id)

    markdown = st.session_state.report_markdown
    st.markdown(markdown)

    st.divider()
    col_dl, col_new = st.columns(2)
    with col_dl:
        st.download_button(
            "Scarica report .md",
            markdown,
            file_name=f"report_cicerone_{assessment_id}.md",
            mime="text/markdown",
            type="primary",
        )
    with col_new:
        if st.button("Nuovo assessment"):
            for k in CHIAVI_RESET:
                st.session_state.pop(k, None)
            st.rerun()
