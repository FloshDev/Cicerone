"""Generazione report finale personalizzato via LLM.

Aggrega: contesto azienda, pesi MCDA, classifica framework, Q&A diagnostica,
knowledge base framework vincitore. Output: markdown completo pronto per
download/distribuzione al cliente.
"""
from cicerone.db import repository as repo
from cicerone.llm._client import get_client
from cicerone.llm.diagnostica import _carica_framework_md
from cicerone.mcda import calcolo

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
    # Filtra solo Q&A complete
    diags_tutti = repo.get_diagnostica(assessment_id)
    diags = [d for d in diags_tutti if d.get("risposta_utente")]

    framework_id = ass.get("framework_vincitore_id") or (
        classifica[0]["framework_id"] if classifica else None
    )
    framework = repo.get_framework(framework_id) if framework_id else None
    framework_nome = framework["nomeFramework"] if framework else "Sconosciuto"
    framework_md = _carica_framework_md(framework_id) if framework_id else ""

    nome_azienda = contesto.get("nome_azienda") or contesto.get("settore") or "Azienda"

    system = f"""Sei un consulente senior di AI Strategy per PMI italiane.
Devi generare un REPORT FINALE personalizzato di valutazione AI Rediness per
un'azienda che ha completato un assessment guidato.

Output: SOLO markdown ben formattato, in italiano, professionale ma leggibile.
Tono: consulenziale, concreto, non accademico. Niente filler, niente premesse
generiche, niente disclaimer.

Struttura ESATTA (5 sezioni, niente "Riepilogo punteggi"):

# Report AI Rediness — {nome_azienda}
## Framework consigliato: {framework_nome}

_(Subito sotto il titolo, in 1 frase italica, anticipa il "perché" della scelta)_

## 1. Profilo aziendale
Sintesi del contesto fornito (1 paragrafo breve, 3-5 righe).
Cita nome azienda, settore, dimensione, paese/regione, eventuale uso AI attuale.

## 2. Perché questo framework
2 paragrafi che spiegano PERCHÉ "{framework_nome}" è il più adatto per questa
specifica azienda. Sfrutta: criteri con peso alto dell'azienda + knowledge base
del framework. Niente generalità — argomenta sul caso concreto.

## 3. Maturità attuale e gap
Analisi basata sulle risposte alla diagnostica. Identifica 2-4 gap specifici
tra stato attuale e framework target. Per ogni gap: nome + 2-3 righe descrizione
+ implicazione operativa.

## 4. Roadmap azioni (priorizzate)
3-5 azioni concrete, in ordine di PRIORITÀ. Per ogni azione, formato esatto:

### P1 — [Titolo azione]
**Quando:** [orizzonte temporale realistico, es. "Q1 2026", "primi 90 giorni"]
**Perché priorità P1:** [1-2 righe motivazione del livello di priorità —
quale gap chiude, perché va fatto prima delle altre]
**Cosa fare:** [3-5 righe operative, specifiche per settore e dimensione]

Usa P1 = critica/immediata, P2 = importante/medio termine, P3 = consolidamento.
NON usare P1 per tutto: ordina davvero.

## 5. KPI da monitorare
3-5 KPI quantificabili. Per ciascuno, formato esatto:

### [Nome KPI]
**Cosa misura:** [1 riga, definizione operativa misurabile]
**Perché è critico per voi:** [1-2 righe, lega al framework e ai gap identificati]
**Come si calcola:** [formula o procedura concreta, con frequenza di
rilevazione, es. "mensile da log sistema X"]
**Baseline attuale → Target:** [valore stimato oggi → valore atteso entro N mesi]

Regole di scrittura:
- Niente bullet generici tipo "Da approfondire" o "Valutare"
- Niente "potrebbe", "forse", "dipende" — sii direttivo
- Cita criteri specifici e risposte specifiche dell'azienda dove rilevante
- Tono diretto, italiano consulenziale, no anglicismi inutili
- Lunghezza target: 700-1100 parole
- NIENTE sezione "Riepilogo punteggi" o tabella classifica framework
"""

    user_prompt = f"""Genera il report per questa azienda.

# Contesto azienda
{_formatta_contesto(contesto)}

# Importanza criteri (compilata dall'azienda)
{_formatta_pesi(pesi)}

# Classifica framework MCDA (solo per tuo riferimento interno — NON pubblicare)
{_formatta_classifica(classifica)}

Framework vincitore (oggetto del report): **{framework_nome}**

# Diagnostica conversazionale (solo Q&A risposte)
{_formatta_diagnostica(diags)}

# Knowledge base framework vincitore ({framework_nome})
{framework_md[:10000]}

Genera ora il report completo in markdown, seguendo la struttura esatta del
system prompt (5 sezioni, niente riepilogo punteggi)."""

    resp = get_client().messages.create(
        model=MODEL,
        max_tokens=4500,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return resp.content[0].text
