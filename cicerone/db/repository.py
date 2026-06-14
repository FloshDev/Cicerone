"""Funzioni alto livello su DB. Niente SQL fuori da qui."""
import json

from .connection import get_connection


def _ensure_contesto_column() -> None:
    """Migration idempotente: ALTER TABLE Assessment ADD contesto_azienda."""
    with get_connection() as conn:
        cols = conn.execute("PRAGMA table_info(Assessment)").fetchall()
        if any(c["name"] == "contesto_azienda" for c in cols):
            return
        conn.execute("ALTER TABLE Assessment ADD COLUMN contesto_azienda TEXT")
        conn.commit()


_ensure_contesto_column()


def lista_criteri(sheet_nome: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.idCriterio, c.nomeCriterio, c.definizione
            FROM Criterio c
            JOIN Sheet s ON c.sheet_id = s.idSheet
            WHERE s.nome = ?
            ORDER BY c.idCriterio
            """,
            (sheet_nome,),
        ).fetchall()
    return [dict(r) for r in rows]


def lista_framework(sheet_nome: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT f.idFramework, f.nomeFramework, f.pdf_path
            FROM Framework f
            JOIN Sheet s ON f.sheet_id = s.idSheet
            WHERE s.nome = ?
            ORDER BY f.idFramework
            """,
            (sheet_nome,),
        ).fetchall()
    return [dict(r) for r in rows]


def crea_assessment(sheet_nome: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO Assessment (sheet_id)
            SELECT idSheet FROM Sheet WHERE nome = ?
            """,
            (sheet_nome,),
        )
        if cur.rowcount == 0:
            raise ValueError(f"Sheet '{sheet_nome}' non trovato")
        conn.commit()
        return cur.lastrowid


def salva_peso(
    assessment_id: int,
    criterio_id: int,
    livello: str,
    peso: float,
    motivazione: str | None = None,
    trascrizione: str | None = None,
    ambiguo: bool = False,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO peso_assessment
                (assessment_id, criterio_id, livello, peso,
                 motivazione, trascrizione, ambiguo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(assessment_id, criterio_id) DO UPDATE SET
                livello      = excluded.livello,
                peso         = excluded.peso,
                motivazione  = excluded.motivazione,
                trascrizione = excluded.trascrizione,
                ambiguo      = excluded.ambiguo
            """,
            (
                assessment_id,
                criterio_id,
                livello,
                peso,
                motivazione,
                trascrizione,
                int(ambiguo),
            ),
        )
        conn.commit()


def salva_contesto(assessment_id: int, contesto: dict) -> None:
    """Salva JSON contesto_azienda su Assessment."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE Assessment SET contesto_azienda = ? WHERE idAssessment = ?",
            (json.dumps(contesto, ensure_ascii=False), assessment_id),
        )
        conn.commit()


def get_contesto(assessment_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT contesto_azienda FROM Assessment WHERE idAssessment = ?",
            (assessment_id,),
        ).fetchone()
    if row is None or row["contesto_azienda"] is None:
        return None
    return json.loads(row["contesto_azienda"])


def get_assessment(assessment_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT a.idAssessment, a.sheet_id, a.framework_vincitore_id,
                   a.contesto_azienda, a.ts, s.nome AS sheet_nome
            FROM Assessment a
            JOIN Sheet s ON a.sheet_id = s.idSheet
            WHERE a.idAssessment = ?
            """,
            (assessment_id,),
        ).fetchone()
    if row is None:
        return None
    d = dict(row)
    if d.get("contesto_azienda"):
        d["contesto_azienda"] = json.loads(d["contesto_azienda"])
    return d


def set_framework_vincitore(assessment_id: int, framework_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE Assessment SET framework_vincitore_id = ? WHERE idAssessment = ?",
            (framework_id, assessment_id),
        )
        conn.commit()


def get_framework(framework_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT idFramework, nomeFramework, pdf_path FROM Framework WHERE idFramework = ?",
            (framework_id,),
        ).fetchone()
    return dict(row) if row else None


def salva_diagnostica(
    assessment_id: int,
    domanda: str,
    risposta_utente: str,
    criterio_id: int | None = None,
    valutazione_llm: str | None = None,
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO Diagnostica
                (assessment_id, criterio_id, domanda, risposta_utente, valutazione_llm)
            VALUES (?, ?, ?, ?, ?)
            """,
            (assessment_id, criterio_id, domanda, risposta_utente, valutazione_llm),
        )
        conn.commit()
        return cur.lastrowid


def storia_diagnostica(assessment_id: int) -> list[dict]:
    """Diagnostica Q&A complete (esclude righe pending con risposta vuota).
    Strip eventuale prefisso interno [RIASK] dalla domanda.
    """
    diags = get_diagnostica(assessment_id)
    risultato = []
    for d in diags:
        if not d["risposta_utente"]:
            continue
        domanda = d["domanda"]
        if domanda.lstrip().startswith("[RIASK]"):
            domanda = domanda.lstrip()[len("[RIASK]"):].lstrip()
        risultato.append({**d, "domanda": domanda, "is_riask": d["domanda"].lstrip().startswith("[RIASK]")})
    return risultato


def update_risposta_diagnostica(diagnostica_id: int, risposta_utente: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE Diagnostica SET risposta_utente = ? WHERE idDiagnostica = ?",
            (risposta_utente, diagnostica_id),
        )
        conn.commit()


def get_diagnostica(assessment_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT idDiagnostica, criterio_id, domanda, risposta_utente, valutazione_llm
            FROM Diagnostica
            WHERE assessment_id = ?
            ORDER BY idDiagnostica
            """,
            (assessment_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_pesi_assessment(assessment_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT pa.criterio_id, c.nomeCriterio, pa.livello, pa.peso,
                   pa.motivazione, pa.trascrizione, pa.ambiguo
            FROM peso_assessment pa
            JOIN Criterio c ON pa.criterio_id = c.idCriterio
            WHERE pa.assessment_id = ?
            ORDER BY pa.criterio_id
            """,
            (assessment_id,),
        ).fetchall()
    return [dict(r) for r in rows]
