"""Intervista LLM-guidata: una domanda per criterio adattata al contesto
azienda, parsing risposta libera utente in (livello, peso, motivazione, ambiguo).

API:
    domanda_per_criterio(criterio, contesto) -> str
    parse_risposta(criterio, contesto, risposta_libera) -> dict
        keys: livello, peso, motivazione, ambiguo
"""
import json

from cicerone.llm._client import get_client

MODEL = "claude-haiku-4-5-20251001"

LIVELLO_PESO = {
    "Fondamentale": 10.0,
    "Importante": 7.5,
    "Abbastanza importante": 5.0,
    "Poco importante": 2.5,
    "Non importante": 0.0,
}


def _contesto_str(contesto: dict | None) -> str:
    if not contesto:
        return "Nessun contesto fornito."
    return ", ".join(f"{k}: {v}" for k, v in contesto.items() if v)


def domanda_per_criterio(criterio: dict, contesto: dict | None) -> str:
    """Genera UNA domanda specifica per indagare l'importanza del criterio
    dal punto di vista dell'azienda. Tarata sul settore/dimensione/contesto.
    """
    system = """Sei un consulente AI Readiness per PMI italiane.
Stai conducendo un'intervista strutturata: un criterio alla volta, una domanda
alla volta. La domanda deve aiutare l'imprenditore a capire QUANTO QUEL
CRITERIO è importante PER LA SUA SPECIFICA AZIENDA (non in astratto).

Regole output:
- SOLO la domanda, niente preambolo, niente "Domanda:", niente commenti
- Italiano, max 2 righe, concreta e operativa
- Adatta a settore e dimensione azienda fornita
- Stimola riflessione, non risposta sì/no"""

    user = f"""Criterio da indagare:
**{criterio['nomeCriterio']}**
Definizione: {criterio['definizione']}

Contesto azienda: {_contesto_str(contesto)}

Genera la domanda."""

    resp = get_client().messages.create(
        model=MODEL,
        max_tokens=200,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text.strip()


def parse_risposta(criterio: dict, contesto: dict | None,
                   risposta_libera: str, is_retry: bool = False) -> dict:
    """Parsa risposta utente in livello/peso/motivazione/ambiguo,
    o richiede chiarimento se l'utente non ha capito / risposta inutilizzabile.

    Se `is_retry=False` e la risposta è palesemente non-comprensione
    (es. "non ho capito", "boh", "non saprei", domanda di rimando, vuoto):
        ritorna {"needs_clarification": True,
                 "clarification_question": "<riformulazione semplificata>"}

    Altrimenti ritorna:
        {"needs_clarification": False,
         "livello": str,
         "peso": float,
         "motivazione": str,
         "ambiguo": bool}

    Se `is_retry=True` e la risposta è ancora vaga, accetta best-effort
    (ambiguo=True) e prosegue.
    """
    livelli = list(LIVELLO_PESO.keys())

    system = f"""Sei un parser strutturato per un'intervista AI Readiness.
Devi analizzare la risposta libera di un utente a una domanda su un criterio
MCDA, e DECIDERE una di queste due strade:

A) Se la risposta è inutilizzabile per inferire l'importanza del criterio
   (esempi: "non ho capito", "boh", "non saprei", "che vuol dire?", risposta
   vuota, risposta che chiede chiarimento sulla domanda, parole sole tipo
   "abbastanza" senza contesto):
   → ritorna `{{"needs_clarification": true,
                "clarification_question": "<una riformulazione MOLTO più
                semplice e concreta della domanda, max 2 righe, in italiano,
                con un esempio concreto adatto al settore se possibile>"}}`

B) Se la risposta contiene informazione utile (anche imperfetta):
   → ritorna `{{"needs_clarification": false,
                "livello": "<uno di: {', '.join(livelli)}>",
                "motivazione": "<sintesi 1-2 frasi della risposta utente>",
                "ambiguo": <true se l'inferenza è incerta, false altrimenti>}}`

{'IMPORTANTE: questo è il SECONDO tentativo. Anche se la risposta è ancora vaga, NON usare ramo A. Usa ramo B con ambiguo=true, scegliendo il livello che meglio approssima.' if is_retry else ''}

Output: SOLO JSON valido, niente altro."""

    user = f"""Criterio: {criterio['nomeCriterio']}
Definizione: {criterio['definizione']}
Contesto azienda: {_contesto_str(contesto)}

Risposta libera dell'utente:
\"\"\"
{risposta_libera}
\"\"\"

Decidi ramo A o B e ritorna il JSON."""

    resp = get_client().messages.create(
        model=MODEL,
        max_tokens=500,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    testo = resp.content[0].text.strip()

    if testo.startswith("```"):
        testo = testo.split("```")[1]
        if testo.startswith("json"):
            testo = testo[4:]
        testo = testo.strip()

    parsed = json.loads(testo)

    # Ramo A: chiarimento
    if parsed.get("needs_clarification") and not is_retry:
        return {
            "needs_clarification": True,
            "clarification_question": parsed.get(
                "clarification_question",
                "Mi spiego meglio: quanto è importante questo aspetto per la tua azienda, su una scala da 'per nulla' a 'fondamentale'?",
            ).strip(),
        }

    # Ramo B: parse normale (anche se LLM tentava chiarimento ma è retry)
    livello = parsed.get("livello") or "Abbastanza importante"
    if livello not in LIVELLO_PESO:
        match = next((liv for liv in livelli if liv.lower() == livello.lower()), None)
        livello = match or "Abbastanza importante"

    return {
        "needs_clarification": False,
        "livello": livello,
        "peso": LIVELLO_PESO[livello],
        "motivazione": parsed.get("motivazione", "").strip(),
        "ambiguo": bool(parsed.get("ambiguo", bool(is_retry))),
    }
