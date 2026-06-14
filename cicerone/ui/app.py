"""Scheletro UI Streamlit per Cicerone.

Avvio:
    uv run streamlit run cicerone/ui/app.py
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from cicerone.db import repository as repo
from cicerone.db import seed
from cicerone.db.connection import get_connection
from cicerone.ui import _mock

try:
    from cicerone.llm._client import set_api_key
except ImportError:
    def set_api_key(_k):  # type: ignore
        return None

# Try-import dei moduli backend: se non ancora pubblicati, fallback al mock.
try:
    from cicerone.mcda import calcolo as mcda
except ImportError:
    mcda = _mock

try:
    from cicerone.llm import diagnostica as llm_diag
except ImportError:
    llm_diag = _mock

try:
    from cicerone.llm import report as llm_report
except ImportError:
    llm_report = _mock

# salva_contesto: prova nel repository (round 2), fallback al mock no-op
salva_contesto = getattr(repo, "salva_contesto", _mock.salva_contesto)

SCHEMA_SQL = Path(__file__).parent.parent / "db" / "schema.sql"

SHEET = "readiness"

LIVELLO_PESO = {
    "Fondamentale": 10.0,
    "Importante": 7.5,
    "Abbastanza importante": 5.0,
    "Poco importante": 2.5,
    "Non importante": 0.0,
}
LIVELLI = list(LIVELLO_PESO.keys())

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
REGIONI = [
    "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna",
    "Friuli-Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche",
    "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana",
    "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto",
]
FASCE_FATTURATO = ["< 500k €", "500k - 2M €", "2M - 10M €", "10M - 50M €", "> 50M €"]


# ---------- helpers ----------

def bootstrap_schema() -> None:
    """Applica schema.sql se il DB è ancora vuoto. Idempotente."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='Sheet'"
        ).fetchone()
        if row:
            return
        conn.executescript(SCHEMA_SQL.read_text(encoding="utf-8"))
        conn.commit()


def init_state() -> None:
    st.session_state.setdefault("step", "onboarding")
    st.session_state.setdefault("contesto_azienda", None)
    st.session_state.setdefault("assessment_id", None)
    st.session_state.setdefault("criteri", None)
    st.session_state.setdefault("idx_criterio", 0)
    st.session_state.setdefault("diag_domanda_corrente", None)
    st.session_state.setdefault("diag_risposta_input", "")
    st.session_state.setdefault("report_markdown", None)


def get_criteri() -> list[dict]:
    if st.session_state.criteri is None:
        st.session_state.criteri = repo.lista_criteri(SHEET)
    return st.session_state.criteri


def sidebar_stepper() -> None:
    step = st.session_state.step
    st.sidebar.title("Cicerone")
    st.sidebar.caption("Assessment AI Readiness")

    # API key Anthropic (richiesta per diagnostica + report)
    api_key = st.sidebar.text_input(
        "Anthropic API Key",
        type="password",
        value=st.session_state.get("api_key", ""),
        help="Necessaria per diagnostica LLM e report. Non viene salvata su disco.",
        placeholder="sk-ant-api03-...",
    )
    if api_key:
        st.session_state["api_key"] = api_key
        set_api_key(api_key)

    st.sidebar.divider()

    fasi = [
        ("onboarding", "Azienda"),
        ("intervista", "Intervista criteri"),
        ("vincitore", "Framework vincitore"),
        ("diagnostica", "Diagnostica"),
        ("report", "Report finale"),
    ]
    for key, label in fasi:
        marker = "●" if key == step else "○"
        st.sidebar.markdown(f"{marker} **{label}**" if key == step else f"{marker} {label}")

    if step == "intervista":
        criteri = get_criteri()
        st.sidebar.divider()
        n = len(criteri)
        i = min(st.session_state.idx_criterio, n)
        st.sidebar.progress(i / n if n else 0, text=f"Criterio {min(i+1, n)}/{n}")

    st.sidebar.divider()
    if st.sidebar.button("Ricomincia"):
        for k in ("step", "contesto_azienda", "assessment_id", "criteri", "idx_criterio",
                  "diag_domanda_corrente", "diag_risposta_input", "report_markdown"):
            st.session_state.pop(k, None)
        st.rerun()


# ---------- pagine ----------

def pagina_onboarding() -> None:
    st.header("Profilo dell'azienda")
    st.write("Compila i campi per contestualizzare l'assessment.")

    with st.form("onboarding"):
        settore = st.selectbox("Settore", SETTORI, index=0)
        dipendenti = st.selectbox("Numero di dipendenti", FASCE_DIPENDENTI, index=1)
        regione = st.selectbox("Regione", REGIONI, index=REGIONI.index("Lombardia"))
        gia_usa_ai = st.radio("L'azienda utilizza già strumenti AI?",
                              ["No", "Sì, in modo sporadico", "Sì, in modo strutturato"],
                              horizontal=False)
        fatturato = st.selectbox("Fascia di fatturato annuo", FASCE_FATTURATO, index=1)
        note = st.text_area("Note aggiuntive (opzionale)", placeholder="Es. processo principale, mercato...")
        submitted = st.form_submit_button("Avvia intervista")

    if submitted:
        st.session_state.contesto_azienda = {
            "settore": settore,
            "fascia_dipendenti": dipendenti,
            "regione": regione,
            "uso_ai_attuale": gia_usa_ai,
            "fascia_fatturato": fatturato,
            "note": note.strip() or None,
        }
        st.session_state.assessment_id = repo.crea_assessment(SHEET)
        salva_contesto(st.session_state.assessment_id, st.session_state.contesto_azienda)
        st.session_state.step = "intervista"
        st.session_state.idx_criterio = 0
        st.rerun()


def pagina_intervista() -> None:
    criteri = get_criteri()
    n = len(criteri)
    i = st.session_state.idx_criterio

    if i >= n:
        st.session_state.step = "vincitore"
        st.rerun()

    criterio = criteri[i]
    st.header(f"Criterio {i+1}/{n}")
    st.subheader(criterio["nomeCriterio"])
    with st.expander("Definizione", expanded=True):
        st.write(criterio["definizione"])

    pesi_compilati = {p["criterio_id"]: p for p in repo.get_pesi_assessment(st.session_state.assessment_id)}
    precompilato = pesi_compilati.get(criterio["idCriterio"])

    with st.form(f"criterio_{criterio['idCriterio']}"):
        livello_default = LIVELLI.index(precompilato["livello"]) if precompilato else 2
        livello = st.selectbox(
            "Quanto è importante questo criterio per la tua azienda?",
            LIVELLI,
            index=livello_default,
        )
        motivazione = st.text_area(
            "Motivazione (perché questo livello?)",
            value=(precompilato or {}).get("motivazione") or "",
            height=120,
        )
        col_indietro, _, col_avanti = st.columns([1, 2, 1])
        with col_indietro:
            indietro = st.form_submit_button("← Indietro", disabled=(i == 0))
        with col_avanti:
            avanti = st.form_submit_button(
                "Vai al calcolo →" if i == n - 1 else "Salva e prossimo →"
            )

    if indietro:
        st.session_state.idx_criterio = max(0, i - 1)
        st.rerun()

    if avanti:
        repo.salva_peso(
            assessment_id=st.session_state.assessment_id,
            criterio_id=criterio["idCriterio"],
            livello=livello,
            peso=LIVELLO_PESO[livello],
            motivazione=motivazione.strip() or None,
        )
        st.session_state.idx_criterio = i + 1
        if st.session_state.idx_criterio >= n:
            st.session_state.step = "vincitore"
        st.rerun()


def pagina_vincitore() -> None:
    assessment_id = st.session_state.assessment_id
    if assessment_id is None:
        st.warning("Nessun assessment attivo. Torna all'onboarding.")
        return

    classifica = mcda.classifica_framework(assessment_id)
    st.header("Framework più adatti")
    st.caption("Calcolo basato sulla matrice dei voti per i pesi che hai espresso.")

    if not classifica:
        st.error("Nessun framework disponibile in DB.")
        return

    top3 = classifica[:3]
    cols = st.columns(3)
    medaglie = ["1°", "2°", "3°"]
    for col, voce, medaglia in zip(cols, top3, medaglie):
        with col:
            st.metric(label=medaglia, value=voce["nome"], delta=f"{voce['punteggio']:.1f} pt")

    st.divider()
    st.subheader("Classifica completa")
    st.dataframe(
        [{"Framework": v["nome"], "Punteggio": round(v["punteggio"], 2)} for v in classifica],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.subheader("Dettaglio per criterio")
    nomi = [v["nome"] for v in classifica]
    scelto = st.selectbox("Scegli un framework", nomi, index=0)
    framework_id = next(v["framework_id"] for v in classifica if v["nome"] == scelto)
    dettaglio = mcda.breakdown_per_criterio(assessment_id, framework_id)
    st.dataframe(
        [
            {
                "Criterio": d["nome"],
                "Voto framework": d["voto"],
                "Peso utente": d["peso"],
                "Contributo": round(d["contributo"] or 0, 2),
            }
            for d in dettaglio
        ],
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Contesto azienda registrato"):
        st.json(st.session_state.contesto_azienda or {})

    st.divider()
    if st.button("Continua alla diagnostica →", type="primary"):
        st.session_state.step = "diagnostica"
        st.session_state.diag_domanda_corrente = None
        st.rerun()


def pagina_diagnostica() -> None:
    assessment_id = st.session_state.assessment_id
    st.header("Diagnostica guidata")
    st.caption("Rispondi alle domande per personalizzare il report finale.")

    # Storia Q&A precedenti (dal DB)
    storia = _mock.storia_diagnostica(assessment_id) if hasattr(_mock, "storia_diagnostica") else []
    for qa in storia:
        with st.chat_message("assistant"):
            st.markdown(qa["domanda"])
        with st.chat_message("user"):
            st.markdown(qa["risposta_utente"])

    # Domanda corrente
    if st.session_state.diag_domanda_corrente is None:
        with st.spinner("Generazione domanda..."):
            st.session_state.diag_domanda_corrente = llm_diag.next_question(assessment_id)

    domanda = st.session_state.diag_domanda_corrente
    if domanda is None:
        st.success("Diagnostica completata.")
        if st.button("Genera il report →", type="primary"):
            st.session_state.step = "report"
            st.rerun()
        return

    with st.chat_message("assistant"):
        st.markdown(domanda)

    with st.form("diagnostica_risposta", clear_on_submit=True):
        risposta = st.text_area("La tua risposta", height=120)
        inviata = st.form_submit_button("Invia →", type="primary")

    if inviata and risposta.strip():
        with st.spinner("Generazione prossima domanda..."):
            prossima = llm_diag.next_question(
                assessment_id,
                domanda_precedente=domanda,
                risposta_precedente=risposta.strip(),
            )
        st.session_state.diag_domanda_corrente = prossima
        st.rerun()


def pagina_report() -> None:
    assessment_id = st.session_state.assessment_id
    st.header("Report finale")

    if st.session_state.report_markdown is None:
        with st.spinner("Generazione del report in corso..."):
            st.session_state.report_markdown = llm_report.genera_report(assessment_id)

    markdown = st.session_state.report_markdown
    st.markdown(markdown)

    col_dl, col_new = st.columns(2)
    with col_dl:
        st.download_button(
            "Scarica report .md",
            markdown,
            file_name=f"report_cicerone_{assessment_id}.md",
            mime="text/markdown",
        )
    with col_new:
        if st.button("Nuovo assessment"):
            for k in ("step", "contesto_azienda", "assessment_id", "criteri", "idx_criterio",
                      "diag_domanda_corrente", "diag_risposta_input", "report_markdown"):
                st.session_state.pop(k, None)
            st.rerun()


# ---------- entry point ----------

def main() -> None:
    st.set_page_config(page_title="Cicerone", page_icon=None, layout="centered")
    bootstrap_schema()
    seed.run_if_needed()
    init_state()
    sidebar_stepper()

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
