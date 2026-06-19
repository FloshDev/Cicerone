"""Layer LLM provider-agnostico via litellm. Permette override di API key e
modello da UI runtime, così l'utente può usare il provider che preferisce."""
import os

import litellm
from dotenv import load_dotenv

load_dotenv()

# I provider che non supportano un parametro lo ignorano invece di sollevare
# (es. reasoning_effort su modelli non-thinking).
litellm.drop_params = True

_api_key_override: str | None = None
_model_override: str | None = None


class LLMError(Exception):
    """Errore di una chiamata al modello, con messaggio già pronto per l'utente
    (no traceback). Sollevato da complete() mappando le eccezioni litellm."""


def set_api_key(api_key: str | None) -> None:
    """Setta la chiave usata per le call successive. Passa None per resettare."""
    global _api_key_override
    _api_key_override = api_key.strip() if api_key else None


def set_model(model: str | None) -> None:
    """Setta il modello usato per le call successive. Passa None per resettare."""
    global _model_override
    _model_override = model.strip() if model else None


def get_model() -> str:
    """Ritorna il modello: override UI se settato, altrimenti env CICERONE_MODEL,
    altrimenti default."""
    if _model_override:
        return _model_override
    return os.environ.get("CICERONE_MODEL") or "anthropic/claude-sonnet-4-6"


def complete(system: str, messages: list, max_tokens: int) -> str:
    """Unico helper applicativo: compone system + messages e chiama litellm.
    Ritorna il testo della risposta.

    Sui modelli con thinking attivo di default (Gemini 2.5) passiamo
    `reasoning_effort="disable"`: senza, i token di ragionamento consumano il
    budget `max_tokens` e troncano la risposta. NON lo passiamo ad altri
    provider (es. Anthropic) perché il loro default è già senza thinking e il
    parametro genererebbe una richiesta malformata (BadRequest)."""
    model = get_model()
    composti = []
    if system and system.strip():
        composti.append({"role": "system", "content": system})
    composti += messages

    extra: dict = {}
    if "gemini" in model.lower():
        extra["reasoning_effort"] = "disable"

    try:
        resp = litellm.completion(
            model=model,
            messages=composti,
            max_tokens=max_tokens,
            api_key=_api_key_override or None,
            **extra,
        )
    except litellm.RateLimitError as e:
        raise LLMError("Limite richieste raggiunto") from e
    except litellm.AuthenticationError as e:
        raise LLMError("Chiave non valida") from e
    except litellm.NotFoundError as e:
        raise LLMError("Modello non trovato") from e
    except litellm.BadRequestError as e:
        raise LLMError("Modello o chiave non validi") from e
    except Exception as e:
        raise LLMError("Errore del modello") from e
    return resp.choices[0].message.content
