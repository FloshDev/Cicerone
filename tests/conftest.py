"""Fixture di base per la suite Cicerone.

ISOLAMENTO DB (critico): `cicerone.db.connection` legge il path del DB dalla
env var `CICERONE_DB_PATH` *a import-time* (livello-modulo). Quindi qui, PRIMA
di importare qualsiasi modulo `cicerone.db`, settiamo la env var verso un file
SQLite in una cartella temporanea dedicata alla sessione di test. Solo dopo
applichiamo lo schema e popoliamo col seed reale.
"""
import os
import tempfile
from pathlib import Path

# --- 1. Env var DB temporaneo PRIMA di ogni import di cicerone.db -------------
_TMP_DIR = tempfile.mkdtemp(prefix="cicerone_test_db_")
_DB_PATH = Path(_TMP_DIR) / "cicerone_test.sqlite"
os.environ["CICERONE_DB_PATH"] = str(_DB_PATH)

# Evita che il client Anthropic provi a leggere una chiave reale / fare rete
# se qualche import laterale dovesse istanziarlo. Non serve per i test
# (il client è monkeypatchato), ma rende l'ambiente deterministico.
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-used")

# --- 2. Applica schema + seed una sola volta per sessione --------------------
SCHEMA_SQL = Path(__file__).parent.parent / "cicerone" / "db" / "schema.sql"


def _init_db_once() -> None:
    # Import qui (dopo il set della env var) per garantire il path giusto.
    from cicerone.db.connection import get_connection

    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL.read_text(encoding="utf-8"))
        conn.commit()

    # Seed reale: legge MatriceDB.xlsx + Criteri_Rediness_Maturity.md da resources/.
    from cicerone.db import seed

    seed.run_if_needed()


_init_db_once()

import pytest  # noqa: E402  (import dopo init DB per simmetria/leggibilità)


@pytest.fixture
def db_path() -> Path:
    """Path del DB temporaneo di test."""
    return _DB_PATH


@pytest.fixture
def assessment_id():
    """Crea un assessment fresco sullo sheet 'rediness' per ogni test che lo
    richiede. Ogni assessment ha un id distinto -> indipendenza dall'ordine.
    """
    from cicerone.db import repository

    return repository.crea_assessment("rediness")
