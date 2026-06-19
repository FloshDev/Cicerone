"""MCDA: classifica framework per assessment via SUMPRODUCT peso × voto.

Equivalente SQL della formula Excel SUMPRODUCT. Pesi mancanti contano come 0
(LEFT JOIN), coerente con cella vuota in Excel.
"""
from cicerone.db.connection import get_connection


def classifica_framework(assessment_id: int) -> list[dict]:
    """Lista framework ordinata per punteggio decrescente.

    Ogni dict: {framework_id, nome, punteggio}.
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT f.idFramework AS framework_id,
                   f.nomeFramework AS nome,
                   COALESCE(SUM(v.voto * pa.peso), 0) AS punteggio
            FROM Framework f
            LEFT JOIN Voto v ON v.framework_id = f.idFramework
            LEFT JOIN peso_assessment pa
                   ON pa.criterio_id = v.criterio_id
                  AND pa.assessment_id = ?
            JOIN Sheet s ON f.sheet_id = s.idSheet
            WHERE s.nome = 'rediness'
            GROUP BY f.idFramework, f.nomeFramework
            ORDER BY punteggio DESC, f.idFramework
            """,
            (assessment_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def breakdown_per_criterio(assessment_id: int, framework_id: int) -> list[dict]:
    """Per ogni criterio: voto framework, peso utente, contributo (voto*peso)."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.idCriterio AS criterio_id,
                   c.nomeCriterio AS nome,
                   v.voto AS voto,
                   pa.peso AS peso,
                   (v.voto * pa.peso) AS contributo
            FROM Criterio c
            JOIN Voto v ON v.criterio_id = c.idCriterio AND v.framework_id = ?
            LEFT JOIN peso_assessment pa
                   ON pa.criterio_id = c.idCriterio
                  AND pa.assessment_id = ?
            JOIN Sheet s ON c.sheet_id = s.idSheet
            WHERE s.nome = 'rediness'
            ORDER BY c.idCriterio
            """,
            (framework_id, assessment_id),
        ).fetchall()
    return [dict(r) for r in rows]


def vincitore(assessment_id: int) -> dict | None:
    """Framework vincitore (primo in classifica). None se nessun assessment."""
    classifica = classifica_framework(assessment_id)
    return classifica[0] if classifica else None
