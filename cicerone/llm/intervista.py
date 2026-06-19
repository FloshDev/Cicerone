"""Intervista LLM-guidata: una domanda per criterio adattata al contesto
azienda, e valutazione turno-per-turno della conversazione con decisione
guidata dal modello (chiudi / approfondisci / spiega).

API:
    domanda_per_criterio(criterio, contesto) -> str
    valuta_turno(criterio, contesto, history, n_risposte_valutate,
                 forza_chiusura=False) -> dict
        azione "chiudi":        keys azione, livello, peso, motivazione, ambiguo
        azione "approfondisci": keys azione, domanda
        azione "spiega":        keys azione, spiegazione, domanda
"""
import json

from cicerone.llm._client import complete

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
    system = """Sei un consulente AI Rediness per PMI italiane.
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

    testo = complete(
        system=system,
        messages=[{"role": "user", "content": user}],
        max_tokens=200,
    )
    return testo.strip()


def _strip_json_fence(testo: str) -> str:
    """Rimuove un eventuale fence markdown ```json ... ``` attorno al JSON."""
    testo = testo.strip()
    if testo.startswith("```"):
        testo = testo.split("```")[1]
        if testo.startswith("json"):
            testo = testo[4:]
        testo = testo.strip()
    return testo


def _history_str(history: list[dict] | None) -> str:
    """Rende la conversazione del criterio in testo leggibile per il modello."""
    if not history:
        return "(nessuno scambio finora)"
    righe = []
    for m in history:
        ruolo = "CICERONE" if m.get("role") == "assistant" else "UTENTE"
        righe.append(f"{ruolo}: {m.get('content', '').strip()}")
    return "\n".join(righe)


def valuta_turno(criterio: dict, contesto: dict | None,
                 history: list[dict], n_risposte_valutate: int,
                 forza_chiusura: bool = False) -> dict:
    """Valuta lo stato della conversazione su un criterio e decide il prossimo
    passo. Il modello sceglie autonomamente fra tre azioni.

    Parametri:
        history: tutta la conversazione del criterio corrente, lista di dict
            {"role": "assistant"|"user", "content": str} in ordine cronologico.
        n_risposte_valutate: quante risposte valutabili l'utente ha già dato.
        forza_chiusura: se True il modello DEVE ritornare azione "chiudi"
            best-effort (non può più chiedere altro).

    Ritorna un dict con chiave "azione":
        "chiudi"        -> {azione, livello, peso, motivazione, ambiguo}
        "approfondisci" -> {azione, domanda}
        "spiega"        -> {azione, spiegazione, domanda}
    """
    livelli = list(LIVELLO_PESO.keys())

    system = f"""Sei Cicerone, consulente AI Rediness per PMI italiane. Stai
conducendo un'intervista su UN criterio alla volta per capire QUANTO quel
criterio è importante PER LA SPECIFICA AZIENDA dell'utente.

Hai davanti tutta la conversazione finora su questo criterio. Devi decidere il
prossimo passo scegliendo UNA fra tre azioni:

1) "chiudi" — quando dalla conversazione hai informazioni SUFFICIENTI per
   inferire quanto il criterio è importante per questa azienda. Non serve
   essere certi al 100%: chiudi appena hai abbastanza per una stima ragionevole.
   Formato:
   {{"azione": "chiudi",
     "livello": "<uno di: {', '.join(livelli)}>",
     "motivazione": "<sintesi 1-2 frasi di cosa emerge dalle risposte>",
     "ambiguo": <true se l'inferenza resta incerta, false altrimenti>}}

2) "approfondisci" — quando la risposta è utile ma superficiale e UNA domanda
   mirata di follow-up ti farebbe capire meglio. Formato:
   {{"azione": "approfondisci",
     "domanda": "<UNA domanda di follow-up mirata, max 2 righe, italiano>"}}

3) "spiega" — quando l'utente è confuso o non ha capito la domanda (es. "non
   ho capito", "boh", "che vuol dire?", risposta fuori tema, richiesta di
   chiarimento). NON abbandonarlo mai: SPIEGA il concetto in modo semplice e
   concreto, usando il SETTORE/contesto azienda e le risposte già date come
   esempi, POI riproponi una domanda riformulata più semplice. Formato:
   {{"azione": "spiega",
     "spiegazione": "<spiegazione semplice e concreta, con esempio adatto al
       settore dell'azienda>",
     "domanda": "<la domanda riformulata in modo più semplice, max 2 righe>"}}

Filosofia (IMPORTANTE):
- NON forzare un numero fisso di domande. Chiudi appena hai info sufficienti.
- Non insistere oltre il necessario se l'utente è già stato chiaro.
- Non abbandonare mai un utente confuso: se non ha capito, preferisci "spiega"
  a "chiudi".
{'- ATTENZIONE: devi CHIUDERE adesso. Usa SEMPRE azione "chiudi" con la migliore approssimazione possibile dalle info disponibili (ambiguo=true se incerto). Non usare "approfondisci" né "spiega".' if forza_chiusura else ''}

Output: SOLO JSON valido, niente altro."""

    user = f"""Criterio: {criterio['nomeCriterio']}
Definizione: {criterio['definizione']}
Contesto azienda: {_contesto_str(contesto)}
Risposte valutabili già date dall'utente su questo criterio: {n_risposte_valutate}

Conversazione finora su questo criterio:
\"\"\"
{_history_str(history)}
\"\"\"

Decidi l'azione e ritorna SOLO il JSON."""

    raw = complete(
        system=system,
        messages=[{"role": "user", "content": user}],
        max_tokens=600,
    ) or ""

    # Parsing difensivo: chiediamo JSON valido via prompt, ma refusal/troncamento
    # possono comunque dare output non conforme. In quel caso degrada in una
    # chiusura best-effort invece di propagare l'eccezione fino alla UI.
    try:
        parsed = json.loads(_strip_json_fence(raw))
        if not isinstance(parsed, dict):
            raise ValueError("output JSON non è un oggetto")
    except (json.JSONDecodeError, ValueError):
        parsed = {}
        forza_chiusura = True

    azione = parsed.get("azione")

    # forza_chiusura o azione non riconosciuta: tratta come chiusura best-effort.
    if forza_chiusura or azione not in ("chiudi", "approfondisci", "spiega"):
        azione = "chiudi"

    if azione == "approfondisci":
        domanda = (parsed.get("domanda") or "").strip()
        if not domanda:
            azione = "chiudi"
        else:
            return {"azione": "approfondisci", "domanda": domanda}

    if azione == "spiega":
        return {
            "azione": "spiega",
            "spiegazione": (parsed.get("spiegazione") or "").strip(),
            "domanda": (
                parsed.get("domanda")
                or "Detto semplicemente: quanto conta questo aspetto per la tua azienda?"
            ).strip(),
        }

    # azione == "chiudi" (o fallback)
    livello = parsed.get("livello") or "Abbastanza importante"
    if livello not in LIVELLO_PESO:
        match = next((liv for liv in livelli if liv.lower() == livello.lower()), None)
        livello = match or "Abbastanza importante"

    return {
        "azione": "chiudi",
        "livello": livello,
        "peso": LIVELLO_PESO[livello],
        "motivazione": (parsed.get("motivazione") or "").strip(),
        "ambiguo": bool(parsed.get("ambiguo", bool(forza_chiusura))),
    }
