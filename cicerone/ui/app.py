"""UI Streamlit per Cicerone.

Avvio:
    uv run streamlit run cicerone/ui/app.py
"""
from __future__ import annotations

import streamlit as st

from cicerone.db import seed
from cicerone.db.connection import get_connection

# IMPORTANTE — ordine bootstrap schema (FRAGILE):
# `cicerone.ui._pages._shared` esegue `_bootstrap_schema_eager()` in cima al
# modulo, PRIMA di importare `repository` (che al load esegue una migration
# ALTER TABLE che esplode su DB fresco). Importando `_shared` per primo qui
# garantiamo che il bootstrap giri una sola volta prima di qualsiasi import di
# repository fatto dalle pagine.
from cicerone.ui._pages import _shared  # noqa: F401  (import per side-effect bootstrap)
from cicerone.ui._pages._shared import (
    CHIAVI_RESET,
    FASI,
    LOGO_PATH,
    ROMANI,
    get_criteri,
    inject_style,
    set_api_key,
)
from cicerone.ui._pages.diagnostica import pagina_diagnostica
from cicerone.ui._pages.intervista import pagina_intervista
from cicerone.ui._pages.onboarding import pagina_onboarding
from cicerone.ui._pages.report import pagina_report
from cicerone.ui._pages.vincitore import pagina_vincitore
from cicerone.version_check import check_for_update

# ---------- stato ----------

def init_state() -> None:
    st.session_state.setdefault("step", "onboarding")
    st.session_state.setdefault("contesto_azienda", None)
    st.session_state.setdefault("assessment_id", None)
    st.session_state.setdefault("criteri", None)
    st.session_state.setdefault("idx_criterio", 0)
    st.session_state.setdefault("intervista_domanda_corrente", None)
    st.session_state.setdefault("intervista_idx_corrente", None)
    st.session_state.setdefault("intervista_ultima_parsed", None)
    st.session_state.setdefault("intervista_clarif_count", {})
    st.session_state.setdefault("intervista_chat", {})
    st.session_state.setdefault("diag_domanda_corrente", None)
    st.session_state.setdefault("report_markdown", None)
    st.session_state.setdefault("api_key", "")
    st.session_state.setdefault("api_key_valida", None)
    st.session_state.setdefault("api_key_messaggio", "")
    st.session_state.setdefault("fasi_raggiunte", {"onboarding"})


def reset_dati_utente() -> int:
    """Cancella dati assessment dell'utente preservando seed (criteri/framework/voti).

    Ritorna il numero di assessment cancellati prima del wipe.
    """
    with get_connection() as conn:
        n = conn.execute("SELECT COUNT(*) FROM Assessment").fetchone()[0]
        conn.executescript(
            """
            DELETE FROM Diagnostica;
            DELETE FROM peso_assessment;
            DELETE FROM Assessment;
            """
        )
        conn.commit()
    return int(n)


# ---------- sidebar ----------

@st.cache_data(ttl=3600, show_spinner=False)
def _check_aggiornamento_cached() -> dict:
    """Wrapper cached: 1 chiamata GitHub API per ora, niente al primo rerun."""
    return check_for_update()


def banner_aggiornamento() -> None:
    """Banner discreto se una release più recente è disponibile su GitHub.

    Silenzioso se: offline, errore API, già aggiornato. Cache 1h così non
    bombarda l'API ad ogni rerun di Streamlit.
    """
    info = _check_aggiornamento_cached()
    if not info.get("has_update"):
        return
    latest = info.get("latest")
    url = info.get("url") or "https://github.com/FloshDev/Cicerone/releases"
    st.sidebar.markdown(
        f'<div class="cic-update-banner">'
        f'<div class="cic-update-title">Aggiornamento disponibile</div>'
        f'<div class="cic-update-version">v{latest}</div>'
        f'<a class="cic-update-link" href="{url}" target="_blank" rel="noopener">'
        f'Scarica la nuova release</a>'
        f'</div>',
        unsafe_allow_html=True,
    )


def sidebar_stepper() -> None:
    step = st.session_state.step

    if LOGO_PATH.exists():
        col_l, col_c, col_r = st.sidebar.columns([1, 2, 1])
        with col_c:
            st.image(str(LOGO_PATH), use_container_width=True)

    st.sidebar.markdown(
        '<div class="cic-sidebar-title">Cicerone</div>'
        '<div class="cic-sidebar-caption">Assessment AI Readiness</div>',
        unsafe_allow_html=True,
    )

    banner_aggiornamento()

    # Badge stato chiave API
    stato = st.session_state.api_key_valida
    if stato is True:
        badge = '<span class="cic-badge cic-badge-ok">chiave OK</span>'
    elif stato is False:
        badge = '<span class="cic-badge cic-badge-ko">chiave non valida</span>'
    else:
        badge = '<span class="cic-badge cic-badge-idle">chiave non verificata</span>'
    st.sidebar.markdown(f"API key: {badge}", unsafe_allow_html=True)

    st.sidebar.markdown('<div class="cic-divider">─── · ───</div>', unsafe_allow_html=True)

    raggiunte = st.session_state.get("fasi_raggiunte", {"onboarding"})
    fasi_keys = [k for k, _ in FASI]
    current_idx = fasi_keys.index(step) if step in fasi_keys else 0
    for n, (key, label) in enumerate(FASI):
        # Sbloccata se: fase precedente alla corrente (back-nav libera)
        # oppure già visitata in passato.
        sbloccata = n <= current_idx or key in raggiunte
        attivo = key == step
        marker = "●" if attivo else " "
        button_label = f"{marker}  {ROMANI[n]}   {label}"
        if st.sidebar.button(
            button_label,
            key=f"nav_{key}",
            disabled=(not sbloccata) or attivo,
            use_container_width=True,
        ):
            st.session_state.step = key
            st.rerun()

    if step == "intervista":
        criteri = get_criteri()
        n_crit = len(criteri)
        i = min(st.session_state.idx_criterio, n_crit)
        st.sidebar.markdown('<div class="cic-divider">─── · ───</div>', unsafe_allow_html=True)
        st.sidebar.progress(i / n_crit if n_crit else 0, text=f"Criterio {min(i+1, n_crit)}/{n_crit}")

    st.sidebar.markdown('<div class="cic-divider">─── · ───</div>', unsafe_allow_html=True)
    if st.sidebar.button("Ricomincia", key="sidebar_restart"):
        for k in CHIAVI_RESET:
            st.session_state.pop(k, None)
        st.rerun()

    with st.sidebar.expander("Manutenzione", expanded=False):
        st.caption(
            "Resetta tutti i dati di assessment per testare l'app su una nuova PMI. "
            "Criteri e framework restano (sono dati di riferimento)."
        )
        conferma = st.checkbox("Confermo: cancella tutti gli assessment", key="cic_reset_conferma")
        if st.button(
            "Nuova PMI — pulizia dati",
            key="sidebar_reset_db",
            disabled=not conferma,
            use_container_width=True,
        ):
            cancellati = reset_dati_utente()
            for k in CHIAVI_RESET:
                st.session_state.pop(k, None)
            st.session_state.pop("cic_reset_conferma", None)
            st.toast(f"DB ripulito ({cancellati} assessment cancellati).")
            st.rerun()


# ---------- entry point ----------

def main() -> None:
    page_icon = str(LOGO_PATH) if LOGO_PATH.exists() else None
    st.set_page_config(page_title="Cicerone", page_icon=page_icon, layout="centered")
    inject_style()
    seed.run_if_needed()
    init_state()
    sidebar_stepper()

    if st.session_state.api_key and st.session_state.api_key_valida:
        set_api_key(st.session_state.api_key)

    step = st.session_state.step
    if step == "onboarding":
        pagina_onboarding()
    elif step == "intervista":
        pagina_intervista()
    elif step == "vincitore":
        pagina_vincitore()
    elif step == "diagnostica":
        pagina_diagnostica()
    elif step == "report":
        pagina_report()
    else:
        st.error(f"Stato sconosciuto: {step}")


main()
