"""Diagnostica LLM multi-turno post-MCDA.

Confronta profilo aziendale + pesi compilati con il framework vincitore (knowledge base
in `knowledge/frameworks/`). Fa 3-5 domande mirate per scoprire gap e
maturità reale prima di generare il report finale.

API per UI:
    next_question(assessment_id, domanda_precedente=None, risposta_precedente=None)
    -> str | None

    - Prima call: entrambi None → genera Q1
    - Call successive: passa Q&A precedente → salva in DB + genera Qn
    - Quando l'LLM ritorna 'STOP' (≥3 risposte raccolte) → ritorna None
"""
from pathlib import Path

from cicerone.db import repository as repo
from cicerone.llm._client import get_client

MODEL = "claude-haiku-4-5-20251001"
MAX_DOMANDE = 7  # include eventuali re-domande
MIN_DOMANDE = 3
MAX_RIASK = 2  # cap totale re-domande nella sessione
RIASK_TAG = "[RIASK]"

KNOWLEDGE_DIR = Path(__file__).parent.parent.parent / "knowledge" / "frameworks"

# Mapping framework_id (DB) → file .md (best-effort, naming non perfettamente
# allineato; #11 fallback su firm_level.md)
FRAMEWORK_MD = {
    1: "from_ai_to_digital_trasformation.md",
    2: "agritech_ai_readiness.md",
    3: "exhibition-sector-readiness-ai.md",
    4: "tohe_airam.md",
    5: "ai_adoption_model_smes_bettoni_2021.md",
    6: "ready_or_not.md",
    7: "aimm.md",
    8: "towards_ai_maturity_model.md",
    9: "org_chassis_ai_readiness.md",
    10: "social_capital,_cyber_resilience_ai_readiness_nelle_pmi.md",
    11: "firm_level.md",
}


def _carica_framework_md(framework_id: int) -> str:
    nome_file = FRAMEWORK_MD.get(framework_id)
    if not nome_file:
        return ""
    path = KNOWLEDGE_DIR / nome_file
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _system_prompt(contesto: dict, pesi: list[dict], framework_md: str,
                   framework_nome: str) -> str:
    pesi_str = "\n".join(
        f"- {p['nomeCriterio']}: peso {p['peso']}/10 ({p['livello']})"
        + (f" — motivazione: {p['motivazione']}" if p.get('motivazione') else "")
        for p in pesi
    )
    contesto_str = "\n".join(f"- {k}: {v}" for k, v in contesto.items()) if contesto else "Nessun contesto fornito."

    return f"""Sei un consulente esperto di AI Readiness per PMI italiane.
Stai conducendo una diagnostica conversazionale per approfondire la maturità AI
di un'azienda confrontandola con il framework che è risultato il più adatto
secondo l'analisi MCDA.

# Contesto azienda
{contesto_str}

# Importanza dei criteri secondo l'azienda
{pesi_str}

# Framework consigliato: {framework_nome}
Knowledge base del framework:

{framework_md[:8000]}

# Il tuo compito

Fai da {MIN_DOMANDE} a {MAX_DOMANDE} domande mirate, UNA ALLA VOLTA, per:
1. Verificare la maturità reale dell'azienda sui criteri più importanti per loro
2. Identificare gap specifici rispetto al framework consigliato
3. Raccogliere informazioni utili per il report finale (azioni concrete)

Regole base:
- Ogni risposta tua = SOLO una singola domanda (no preamboli, no commenti)
- Domande concrete, operative, in italiano, max 2 righe
- Adatta le domande al settore e alla dimensione dell'azienda
- Approfondisci dove i pesi sono alti (Fondamentale/Importante)

# Gestione risposte vaghe (IMPORTANTE)

Se l'ULTIMA risposta dell'utente è vaga, evasiva, generica, o non risponde
alla domanda (esempi: "boh", "dipende", "un po'", "abbastanza", risposta che
non contiene fatti concreti):
- Anziché passare al prossimo topic, riformula la domanda in modo PIÙ MIRATO
  e concreto sullo STESSO argomento (chiedi esempi, numeri, processi
  specifici).
- Prefissa la nuova domanda con la stringa esatta `{RIASK_TAG}` (incluse
  parentesi quadre) per segnalare la re-domanda.
- Esempio: `{RIASK_TAG} Mi puoi fare un esempio concreto di un progetto AI
  che avete provato a lanciare nell'ultimo anno?`

Vincoli sulle re-domande:
- Massimo {MAX_RIASK} re-domande TOTALI nella sessione (vedi conversazione)
- Una sola re-domanda per topic (se anche la seconda risposta è vaga, prosegui
  al topic successivo)
- Le re-domande contano nel totale {MAX_DOMANDE}

# Chiusura

Quando hai raccolto abbastanza informazioni concrete (almeno {MIN_DOMANDE}
risposte significative non vaghe), rispondi ESATTAMENTE con la parola
"STOP" (niente altro).
"""


def _strip_riask(testo: str) -> str:
    """Rimuove eventuale tag interno [RIASK] prima di mostrare all'utente."""
    if testo.lstrip().startswith(RIASK_TAG):
        return testo.lstrip()[len(RIASK_TAG):].lstrip()
    return testo


def next_question(
    assessment_id: int,
    domanda_precedente: str | None = None,
    risposta_precedente: str | None = None,
) -> str | None:
    """Genera prossima domanda diagnostica.

    Strategia persistenza:
    - La domanda viene salvata in DB al momento della generazione, con
      risposta_utente="" (sentinel "pending").
    - Quando l'utente risponde, UPDATE della risposta sulla riga pending.
    - `domanda_precedente` viene ignorato (usiamo la riga pending in DB).

    Ritorna None quando la diagnostica è chiusa.
    """
    diags = repo.get_diagnostica(assessment_id)

    # 1. Update risposta sulla riga "pending" (ultima senza risposta)
    if risposta_precedente:
        pending = next((d for d in reversed(diags) if not d["risposta_utente"]), None)
        if pending:
            repo.update_risposta_diagnostica(pending["idDiagnostica"], risposta_precedente)
            # Reload diags con la risposta appena salvata
            diags = repo.get_diagnostica(assessment_id)

    # 2. Carica stato
    ass = repo.get_assessment(assessment_id)
    if not ass:
        raise ValueError(f"Assessment {assessment_id} non trovato")

    framework_id = ass.get("framework_vincitore_id")
    if not framework_id:
        # Se non ancora settato, prendi vincitore al volo
        from cicerone.mcda import calcolo
        v = calcolo.vincitore(assessment_id)
        if not v:
            raise ValueError("Nessun framework vincitore per questo assessment")
        framework_id = v["framework_id"]
        repo.set_framework_vincitore(assessment_id, framework_id)

    framework = repo.get_framework(framework_id)
    contesto = repo.get_contesto(assessment_id) or {}
    pesi = repo.get_pesi_assessment(assessment_id)
    framework_md = _carica_framework_md(framework_id)

    # 3. Considera solo diagnostiche già "risposte" per cap e storia
    diags_risposte = [d for d in diags if d["risposta_utente"]]

    if len(diags_risposte) >= MAX_DOMANDE:
        return None

    n_riask = sum(1 for d in diags_risposte if d["domanda"].lstrip().startswith(RIASK_TAG))
    riask_disponibili = max(0, MAX_RIASK - n_riask)

    # 4. Build messages: ricostruisce storia conversazione (solo risposte)
    messages = []
    for d in diags_risposte:
        messages.append({"role": "assistant", "content": d["domanda"]})
        messages.append({"role": "user", "content": d["risposta_utente"]})

    if not messages:
        messages.append({"role": "user", "content": "Inizia la diagnostica."})
    else:
        nota_riask = (
            f"Hai ancora {riask_disponibili} re-domande disponibili (prefissa con {RIASK_TAG})."
            if riask_disponibili > 0
            else "Hai esaurito le re-domande, procedi al prossimo topic o STOP."
        )
        messages.append({
            "role": "user",
            "content": f"Prossima domanda (o STOP se basta). {nota_riask}",
        })

    system = _system_prompt(
        contesto=contesto,
        pesi=pesi,
        framework_md=framework_md,
        framework_nome=framework["nomeFramework"] if framework else "Sconosciuto",
    )

    resp = get_client().messages.create(
        model=MODEL,
        max_tokens=400,
        system=system,
        messages=messages,
    )
    testo = resp.content[0].text.strip()

    # 5. Check STOP
    if testo.upper().startswith("STOP") and len(diags_risposte) >= MIN_DOMANDE:
        return None

    # 6. Se [RIASK] usato oltre il cap, downgrade a domanda normale (toglie tag)
    if testo.startswith(RIASK_TAG) and riask_disponibili == 0:
        testo = testo[len(RIASK_TAG):].lstrip()

    # 7. Persisti domanda in DB (con tag se presente, per contare le re-ask).
    # risposta_utente="" è il sentinel "pending".
    repo.salva_diagnostica(
        assessment_id=assessment_id,
        domanda=testo,
        risposta_utente="",
    )

    # 8. Ritorna testo pulito alla UI (senza tag interno [RIASK])
    return _strip_riask(testo)
