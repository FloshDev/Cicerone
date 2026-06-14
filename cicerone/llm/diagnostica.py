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
MAX_DOMANDE = 5
MIN_DOMANDE = 3

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

Regole:
- Ogni risposta tua = SOLO una singola domanda (no preamboli, no commenti)
- Domande concrete, operative, in italiano, max 2 righe
- Adatta le domande al settore e alla dimensione dell'azienda
- Approfondisci dove i pesi sono alti (Fondamentale/Importante)
- Quando hai raccolto abbastanza informazioni (almeno {MIN_DOMANDE} risposte)
  rispondi ESATTAMENTE con la parola "STOP" (niente altro).
"""


def next_question(
    assessment_id: int,
    domanda_precedente: str | None = None,
    risposta_precedente: str | None = None,
) -> str | None:
    """Genera prossima domanda diagnostica, salva Q&A precedente se passata.

    Ritorna None quando la diagnostica è chiusa.
    """
    # 1. Salva Q&A precedente (se fornita)
    if domanda_precedente and risposta_precedente:
        repo.salva_diagnostica(
            assessment_id=assessment_id,
            domanda=domanda_precedente,
            risposta_utente=risposta_precedente,
        )

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
    diags = repo.get_diagnostica(assessment_id)
    framework_md = _carica_framework_md(framework_id)

    # 3. Hard cap su domande
    if len(diags) >= MAX_DOMANDE:
        return None

    # 4. Build messages: ricostruisce storia conversazione
    messages = []
    for d in diags:
        messages.append({"role": "assistant", "content": d["domanda"]})
        messages.append({"role": "user", "content": d["risposta_utente"]})

    # Trigger LLM per prossima domanda
    if not messages:
        # Prima chiamata: chiediamo direttamente la prima domanda
        messages.append({"role": "user", "content": "Inizia la diagnostica."})
    else:
        # Già conversazione in corso: prossima domanda o STOP
        messages.append({"role": "user", "content": "Prossima domanda o STOP se hai abbastanza informazioni."})

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
    if testo.upper().startswith("STOP") and len(diags) >= MIN_DOMANDE:
        return None

    return testo
