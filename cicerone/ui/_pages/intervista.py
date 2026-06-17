"""Pagina intervista: una domanda per criterio, con clarification e parsing."""
from __future__ import annotations

import streamlit as st

from cicerone.ui._pages._shared import (
    get_criteri,
    header_cicerone,
    llm_intervista,
    repo,
    spinner_cicerone,
    vai_a,
)

MAX_CLARIFICATIONS_INTERVISTA = 2  # re-domande max per criterio (in aggiunta alla domanda iniziale)


def pagina_intervista() -> None:
    criteri = get_criteri()
    n = len(criteri)
    i = st.session_state.idx_criterio

    if i >= n:
        vai_a("vincitore")

    criterio = criteri[i]
    contesto = st.session_state.contesto_azienda
    criterio_id = criterio["idCriterio"]

    header_cicerone()
    st.subheader(f"Criterio {i+1}/{n} — {criterio['nomeCriterio']}")
    with st.expander("Definizione", expanded=False):
        st.write(criterio["definizione"])

    if llm_intervista is None:
        st.error("Modulo intervista LLM non disponibile.")
        return

    chat_per_criterio: dict = st.session_state.intervista_chat
    history: list = chat_per_criterio.setdefault(criterio_id, [])

    # Genera domanda iniziale quando entri nel criterio per la prima volta
    if st.session_state.intervista_idx_corrente != i or st.session_state.intervista_domanda_corrente is None:
        if not history:
            with spinner_cicerone("Sto formulando la domanda adatta al tuo contesto..."):
                domanda_iniziale = llm_intervista.domanda_per_criterio(criterio, contesto)
            history.append({"role": "assistant", "content": domanda_iniziale, "kind": "domanda"})
            st.session_state.intervista_domanda_corrente = domanda_iniziale
        else:
            # Ripristino: usa l'ultima domanda dell'assistente in history
            domande = [m for m in history if m["role"] == "assistant"]
            st.session_state.intervista_domanda_corrente = domande[-1]["content"] if domande else None
        st.session_state.intervista_idx_corrente = i
        st.session_state.intervista_ultima_parsed = None

    # Render chat history del criterio
    for msg in history:
        with st.chat_message(msg["role"]):
            if msg.get("kind") == "approfondimento":
                st.markdown(f"_Approfondimento_ — {msg['content']}")
            else:
                st.markdown(msg["content"])

    # Mostra parsing inferito (trasparenza) — visibile solo per il criterio appena chiuso
    if st.session_state.intervista_ultima_parsed:
        p = st.session_state.intervista_ultima_parsed
        livello_label = f"**Livello inferito:** {p['livello']} (peso {p['peso']})"
        if p["ambiguo"]:
            st.warning(f"{livello_label} — risposta giudicata ambigua dal modello.")
        else:
            st.success(livello_label)

    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("← Indietro", disabled=(i == 0), key=f"back_{i}"):
            st.session_state.idx_criterio = max(0, i - 1)
            st.session_state.intervista_domanda_corrente = None
            st.rerun()

    placeholder = (
        "Vai al calcolo: scrivi la tua ultima risposta..."
        if i == n - 1 else
        "Scrivi la tua risposta e premi Invio"
    )
    risposta = st.chat_input(placeholder)

    if risposta and risposta.strip():
        risposta_clean = risposta.strip()
        history.append({"role": "user", "content": risposta_clean})

        clarif_count = st.session_state.intervista_clarif_count.get(criterio_id, 0)
        # is_retry forza ramo B (parse anche se vago) all'ULTIMO tentativo permesso
        is_retry = clarif_count >= MAX_CLARIFICATIONS_INTERVISTA

        with spinner_cicerone("Sto interpretando la tua risposta..."):
            parsed = llm_intervista.parse_risposta(
                criterio, contesto, risposta_clean, is_retry=is_retry
            )

        # Clarification ammessa finché count < MAX
        if parsed.get("needs_clarification") and clarif_count < MAX_CLARIFICATIONS_INTERVISTA:
            st.session_state.intervista_clarif_count[criterio_id] = clarif_count + 1
            nuova_domanda = (
                parsed.get("clarification_question")
                or "Puoi spiegare meglio cosa intendi? Anche un esempio concreto va bene."
            )
            history.append({"role": "assistant", "content": nuova_domanda, "kind": "approfondimento"})
            st.session_state.intervista_domanda_corrente = nuova_domanda
            st.session_state.intervista_ultima_parsed = None
            st.rerun()

        # Salva e procedi (ramo B accettato, eventualmente con ambiguo=True)
        st.session_state.intervista_ultima_parsed = parsed
        repo.salva_peso(
            assessment_id=st.session_state.assessment_id,
            criterio_id=criterio_id,
            livello=parsed.get("livello", "Abbastanza importante"),
            peso=parsed.get("peso", 5.0),
            motivazione=parsed.get("motivazione") or risposta_clean,
            trascrizione=risposta_clean,
            ambiguo=parsed.get("ambiguo", False),
        )
        st.session_state.idx_criterio = i + 1
        st.session_state.intervista_domanda_corrente = None
        if st.session_state.idx_criterio >= n:
            vai_a("vincitore")
        else:
            st.rerun()
