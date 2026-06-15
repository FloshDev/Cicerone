import os
import sqlite3
from pathlib import Path

DB_PATH = (
    Path(os.environ["CICERONE_DB_PATH"])
    if os.environ.get("CICERONE_DB_PATH")
    else Path(__file__).parent.parent / "data" / "cicerone.sqlite"
)


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn
