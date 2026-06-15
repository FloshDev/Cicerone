"""Path e costanti condivise del launcher desktop.

Modulo standalone: nessun import da altri moduli del package `desktop`.
Risolve i path dati sia in dev sia dentro un bundle PyInstaller e forza la
DB su una location scrivibile.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_SUPPORT = Path.home() / "Library" / "Application Support" / "Cicerone"
KNOWLEDGE_TARGET = APP_SUPPORT / "knowledge" / "frameworks"
DEFAULT_REPO_URL = "https://github.com/FloshDev/cicerone-knowledge.git"


def _base_path() -> Path:
    """Radice da cui risolvere i file dati.

    In bundle PyInstaller `sys._MEIPASS` punta alla cartella con tutti i
    dati raccolti dallo spec. In dev usa la root del repo.
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent.parent


def _setup_db_path() -> Path:
    """Forza la DB su una location scrivibile.

    In bundle l'app è read-only: serve una directory utente. In dev
    rispetta il default di `cicerone.db.connection` (data/ nel repo).
    """
    if getattr(sys, "frozen", False):
        APP_SUPPORT.mkdir(parents=True, exist_ok=True)
        db_path = APP_SUPPORT / "cicerone.sqlite"
    else:
        support = _base_path() / "cicerone" / "data"
        support.mkdir(parents=True, exist_ok=True)
        db_path = support / "cicerone.sqlite"
    os.environ["CICERONE_DB_PATH"] = str(db_path)
    return db_path
