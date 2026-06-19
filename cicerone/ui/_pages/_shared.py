"""Costanti, helper e import "pesanti" condivisi dalle pagine Cicerone.

IMPORTANTE — ordine bootstrap schema (FRAGILE):
Il bootstrap schema (`_bootstrap_schema_eager`) DEVE girare PRIMA di importare
`repository`: repository.py esegue una migration ALTER TABLE al load del modulo,
che esplode su DB fresco senza tabelle. Per questo il bootstrap è in cima a
questo modulo, prima di qualsiasi import di `repository`. Tutte le pagine
importano `repo` (e gli altri moduli pesanti) DA QUI, così il bootstrap gira
una sola volta prima di ogni import di repository.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import streamlit as st

from cicerone.db.connection import get_connection

# Bootstrap schema PRIMA di importare repository: repository.py esegue una
# migration ALTER TABLE al load del modulo, che esplode su DB fresco senza
# tabelle. Applichiamo schema.sql qui per garantire l'invariante.
_SCHEMA_SQL = Path(__file__).parent.parent.parent / "db" / "schema.sql"


def _bootstrap_schema_eager() -> None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='Sheet'"
        ).fetchone()
        if row:
            return
        conn.executescript(_SCHEMA_SQL.read_text(encoding="utf-8"))
        conn.commit()


_bootstrap_schema_eager()

from cicerone.db import repository as repo  # noqa: E402  (import dopo bootstrap)
from cicerone.llm import diagnostica as llm_diag  # noqa: E402
from cicerone.llm import intervista as llm_intervista  # noqa: E402
from cicerone.llm import report as llm_report  # noqa: E402
from cicerone.llm._client import complete, set_api_key, set_model  # noqa: E402
from cicerone.mcda import calcolo as mcda  # noqa: E402

salva_contesto = repo.salva_contesto

STYLE_CSS = Path(__file__).parent.parent / "style.css"
LOGO_PATH = Path(__file__).parent.parent.parent.parent / "resources" / "branding" / "logo.png"

SHEET = "rediness"

TAGLINE = "La voce che orienta la tua PMI nell'adozione dell'AI."

LIVELLO_PESO = {
    "Fondamentale": 10.0,
    "Importante": 7.5,
    "Abbastanza importante": 5.0,
    "Poco importante": 2.5,
    "Non importante": 0.0,
}
LIVELLI = list(LIVELLO_PESO.keys())

ROMANI = ["I", "II", "III", "IV", "V"]

FASI = [
    ("onboarding", "Profilo azienda"),
    ("intervista", "Intervista"),
    ("vincitore", "Framework vincitore"),
    ("diagnostica", "Diagnostica"),
    ("report", "Report finale"),
]

CHIAVI_RESET = (
    "step", "contesto_azienda", "assessment_id", "criteri", "idx_criterio",
    "intervista_domanda_corrente", "intervista_idx_corrente",
    "intervista_ultima_parsed", "intervista_risposte_valutate",
    "intervista_turni_llm", "intervista_chat",
    "diag_domanda_corrente", "report_markdown", "fasi_raggiunte",
)


# ---------- helpers UI ----------

def inject_style() -> None:
    css = STYLE_CSS.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def divider_cicerone() -> None:
    st.markdown('<div class="cic-divider">─── · ───</div>', unsafe_allow_html=True)


def header_cicerone() -> None:
    st.markdown(
        f'<div class="cic-header">Cicerone</div>'
        f'<div class="cic-tagline">{TAGLINE}</div>',
        unsafe_allow_html=True,
    )


def wizard_header(step: str, sub: str | None = None) -> None:
    """Breadcrumb di wizard in cima al contenuto: "Passo X di 5 · <fase>" +
    titolo sans bold + thin progress bar oro (indice fase / 5).

    `sub`: riga secondaria opzionale (es. progress "Criterio i/N" intervista).
    """
    fasi_keys = [k for k, _ in FASI]
    n_tot = len(FASI)
    idx = fasi_keys.index(step) if step in fasi_keys else 0
    label = dict(FASI).get(step, step)
    pct = int(round((idx / n_tot) * 100)) if n_tot else 0
    sub_html = f'<div class="cic-wizard-sub">{sub}</div>' if sub else ""
    st.markdown(
        f'<div class="cic-wizard">'
        f'<div class="cic-wizard-eyebrow">Passo {idx + 1} di {n_tot}</div>'
        f'<div class="cic-wizard-title">{label}</div>'
        f'<div class="cic-wizard-track"><div class="cic-wizard-fill" '
        f'style="width:{pct}%"></div></div>'
        f"{sub_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


@contextmanager
def spinner_cicerone(message: str):
    """Spinner ambrato centrato + testo italico. Sostituisce st.spinner per
    le attese LLM più visibili."""
    placeholder = st.empty()
    placeholder.markdown(
        f'<div class="cic-spinner-wrap">'
        f'<div class="cic-spinner"></div>'
        f'<div class="cic-spinner-text">{message}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    try:
        yield
    finally:
        placeholder.empty()


def vai_a(nuovo_step: str) -> None:
    """Cambia step e registra come raggiunto. Poi rerun."""
    raggiunte = st.session_state.setdefault("fasi_raggiunte", {"onboarding"})
    raggiunte.add(nuovo_step)
    st.session_state.step = nuovo_step
    st.rerun()


def _idx_o_default(lista: list, valore, default):
    """Indice di valore in lista; se assente, indice del default."""
    if valore in lista:
        return lista.index(valore)
    return lista.index(default) if default in lista else 0


def get_criteri() -> list[dict]:
    if st.session_state.criteri is None:
        st.session_state.criteri = repo.lista_criteri(SHEET)
    return st.session_state.criteri


# Superficie pubblica del modulo: import "pesanti" e helper sono re-esportati e
# consumati dalle pagine via `from cicerone.ui._pages._shared import ...`.
__all__ = [
    # moduli/oggetti pesanti (re-export)
    "repo", "mcda", "llm_diag", "llm_intervista", "llm_report",
    "complete", "set_api_key", "set_model", "salva_contesto",
    # costanti
    "STYLE_CSS", "SHEET", "TAGLINE", "LIVELLO_PESO", "LIVELLI",
    "ROMANI", "FASI", "CHIAVI_RESET",
    # helper UI
    "inject_style", "divider_cicerone", "header_cicerone", "wizard_header",
    "spinner_cicerone", "vai_a", "_idx_o_default", "get_criteri",
]
