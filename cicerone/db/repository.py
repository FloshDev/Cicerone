"""Funzioni alto livello su DB. Niente SQL fuori da qui."""
from .connection import get_connection


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
