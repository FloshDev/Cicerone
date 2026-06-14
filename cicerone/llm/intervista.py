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
                   risposta_libera: str) -> dict:
    """Parsa risposta utente in livello/peso/motivazione/ambiguo.

    Ritorna dict:
        - livello: str (uno dei 5 livelli ammessi)
        - peso: float (mapping fisso)
        - motivazione: str (sintesi pulita risposta)
        - ambiguo: bool (True se LLM non sicuro dell'inferenza)
    """
    livelli = list(LIVELLO_PESO.keys())

    system = f"""Sei un parser strutturato. Devi inferire l'importanza che
un'azienda attribuisce a un criterio MCDA, basandoti sulla sua risposta libera.

Devi assegnare ESATTAMENTE uno di questi 5 livelli:
{chr(10).join(f"- {l}" for l in livelli)}

Output: SOLO JSON valido, niente altro, questa struttura esatta:
{{
  "livello": "<uno dei 5 livelli>",
  "motivazione": "<sintesi 1-2 frasi della risposta utente>",
  "ambiguo": <true|false>
}}

"ambiguo": true SE la risposta è troppo vaga, evasiva o contraddittoria per
inferire un livello con sicurezza. Altrimenti false."""

    user = f"""Criterio: {criterio['nomeCriterio']}
Definizione: {criterio['definizione']}
Contesto azienda: {_contesto_str(contesto)}

Risposta libera dell'utente:
\"\"\"
{risposta_libera}
\"\"\"

Parsa in JSON."""

    resp = get_client().messages.create(
        model=MODEL,
        max_tokens=400,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    testo = resp.content[0].text.strip()

    # Strip eventuali code fence
    if testo.startswith("```"):
        testo = testo.split("```")[1]
        if testo.startswith("json"):
            testo = testo[4:]
        testo = testo.strip()

    parsed = json.loads(testo)
    livello = parsed["livello"]
    if livello not in LIVELLO_PESO:
        # Fallback: best-effort match case-insensitive
        match = next((l for l in livelli if l.lower() == livello.lower()), None)
        livello = match or "Abbastanza importante"

    return {
        "livello": livello,
        "peso": LIVELLO_PESO[livello],
        "motivazione": parsed.get("motivazione", "").strip(),
        "ambiguo": bool(parsed.get("ambiguo", False)),
    }
