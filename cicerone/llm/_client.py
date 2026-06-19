"""Layer LLM provider-agnostico via litellm. Permette override di API key e
modello da UI runtime, così l'utente può usare il provider che preferisce."""
import os

import litellm
from dotenv import load_dotenv

load_dotenv()

_api_key_override: str | None = None
_model_override: str | None = None


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
    Ritorna il testo della risposta."""
    composti = [{"role": "system", "content": system}] + messages
    resp = litellm.completion(
        model=get_model(),
        messages=composti,
        max_tokens=max_tokens,
        api_key=_api_key_override or None,
    )
    return resp.choices[0].message.content
