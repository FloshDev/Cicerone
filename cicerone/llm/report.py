"""Generazione report finale personalizzato via LLM.

Aggrega: contesto azienda, pesi MCDA, classifica framework, Q&A diagnostica,
knowledge base framework vincitore. Output: markdown completo pronto per
download/distribuzione al cliente.
"""
from cicerone.db import repository as repo
from cicerone.mcda import calcolo
from cicerone.llm.diagnostica import _carica_framework_md
from cicerone.llm._client import get_client

MODEL = "claude-sonnet-4-6"  # Sonnet per qualità prosa report


def _formatta_pesi(pesi: list[dict]) -> str:
    return "\n".join(
        f"- **{p['nomeCriterio']}**: {p['livello']} (peso {p['peso']}/10)"
        + (f" — _{p['motivazione']}_" if p.get('motivazione') else "")
        for p in pesi
    )


def _formatta_classifica(classifica: list[dict], top: int = 5) -> str:
    return "\n".join(
        f"{i+1}. **{f['nome']}** — punteggio {f['punteggio']:.1f}"
        for i, f in enumerate(classifica[:top])
    )


def _formatta_diagnostica(diags: list[dict]) -> str:
    if not diags:
        return "_(Nessuna diagnostica raccolta.)_"
    return "\n\n".join(
        f"**Q{i+1}:** {d['domanda']}\n\n**R:** {d['risposta_utente']}"
        for i, d in enumerate(diags)
    )


def _formatta_contesto(contesto: dict) -> str:
    if not contesto:
        return "_(Contesto non fornito.)_"
    return "\n".join(f"- **{k.replace('_', ' ').title()}**: {v}"
                     for k, v in contesto.items())


def genera_report(assessment_id: int) -> str:
    """Ritorna markdown completo del report personalizzato."""
    ass = repo.get_assessment(assessment_id)
    if not ass:
        raise ValueError(f"Assessment {assessment_id} non trovato")

    contesto = repo.get_contesto(assessment_id) or {}
    pesi = repo.get_pesi_assessment(assessment_id)
    classifica = calcolo.classifica_framework(assessment_id)
    diags = repo.get_diagnostica(assessment_id)

    framework_id = ass.get("framework_vincitore_id") or (
        classifica[0]["framework_id"] if classifica else None
    )
    framework = repo.get_framework(framework_id) if framework_id else None
    framework_nome = framework["nomeFramework"] if framework else "Sconosciuto"
    framework_md = _carica_framework_md(framework_id) if framework_id else ""

    system = f"""Sei un consulente senior di AI Strategy per PMI italiane.
Devi generare un REPORT FINALE personalizzato di valutazione AI Readiness per
un'azienda che ha completato un assessment guidato.

Output: SOLO markdown ben formattato, in italiano, professionale ma leggibile.
Tono: consulenziale, concreto, non accademico. Niente filler, niente premesse
generiche, niente disclaimer.

Struttura attesa:

# Report AI Readiness — [nome o settore azienda]

## 1. Profilo aziendale
Sintesi del contesto fornito (1 paragrafo breve).

## 2. Framework consigliato: {framework_nome}
Spiega in 1-2 paragrafi PERCHÉ questo framework è il più adatto per questa
specifica azienda (sfrutta i criteri con pesi alti + la knowledge base
fornita).

## 3. Maturità attuale e gap
Analisi basata sulle risposte alla diagnostica. Identifica 2-4 gap principali
tra stato attuale e framework target. Sii specifico.

## 4. Roadmap azioni (3-5 mosse concrete)
Lista priorizzata di azioni operative, con orizzonte temporale realistico
(es. "Q1 2026: ...", "6 mesi: ..."). Adatta a settore e dimensione azienda.

## 5. KPI da monitorare
3-5 KPI quantificabili allineati al framework consigliato.

## 6. Riepilogo punteggi
Riporta tabella markdown con top 3 framework + punteggio.

Regole di scrittura:
- Niente bullet vuoti tipo "Da approfondire"
- Niente "potrebbe", "forse", "dipende" — sii direttivo
- Cita criteri specifici dell'azienda dove rilevante
- Lunghezza target: 600-900 parole
"""

    user_prompt = f"""Genera il report per questa azienda.

# Contesto azienda
{_formatta_contesto(contesto)}

# Importanza criteri (compilata dall'azienda)
{_formatta_pesi(pesi)}

# Classifica framework (MCDA)
{_formatta_classifica(classifica)}

# Diagnostica conversazionale
{_formatta_diagnostica(diags)}

# Knowledge base framework vincitore ({framework_nome})
{framework_md[:10000]}

Genera ora il report completo in markdown."""

    resp = get_client().messages.create(
        model=MODEL,
        max_tokens=4000,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return resp.content[0].text
