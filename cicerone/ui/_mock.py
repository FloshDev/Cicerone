"""Mock temporaneo del modulo MCDA.

Sostituire con cicerone.mcda.calcolo.classifica_framework quando pronto.
Firma allineata a quella concordata col collega.
"""
from cicerone.db.connection import get_connection


def classifica_framework(assessment_id: int) -> list[dict]:
    """Mock: calcola punteggio framework come somma pesata dei voti.

    Per ogni framework, somma su tutti i criteri di voto * peso_assessment.
    Se non ci sono pesi, ritorna i framework con punteggio 0.
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
            WHERE s.nome = 'readiness'
            GROUP BY f.idFramework, f.nomeFramework
            ORDER BY punteggio DESC, f.idFramework
            """,
            (assessment_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def breakdown_per_criterio(assessment_id: int, framework_id: int) -> list[dict]:
    """Dettaglio voto * peso per ogni criterio, per il framework dato."""
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
            WHERE s.nome = 'readiness'
            ORDER BY c.idCriterio
            """,
            (framework_id, assessment_id),
        ).fetchall()
    return [dict(r) for r in rows]
