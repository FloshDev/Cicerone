"""Pagina onboarding: profilo azienda + configurazione/verifica API key."""
from __future__ import annotations

import streamlit as st

from cicerone.ui._pages._shared import (
    SHEET,
    _idx_o_default,
    complete,
    repo,
    salva_contesto,
    set_api_key,
    set_model,
    spinner_cicerone,
    vai_a,
    wizard_header,
)

SETTORI = [
    "Manifatturiero",
    "Servizi professionali",
    "Commercio / Retail",
    "Edilizia",
    "Logistica e trasporti",
    "Agroalimentare",
    "ICT / Software",
    "Sanità",
    "Turismo / Ospitalità",
    "Altro",
]
FASCE_DIPENDENTI = ["1-9", "10-49", "50-249", "250+"]
FASCE_FATTURATO = ["< 500k €", "500k - 2M €", "2M - 10M €", "10M - 50M €", "> 50M €"]
USO_AI_OPZIONI = ["No", "Sì, in modo sporadico", "Sì, in modo strutturato"]
NAZIONI_EUROPA = [
    "Austria", "Belgio", "Bulgaria", "Cechia", "Cipro", "Croazia",
    "Danimarca", "Estonia", "Finlandia", "Francia", "Germania", "Grecia",
    "Irlanda", "Italia", "Lettonia", "Lituania", "Lussemburgo", "Malta",
    "Paesi Bassi", "Polonia", "Portogallo", "Regno Unito", "Romania",
    "Slovacchia", "Slovenia", "Spagna", "Svezia", "Svizzera", "Ungheria",
]


def verifica_chiave(api_key: str, model: str) -> tuple[bool, str]:
    """Test minimo con call di 10 token al modello scelto — costo trascurabile."""
    set_api_key(api_key)
    set_model(model)
    try:
        complete(system="", messages=[{"role": "user", "content": "ping"}], max_tokens=10)
        return True, "Chiave valida."
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:200]}"


def blocco_api_key() -> None:
    st.markdown('<div class="cic-card-header">Configurazione</div>', unsafe_allow_html=True)
    model = st.text_input(
        "Modello",
        value=st.session_state.model,
        placeholder="anthropic/claude-sonnet-4-6",
        help=(
            "Stringa modello in formato litellm. Esempi: "
            "`anthropic/claude-sonnet-4-6`, `openai/gpt-4o`, "
            "`gemini/gemini-2.0-flash`."
        ),
    )
    api_key = st.text_input(
        "API Key",
        type="password",
        value=st.session_state.api_key,
        placeholder="La chiave del provider scelto",
        help="Necessaria per intervista, diagnostica e report. Non viene salvata su disco.",
    )

    col_btn, col_msg = st.columns([1, 3], vertical_alignment="center")
    with col_btn:
        verifica_clicked = st.button("Verifica chiave", type="primary", disabled=not api_key.strip())

    if verifica_clicked:
        with spinner_cicerone("Verifico la chiave..."):
            ok, msg = verifica_chiave(api_key.strip(), model.strip())
        st.session_state.api_key = api_key.strip()
        st.session_state.model = model.strip()
        st.session_state.api_key_valida = ok
        st.session_state.api_key_messaggio = msg
        st.rerun()
    elif api_key and api_key.strip() != st.session_state.api_key:
        st.session_state.api_key = api_key.strip()
        st.session_state.model = model.strip()
        st.session_state.api_key_valida = None
        st.session_state.api_key_messaggio = ""
        set_api_key(api_key.strip())
        set_model(model.strip())
    elif api_key:
        set_api_key(api_key.strip())
        set_model(model.strip())

    with col_msg:
        if st.session_state.api_key_valida is True:
            st.markdown(
                f'<div class="cic-key-ok">✓ {st.session_state.api_key_messaggio}</div>',
                unsafe_allow_html=True,
            )
        elif st.session_state.api_key_valida is False:
            st.markdown(
                f'<div class="cic-key-ko">✗ {st.session_state.api_key_messaggio}</div>',
                unsafe_allow_html=True,
            )


def pagina_onboarding() -> None:
    wizard_header("onboarding")

    with st.container(border=True):
        blocco_api_key()

    ctx = st.session_state.contesto_azienda or {}

    with st.container(border=True):
        st.markdown('<div class="cic-card-header">Profilo dell\'azienda</div>', unsafe_allow_html=True)
        st.caption("I dati restano locali; servono al modello per adattare l'intervista al tuo contesto.")

        with st.form("onboarding"):
            r1_a, r1_b = st.columns(2)
            with r1_a:
                nome_azienda = st.text_input(
                    "Nome azienda",
                    value=ctx.get("nome_azienda", ""),
                    placeholder="Es. Acme S.r.l.",
                )
            with r1_b:
                settore = st.selectbox(
                    "Settore", SETTORI,
                    index=_idx_o_default(SETTORI, ctx.get("settore"), "Manifatturiero"),
                )

            r2_a, r2_b = st.columns(2)
            with r2_a:
                nazione = st.selectbox(
                    "Nazione", NAZIONI_EUROPA,
                    index=_idx_o_default(NAZIONI_EUROPA, ctx.get("nazione"), "Italia"),
                )
            with r2_b:
                regione = st.text_input(
                    "Regione / Cantone / Stato — opzionale",
                    value=ctx.get("regione") or "",
                    placeholder="Es. Lombardia, Vaud, Bayern...",
                )

            r3_a, r3_b = st.columns(2)
            with r3_a:
                dipendenti = st.selectbox(
                    "Numero di dipendenti", FASCE_DIPENDENTI,
                    index=_idx_o_default(FASCE_DIPENDENTI, ctx.get("fascia_dipendenti"), "10-49"),
                )
            with r3_b:
                fatturato = st.selectbox(
                    "Fascia di fatturato annuo", FASCE_FATTURATO,
                    index=_idx_o_default(FASCE_FATTURATO, ctx.get("fascia_fatturato"), "500k - 2M €"),
                )

            note = st.text_area(
                "Note aggiuntive (opzionale)",
                value=ctx.get("note") or "",
                placeholder="Es. processo principale, mercato, vincoli...",
            )
            gia_usa_ai = st.radio(
                "L'azienda utilizza già strumenti AI?",
                USO_AI_OPZIONI,
                index=_idx_o_default(USO_AI_OPZIONI, ctx.get("uso_ai_attuale"), "No"),
            )

            chiave_ok = st.session_state.api_key_valida is True
            submitted = st.form_submit_button(
                "Avvia intervista",
                type="primary",
                disabled=not chiave_ok,
            )

    if not chiave_ok:
        st.info("Verifica prima la API key per abilitare l'avvio dell'intervista.")

    if submitted and not nome_azienda.strip():
        st.error("Inserisci il nome dell'azienda per proseguire.")
        return

    if submitted and chiave_ok and nome_azienda.strip():
        nuovo_contesto = {
            "nome_azienda": nome_azienda.strip(),
            "settore": settore,
            "fascia_dipendenti": dipendenti,
            "nazione": nazione,
            "regione": regione.strip() or None,
            "uso_ai_attuale": gia_usa_ai,
            "fascia_fatturato": fatturato,
            "note": note.strip() or None,
        }
        st.session_state.contesto_azienda = nuovo_contesto
        # Crea un nuovo assessment SOLO se non c'è ancora uno attivo
        # (tornando indietro dall'intervista NON vogliamo invalidare il lavoro fatto)
        if st.session_state.assessment_id is None:
            st.session_state.assessment_id = repo.crea_assessment(SHEET)
            st.session_state.idx_criterio = 0
        salva_contesto(st.session_state.assessment_id, nuovo_contesto)
        vai_a("intervista")
