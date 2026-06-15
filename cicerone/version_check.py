"""Controllo aggiornamenti via GitHub Releases API.

Confronta la versione installata (da `importlib.metadata`) con l'ultima
release pubblicata sul repository pubblico GitHub. Non blocca l'app:
chiamata HTTP con timeout breve, errori silenziati.

API per UI:
    check_for_update() -> dict {
        "current": str,        # versione installata (es. "0.1.1")
        "latest": str | None,  # versione ultima release (es. "0.1.2") o None se check fallito
        "has_update": bool,    # True se latest > current
        "url": str | None,     # link alla release (es. https://.../releases/tag/v0.1.2)
        "error": str | None,   # messaggio errore se check fallito
    }
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from importlib.metadata import PackageNotFoundError, version

GITHUB_API_LATEST = "https://api.github.com/repos/FloshDev/Cicerone/releases/latest"
HTTP_TIMEOUT = 3.0


def _current_version() -> str:
    try:
        return version("cicerone")
    except PackageNotFoundError:
        return "0.0.0"


def _parse_semver(v: str) -> tuple[int, int, int]:
    """Parser tollerante: rimuove prefisso v, ignora suffissi (-rc1, +meta)."""
    v = v.strip().lstrip("v")
    core = v.split("-", 1)[0].split("+", 1)[0]
    parts = (core.split(".") + ["0", "0", "0"])[:3]
    out: list[int] = []
    for p in parts:
        try:
            out.append(int(p))
        except ValueError:
            out.append(0)
    return out[0], out[1], out[2]


def _is_newer(latest: str, current: str) -> bool:
    return _parse_semver(latest) > _parse_semver(current)


def check_for_update() -> dict:
    current = _current_version()
    result: dict = {
        "current": current,
        "latest": None,
        "has_update": False,
        "url": None,
        "error": None,
    }

    req = urllib.request.Request(
        GITHUB_API_LATEST,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"Cicerone/{current}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            if resp.status != 200:
                result["error"] = f"HTTP {resp.status}"
                return result
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # 404 = nessuna release pubblicata (repo nuovo): non è un errore utente
        if e.code == 404:
            result["error"] = "nessuna release pubblicata"
            return result
        result["error"] = f"HTTP {e.code}"
        return result
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        result["error"] = "offline"
        return result
    except (json.JSONDecodeError, ValueError):
        result["error"] = "risposta GitHub non valida"
        return result

    latest_tag = (payload.get("tag_name") or "").strip()
    if not latest_tag:
        result["error"] = "tag_name mancante"
        return result

    result["latest"] = latest_tag.lstrip("v")
    result["url"] = payload.get("html_url")
    result["has_update"] = _is_newer(latest_tag, current)
    return result
