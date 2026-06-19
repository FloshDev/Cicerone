"""Pagina diagnostica: domande guidate generate dall'LLM."""
from __future__ import annotations

import streamlit as st

from cicerone.ui._pages._shared import (
    llm_diag,
    llm_guard,
    repo,
    spinner_cicerone,
    vai_a,
    wizard_header,
)


def pagina_diagnostica() -> None:
    assessment_id = st.session_state.assessment_id

    wizard_header("diagnostica")
    st.caption("Rispondi alle domande per personalizzare il report finale.")

    storia = repo.storia_diagnostica(assessment_id)
    for qa in storia:
        with st.chat_message("assistant"):
            etichetta = "**Approfondimento** — " if qa.get("is_riask") else ""
            st.markdown(f"{etichetta}{qa['domanda']}")
        with st.chat_message("user"):
            st.markdown(qa["risposta_utente"])

    if st.session_state.diag_domanda_corrente is None:
        with llm_guard(), spinner_cicerone("Sto generando la prossima domanda..."):
            st.session_state.diag_domanda_corrente = llm_diag.next_question(assessment_id)

    domanda = st.session_state.diag_domanda_corrente
    if domanda is None:
        st.success("Diagnostica completata.")
        if st.button("Genera il report →", type="primary"):
            vai_a("report")
        return

    with st.chat_message("assistant"):
        st.markdown(domanda)

    risposta = st.chat_input("Scrivi la tua risposta e premi Invio")

    if risposta and risposta.strip():
        with st.chat_message("user"):
            st.markdown(risposta)
        with llm_guard(), spinner_cicerone("Sto interpretando la tua risposta..."):
            prossima = llm_diag.next_question(
                assessment_id,
                domanda_precedente=domanda,
                risposta_precedente=risposta.strip(),
            )
        st.session_state.diag_domanda_corrente = prossima
        st.rerun()
