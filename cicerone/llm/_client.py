"""Client Anthropic condiviso. Permette override API key da UI runtime."""
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

_api_key_override: str | None = None


def set_api_key(api_key: str | None) -> None:
    """Setta la chiave usata per le call successive. Passa None per resettare."""
    global _api_key_override
    _api_key_override = api_key.strip() if api_key else None


def get_client() -> Anthropic:
    """Ritorna client Anthropic. Usa override UI se settato, altrimenti env."""
    if _api_key_override:
        return Anthropic(api_key=_api_key_override)
    return Anthropic()  # fallback: legge ANTHROPIC_API_KEY da env
