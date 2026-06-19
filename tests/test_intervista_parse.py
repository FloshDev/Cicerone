"""Unit test per cicerone.llm.intervista.valuta_turno / domanda_per_criterio.

NESSUNA chiamata di rete: l'helper `complete` di `_client` è monkeypatchato.
`intervista.py` chiama `complete(system=..., messages=..., max_tokens=...)` e
usa direttamente la stringa ritornata. Costruiamo un fake `complete` che
registra le call e ritorna un testo "canned", così da pilotare i tre rami di
valuta_turno (chiudi / approfondisci / spiega).
"""
import json

import pytest

from cicerone.llm import intervista


# --- Fake complete che registra le call e ritorna testo canned ---------------
class _FakeComplete:
    def __init__(self, canned_text: str):
        self._canned_text = canned_text
        self.calls: list[dict] = []

    def __call__(self, system: str, messages: list, max_tokens: int):
        self.calls.append(
            {"system": system, "messages": messages, "max_tokens": max_tokens}
        )
        return self._canned_text


@pytest.fixture
def patch_client(monkeypatch):
    """Ritorna un factory: data una stringa canned, monkeypatcha
    intervista.complete per ritornare quel testo. Espone il fake complete
    (per ispezionare le call)."""

    def _install(canned_text: str):
        fake = _FakeComplete(canned_text)
        monkeypatch.setattr(intervista, "complete", fake)
        return fake

    return _install


CRITERIO = {
    "idCriterio": 1,
    "nomeCriterio": "Strategia AI",
    "definizione": "Quanto l'azienda ha una visione chiara sull'uso dell'AI.",
}
CONTESTO = {"settore": "manifatturiero", "dimensione": "PMI 40 addetti"}

HISTORY = [
    {"role": "assistant", "content": "Quanto è centrale l'AI per voi?", "kind": "domanda"},
    {"role": "user", "content": "Abbastanza importante."},
]


# --- Azione: chiudi ----------------------------------------------------------
def test_valuta_turno_chiudi(patch_client):
    canned = json.dumps({
        "azione": "chiudi",
        "livello": "Fondamentale",
        "motivazione": "Per loro l'AI è centrale nel piano industriale.",
        "ambiguo": False,
    })
    patch_client(canned)

    out = intervista.valuta_turno(CRITERIO, CONTESTO, HISTORY, 1)
    assert out["azione"] == "chiudi"
    assert out["livello"] == "Fondamentale"
    assert out["peso"] == 10.0  # mapping LIVELLO_PESO
    assert out["motivazione"] == "Per loro l'AI è centrale nel piano industriale."
    assert out["ambiguo"] is False


def test_chiudi_livello_sconosciuto_fallback(patch_client):
    """Livello non in mappa -> fallback 'Abbastanza importante'."""
    canned = json.dumps({
        "azione": "chiudi",
        "livello": "Super Mega Critico",
        "motivazione": "x",
        "ambiguo": False,
    })
    patch_client(canned)
    out = intervista.valuta_turno(CRITERIO, CONTESTO, HISTORY, 1)
    assert out["livello"] == "Abbastanza importante"
    assert out["peso"] == 5.0


def test_chiudi_livello_case_insensitive(patch_client):
    """Match case-insensitive di un livello valido."""
    canned = json.dumps({
        "azione": "chiudi",
        "livello": "importante",  # minuscolo
        "motivazione": "x",
        "ambiguo": False,
    })
    patch_client(canned)
    out = intervista.valuta_turno(CRITERIO, CONTESTO, HISTORY, 1)
    assert out["livello"] == "Importante"
    assert out["peso"] == 7.5


def test_chiudi_json_in_code_fence(patch_client):
    """valuta_turno deve gestire JSON dentro ```json ... ``` (markdown)."""
    payload = {
        "azione": "chiudi",
        "livello": "Importante",
        "motivazione": "ok",
        "ambiguo": True,
    }
    canned = "```json\n" + json.dumps(payload) + "\n```"
    patch_client(canned)
    out = intervista.valuta_turno(CRITERIO, CONTESTO, HISTORY, 1)
    assert out["azione"] == "chiudi"
    assert out["livello"] == "Importante"
    assert out["ambiguo"] is True


# --- Azione: approfondisci ---------------------------------------------------
def test_valuta_turno_approfondisci(patch_client):
    canned = json.dumps({
        "azione": "approfondisci",
        "domanda": "Avete già sperimentato strumenti AI in produzione?",
    })
    patch_client(canned)
    out = intervista.valuta_turno(CRITERIO, CONTESTO, HISTORY, 1)
    assert out["azione"] == "approfondisci"
    assert out["domanda"] == "Avete già sperimentato strumenti AI in produzione?"


def test_approfondisci_senza_domanda_diventa_chiudi(patch_client):
    """approfondisci senza una domanda valida -> fallback a chiusura."""
    canned = json.dumps({"azione": "approfondisci", "domanda": ""})
    patch_client(canned)
    out = intervista.valuta_turno(CRITERIO, CONTESTO, HISTORY, 1)
    assert out["azione"] == "chiudi"
    assert out["livello"] == "Abbastanza importante"


# --- Azione: spiega ----------------------------------------------------------
def test_valuta_turno_spiega(patch_client):
    canned = json.dumps({
        "azione": "spiega",
        "spiegazione": "Per strategia AI intendo se nel vostro piano c'è l'AI.",
        "domanda": "Nel vostro settore manifatturiero, l'AI vi serve?",
    })
    patch_client(canned)
    out = intervista.valuta_turno(CRITERIO, CONTESTO, HISTORY, 0)
    assert out["azione"] == "spiega"
    assert out["spiegazione"]
    assert out["domanda"] == "Nel vostro settore manifatturiero, l'AI vi serve?"


def test_spiega_senza_domanda_usa_default(patch_client):
    canned = json.dumps({
        "azione": "spiega",
        "spiegazione": "Spiegazione semplice.",
    })
    patch_client(canned)
    out = intervista.valuta_turno(CRITERIO, CONTESTO, HISTORY, 0)
    assert out["azione"] == "spiega"
    assert isinstance(out["domanda"], str) and out["domanda"]


# --- forza_chiusura ----------------------------------------------------------
def test_forza_chiusura_ignora_altre_azioni(patch_client):
    """Con forza_chiusura=True, anche se l'LLM ritorna 'spiega' o
    'approfondisci', valuta_turno chiude best-effort (ambiguo=True di default)."""
    canned = json.dumps({
        "azione": "spiega",
        "spiegazione": "...",
        "domanda": "riprova...",
    })
    patch_client(canned)
    out = intervista.valuta_turno(
        CRITERIO, CONTESTO, HISTORY, 3, forza_chiusura=True)
    assert out["azione"] == "chiudi"
    # Nessun livello fornito -> default 'Abbastanza importante'.
    assert out["livello"] == "Abbastanza importante"
    assert out["peso"] == 5.0
    # ambiguo non specificato + forza_chiusura=True -> default True.
    assert out["ambiguo"] is True


def test_forza_chiusura_preserva_livello_se_presente(patch_client):
    """Se il modello fornisce un livello valido pur in forza_chiusura, lo usa."""
    canned = json.dumps({
        "azione": "chiudi",
        "livello": "Poco importante",
        "motivazione": "Per loro conta poco.",
        "ambiguo": False,
    })
    patch_client(canned)
    out = intervista.valuta_turno(
        CRITERIO, CONTESTO, HISTORY, 3, forza_chiusura=True)
    assert out["azione"] == "chiudi"
    assert out["livello"] == "Poco importante"
    assert out["peso"] == 2.5


# --- robustezza --------------------------------------------------------------
def test_azione_sconosciuta_diventa_chiudi(patch_client):
    """Azione non riconosciuta -> trattata come chiusura best-effort."""
    canned = json.dumps({"azione": "boh", "livello": "Importante"})
    patch_client(canned)
    out = intervista.valuta_turno(CRITERIO, CONTESTO, HISTORY, 1)
    assert out["azione"] == "chiudi"
    assert out["livello"] == "Importante"


def test_valuta_turno_no_rete_nessun_client_reale(patch_client):
    """Sanity: la call passa per il fake complete (registra l'invocazione)."""
    canned = json.dumps({"azione": "chiudi", "livello": "Importante",
                         "motivazione": "x", "ambiguo": False})
    fake = patch_client(canned)
    intervista.valuta_turno(CRITERIO, CONTESTO, HISTORY, 1)
    assert len(fake.calls) == 1


def test_valuta_turno_history_nel_prompt(patch_client):
    """La conversazione (history) deve finire nel prompt user del modello."""
    canned = json.dumps({"azione": "chiudi", "livello": "Importante",
                         "motivazione": "x", "ambiguo": False})
    fake = patch_client(canned)
    intervista.valuta_turno(CRITERIO, CONTESTO, HISTORY, 1)
    user_msg = fake.calls[0]["messages"][0]["content"]
    assert "Abbastanza importante." in user_msg  # contenuto risposta utente


def test_json_malformato_non_crasha_chiude_best_effort(patch_client):
    """JSON invalido dal modello (es. virgoletta non-escaped dentro una
    stringa, caso reale Oil&gas) NON deve propagare JSONDecodeError fino alla
    UI: valuta_turno degrada in una chiusura sicura (ambiguo=True)."""
    canned = '{"azione": "chiudi", "livello": "Importante", "motivazione": "standard "API 6D"", "ambiguo": false}'
    patch_client(canned)
    out = intervista.valuta_turno(CRITERIO, CONTESTO, HISTORY, 1)
    assert out["azione"] == "chiudi"
    assert out["livello"] in intervista.LIVELLO_PESO
    assert out["ambiguo"] is True


def test_output_json_richiesto_nel_system(patch_client):
    """valuta_turno deve istruire il modello a emettere SOLO JSON valido nel
    system prompt (niente structured outputs provider-specifici con litellm)."""
    canned = json.dumps({"azione": "chiudi", "livello": "Importante",
                         "motivazione": "x", "ambiguo": False})
    fake = patch_client(canned)
    intervista.valuta_turno(CRITERIO, CONTESTO, HISTORY, 1)
    system = fake.calls[0]["system"]
    assert "JSON" in system


# --- domanda_per_criterio ----------------------------------------------------
def test_domanda_per_criterio(patch_client):
    patch_client("  Quanto è centrale l'AI nella vostra strategia produttiva?  ")
    domanda = intervista.domanda_per_criterio(CRITERIO, CONTESTO)
    # strip applicato.
    assert domanda == "Quanto è centrale l'AI nella vostra strategia produttiva?"


def test_domanda_per_criterio_contesto_none(patch_client):
    fake = patch_client("Una domanda generica?")
    domanda = intervista.domanda_per_criterio(CRITERIO, None)
    assert domanda == "Una domanda generica?"
    # Contesto None -> stringa 'Nessun contesto fornito.' finisce nel prompt user.
    user_msg = fake.calls[0]["messages"][0]["content"]
    assert "Nessun contesto fornito." in user_msg
