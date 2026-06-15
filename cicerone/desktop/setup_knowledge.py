"""Funzioni pure per il setup della knowledge base (first-run).

Nessuna dipendenza da pywebview/streamlit né dalle closure di `main()`.
Importa solo da `cicerone.desktop.paths`.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from cicerone.desktop.paths import APP_SUPPORT, KNOWLEDGE_TARGET


def _knowledge_presente(d: Path) -> bool:
    return d.is_dir() and any(d.glob("*.md"))


def _trova_frameworks_dir(root: Path) -> Path | None:
    """Cerca la sottocartella `frameworks/` (con .md) dentro `root`.

    Tollera due layout del repo knowledge:
      root/frameworks/*.md    (atteso)
      root/*.md               (md direttamente in root)
    """
    candidate = root / "frameworks"
    if _knowledge_presente(candidate):
        return candidate
    if _knowledge_presente(root):
        return root
    # Ricerca ricorsiva limitata: prima dir con .md dentro, escluse le nascoste
    for sub in root.rglob("*"):
        if (
            sub.is_dir()
            and any(sub.glob("*.md"))
            and not any(p.startswith(".") for p in sub.relative_to(root).parts)
        ):
            return sub
    return None


def _resolve_knowledge_dev() -> Path | None:
    """In dev, prova a riusare la knowledge nel repo se presente."""
    if getattr(sys, "frozen", False):
        return None
    from cicerone.desktop.paths import _base_path

    candidate = _base_path() / "knowledge" / "frameworks"
    if _knowledge_presente(candidate):
        return candidate
    return None


def _clone_repo_knowledge(token: str, repo_url: str) -> tuple[bool, str]:
    """Clona il repo privato usando il PAT come basic-auth.

    Strategia: rimpiazza `https://` con `https://<token>@` nell'URL. Funziona
    con GitHub PAT classic e fine-grained. Token NON viene salvato.
    """
    if not token.strip():
        return False, "Token vuoto."
    if not repo_url.strip().startswith("https://"):
        return False, "Repo URL deve iniziare con https://"

    auth_url = repo_url.strip().replace("https://", f"https://{token.strip()}@", 1)
    APP_SUPPORT.mkdir(parents=True, exist_ok=True)
    clone_dir = APP_SUPPORT / "knowledge_repo"
    if clone_dir.exists():
        shutil.rmtree(clone_dir)

    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", auth_url, str(clone_dir)],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        return False, "git non disponibile. Installa Xcode Command Line Tools."
    except subprocess.TimeoutExpired:
        return False, "Clone in timeout (120s). Controlla connessione."

    if result.returncode != 0:
        # Filtra il token da eventuali messaggi di errore prima di tornarli
        stderr_safe = result.stderr.replace(token.strip(), "***TOKEN***")
        return False, f"Clone fallito: {stderr_safe.strip()[:300]}"

    src = _trova_frameworks_dir(clone_dir)
    if src is None:
        return False, "Repo clonato ma nessun .md trovato."

    KNOWLEDGE_TARGET.parent.mkdir(parents=True, exist_ok=True)
    if KNOWLEDGE_TARGET.exists():
        shutil.rmtree(KNOWLEDGE_TARGET)
    shutil.copytree(src, KNOWLEDGE_TARGET)
    return True, f"Knowledge installata ({len(list(KNOWLEDGE_TARGET.glob('*.md')))} file)."


def _copia_da_cartella(source_path: str) -> tuple[bool, str]:
    src = Path(source_path).expanduser().resolve()
    if not src.is_dir():
        return False, "Cartella non valida."
    found = _trova_frameworks_dir(src)
    if found is None:
        return False, "Nessun file .md trovato nella cartella indicata."

    KNOWLEDGE_TARGET.parent.mkdir(parents=True, exist_ok=True)
    if KNOWLEDGE_TARGET.exists():
        shutil.rmtree(KNOWLEDGE_TARGET)
    shutil.copytree(found, KNOWLEDGE_TARGET)
    return True, f"Knowledge importata ({len(list(KNOWLEDGE_TARGET.glob('*.md')))} file)."
