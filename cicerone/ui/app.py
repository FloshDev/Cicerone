"""UI Streamlit per Cicerone.

Avvio:
    uv run streamlit run cicerone/ui/app.py
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import streamlit as st

from cicerone.db import seed
from cicerone.db.connection import get_connection

# Bootstrap schema PRIMA di importare repository: repository.py esegue una
# migration ALTER TABLE al load del modulo, che esplode su DB fresco senza
# tabelle. Applichiamo schema.sql qui per garantire l'invariante.
_SCHEMA_SQL = Path(__file__).parent.parent / "db" / "schema.sql"


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
from cicerone.ui import _mock  # noqa: E402

try:
    from cicerone.llm._client import set_api_key, get_client
except ImportError:
    def set_api_key(_k):  # type: ignore
        return None

    def get_client():  # type: ignore
        raise RuntimeError("Client Anthropic non disponibile")

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

try:
    from cicerone.llm import intervista as llm_intervista
except ImportError:
    llm_intervista = None

salva_contesto = getattr(repo, "salva_contesto", _mock.salva_contesto)

STYLE_CSS = Path(__file__).parent / "style.css"

SHEET = "readiness"

TAGLINE = "La voce che orienta la tua PMI nell'adozione dell'AI."

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
FASCE_FATTURATO = ["< 500k €", "500k - 2M €", "2M - 10M €", "10M - 50M €", "> 50M €"]
USO_AI_OPZIONI = ["No", "Sì, in modo sporadico", "Sì, in modo strutturato"]
NAZIONI_EUROPA = [
    "Austria", "Belgio", "Bulgaria", "Cechia", "Cipro", "Croazia",
    "Danimarca", "Estonia", "Finlandia", "Francia", "Germania", "Grecia",
    "Irlanda", "Italia", "Lettonia", "Lituania", "Lussemburgo", "Malta",
    "Paesi Bassi", "Polonia", "Portogallo", "Regno Unito", "Romania",
    "Slovacchia", "Slovenia", "Spagna", "Svezia", "Svizzera", "Ungheria",
]

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
    "intervista_ultima_parsed", "intervista_clarif_count", "intervista_chat",
    "diag_domanda_corrente", "report_markdown", "fasi_raggiunte",
)

MAX_CLARIFICATIONS_INTERVISTA = 2  # re-domande max per criterio (in aggiunta alla domanda iniziale)


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


def get_criteri() -> list[dict]:
    if st.session_state.criteri is None:
        st.session_state.criteri = repo.lista_criteri(SHEET)
    return st.session_state.criteri


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


def verifica_chiave(api_key: str) -> tuple[bool, str]:
    """Test minimo con call di 10 token a haiku — costo trascurabile."""
    set_api_key(api_key)
    try:
        get_client().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "ping"}],
        )
        return True, "Chiave valida."
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:200]}"


# ---------- sidebar ----------

def sidebar_stepper() -> None:
    step = st.session_state.step

    st.sidebar.markdown(
        '<div class="cic-sidebar-title">Cicerone</div>'
        '<div class="cic-sidebar-caption">Assessment AI Readiness</div>',
        unsafe_allow_html=True,
    )

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
    for n, (key, label) in enumerate(FASI):
        sbloccata = key in raggiunte
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


# ---------- pagine ----------

def blocco_api_key() -> None:
    st.subheader("Configurazione")
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        value=st.session_state.api_key,
        placeholder="sk-ant-api03-...",
        help="Necessaria per intervista, diagnostica e report. Non viene salvata su disco.",
    )

    col_btn, col_msg = st.columns([1, 3])
    with col_btn:
        verifica_clicked = st.button("Verifica chiave", type="primary", disabled=not api_key.strip())

    if verifica_clicked:
        with spinner_cicerone("Sto verificando la chiave con un ping ad Anthropic..."):
            ok, msg = verifica_chiave(api_key.strip())
        st.session_state.api_key = api_key.strip()
        st.session_state.api_key_valida = ok
        st.session_state.api_key_messaggio = msg
        st.rerun()
    elif api_key and api_key.strip() != st.session_state.api_key:
        st.session_state.api_key = api_key.strip()
        st.session_state.api_key_valida = None
        st.session_state.api_key_messaggio = ""
        set_api_key(api_key.strip())
    elif api_key:
        set_api_key(api_key.strip())

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
    header_cicerone()
    blocco_api_key()
    divider_cicerone()

    st.subheader("Profilo dell'azienda")
    st.caption("I dati restano locali; servono al modello per adattare l'intervista al tuo contesto.")

    ctx = st.session_state.contesto_azienda or {}

    with st.form("onboarding"):
        nome_azienda = st.text_input(
            "Nome azienda",
            value=ctx.get("nome_azienda", ""),
            placeholder="Es. Acme S.r.l.",
        )
        settore = st.selectbox(
            "Settore", SETTORI,
            index=_idx_o_default(SETTORI, ctx.get("settore"), "Manifatturiero"),
        )
        dipendenti = st.selectbox(
            "Numero di dipendenti", FASCE_DIPENDENTI,
            index=_idx_o_default(FASCE_DIPENDENTI, ctx.get("fascia_dipendenti"), "10-49"),
        )
        nazione = st.selectbox(
            "Nazione", NAZIONI_EUROPA,
            index=_idx_o_default(NAZIONI_EUROPA, ctx.get("nazione"), "Italia"),
        )
        regione = st.text_input(
            "Regione / Cantone / Stato — opzionale",
            value=ctx.get("regione") or "",
            placeholder="Es. Lombardia, Vaud, Bayern...",
        )
        gia_usa_ai = st.radio(
            "L'azienda utilizza già strumenti AI?",
            USO_AI_OPZIONI,
            index=_idx_o_default(USO_AI_OPZIONI, ctx.get("uso_ai_attuale"), "No"),
        )
        fatturato = st.selectbox(
            "Fascia di fatturato annuo", FASCE_FATTURATO,
            index=_idx_o_default(FASCE_FATTURATO, ctx.get("fascia_fatturato"), "500k - 2M €"),
        )
        note = st.text_area(
            "Note aggiuntive (opzionale)",
            value=ctx.get("note") or "",
            placeholder="Es. processo principale, mercato, vincoli...",
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


def _card_framework(medaglia: str, voce: dict) -> str:
    return (
        f'<div class="cic-card">'
        f'<div class="cic-card-medal">{medaglia}</div>'
        f'<div class="cic-card-body">'
        f'<div class="cic-card-name">{voce["nome"]}</div>'
        f'<div class="cic-card-score">{voce["punteggio"]:.1f} pt</div>'
        f'</div>'
        f'</div>'
    )


def pagina_vincitore() -> None:
    assessment_id = st.session_state.assessment_id
    if assessment_id is None:
        st.warning("Nessun assessment attivo. Torna all'onboarding.")
        return

    header_cicerone()
    classifica = mcda.classifica_framework(assessment_id)
    st.subheader("Framework più adatti")
    st.caption("Calcolo basato sulla matrice dei voti per i pesi che hai espresso.")

    if not classifica:
        st.error("Nessun framework disponibile in DB.")
        return

    top3 = classifica[:3]
    medaglie = ["I", "II", "III"]
    cards_html = "".join(_card_framework(m, v) for m, v in zip(medaglie, top3))
    st.markdown(f'<div class="cic-cards">{cards_html}</div>', unsafe_allow_html=True)

    divider_cicerone()
    st.subheader("Classifica completa")
    st.dataframe(
        [{"Framework": v["nome"], "Punteggio": round(v["punteggio"], 2)} for v in classifica],
        use_container_width=True,
        hide_index=True,
    )

    divider_cicerone()
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

    divider_cicerone()
    if st.button("Continua alla diagnostica →", type="primary"):
        st.session_state.diag_domanda_corrente = None
        vai_a("diagnostica")


def pagina_diagnostica() -> None:
    assessment_id = st.session_state.assessment_id

    header_cicerone()
    st.subheader("Diagnostica guidata")
    st.caption("Rispondi alle domande per personalizzare il report finale.")

    storia_fn = getattr(repo, "storia_diagnostica", None) or getattr(_mock, "storia_diagnostica", lambda _: [])
    storia = storia_fn(assessment_id)
    for qa in storia:
        with st.chat_message("assistant"):
            etichetta = "**Approfondimento** — " if qa.get("is_riask") else ""
            st.markdown(f"{etichetta}{qa['domanda']}")
        with st.chat_message("user"):
            st.markdown(qa["risposta_utente"])

    if st.session_state.diag_domanda_corrente is None:
        with spinner_cicerone("Sto generando la prossima domanda..."):
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
        with spinner_cicerone("Sto interpretando la tua risposta..."):
            prossima = llm_diag.next_question(
                assessment_id,
                domanda_precedente=domanda,
                risposta_precedente=risposta.strip(),
            )
        st.session_state.diag_domanda_corrente = prossima
        st.rerun()


def pagina_report() -> None:
    assessment_id = st.session_state.assessment_id
    header_cicerone()
    st.subheader("Report finale")

    if st.session_state.report_markdown is None:
        with spinner_cicerone(
            "Sto preparando il report finale, possono volerci 20-30 secondi..."
        ):
            st.session_state.report_markdown = llm_report.genera_report(assessment_id)

    markdown = st.session_state.report_markdown
    st.markdown(markdown)

    divider_cicerone()
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


# ---------- entry point ----------

def main() -> None:
    st.set_page_config(page_title="Cicerone", page_icon=None, layout="centered")
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
