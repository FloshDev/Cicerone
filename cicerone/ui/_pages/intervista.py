"""Pagina intervista: una domanda per criterio, con decisione guidata dal
modello (chiudi / approfondisci / spiega) turno per turno."""
from __future__ import annotations

import html

import streamlit as st

from cicerone.ui._pages._shared import (
    get_criteri,
    llm_guard,
    llm_intervista,
    repo,
    spinner_cicerone,
    vai_a,
    wizard_header,
)

# Paracadute (NON target): cap morbido sulle risposte valutabili per criterio.
# Al raggiungimento, la risposta successiva forza la chiusura del modello.
MAX_RISPOSTE_VALUTATE = 3
# Soffitto assoluto anti-runaway: numero massimo di turni LLM per criterio,
# solo protezione anti-loop.
HARD_CEILING_TURNI = 10


def pagina_intervista() -> None:
    criteri = get_criteri()
    n = len(criteri)
    i = st.session_state.idx_criterio

    if i >= n:
        vai_a("vincitore")

    criterio = criteri[i]
    contesto = st.session_state.contesto_azienda
    criterio_id = criterio["idCriterio"]

    wizard_header(
        "intervista",
        sub=(
            f'<span class="cic-crit-count">Criterio {i+1} di {n}</span>'
            f'<span class="cic-crit-name">{html.escape(criterio["nomeCriterio"])}</span>'
        ),
    )
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
            with llm_guard(), spinner_cicerone("Sto formulando la domanda adatta al tuo contesto..."):
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
            kind = msg.get("kind")
            if kind == "approfondimento":
                st.markdown(f"_Approfondimento_ — {msg['content']}")
            elif kind == "spiegazione":
                st.markdown(f"_Chiarimento_ — {msg['content']}")
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

        n_valutate = st.session_state.intervista_risposte_valutate.get(criterio_id, 0)
        n_turni = st.session_state.intervista_turni_llm.get(criterio_id, 0)

        # Paracadute: forza chiusura se raggiunti i cap (non sono target).
        forza = (
            n_valutate >= MAX_RISPOSTE_VALUTATE
            or n_turni >= HARD_CEILING_TURNI
        )

        with llm_guard(), spinner_cicerone("Sto interpretando la tua risposta..."):
            esito = llm_intervista.valuta_turno(
                criterio, contesto, history, n_valutate, forza_chiusura=forza
            )
        st.session_state.intervista_turni_llm[criterio_id] = n_turni + 1

        azione = esito.get("azione")

        if azione == "spiega":
            spiegazione = esito.get("spiegazione", "")
            nuova_domanda = esito.get("domanda", "")
            contenuto = f"{spiegazione}\n\n{nuova_domanda}".strip() if spiegazione else nuova_domanda
            history.append({
                "role": "assistant",
                "content": contenuto,
                "kind": "spiegazione",
            })
            st.session_state.intervista_domanda_corrente = nuova_domanda or contenuto
            st.session_state.intervista_ultima_parsed = None
            # "spiega" NON incrementa il contatore risposte valutabili.
            st.rerun()

        if azione == "approfondisci":
            nuova_domanda = (
                esito.get("domanda")
                or "Puoi farmi un esempio concreto?"
            )
            history.append({
                "role": "assistant",
                "content": nuova_domanda,
                "kind": "approfondimento",
            })
            st.session_state.intervista_domanda_corrente = nuova_domanda
            st.session_state.intervista_ultima_parsed = None
            st.session_state.intervista_risposte_valutate[criterio_id] = n_valutate + 1
            st.rerun()

        # azione == "chiudi": salva e procedi.
        st.session_state.intervista_risposte_valutate[criterio_id] = n_valutate + 1
        parsed = {
            "livello": esito.get("livello", "Abbastanza importante"),
            "peso": esito.get("peso", 5.0),
            "motivazione": esito.get("motivazione") or risposta_clean,
            "ambiguo": esito.get("ambiguo", False),
        }
        st.session_state.intervista_ultima_parsed = parsed
        repo.salva_peso(
            assessment_id=st.session_state.assessment_id,
            criterio_id=criterio_id,
            livello=parsed["livello"],
            peso=parsed["peso"],
            motivazione=parsed["motivazione"],
            trascrizione=risposta_clean,
            ambiguo=parsed["ambiguo"],
        )
        st.session_state.idx_criterio = i + 1
        st.session_state.intervista_domanda_corrente = None
        if st.session_state.idx_criterio >= n:
            vai_a("vincitore")
        else:
            st.rerun()
