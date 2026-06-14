"""Mock temporaneo per moduli backend non ancora pubblicati.

Coperti:
- MCDA: classifica_framework, breakdown_per_criterio
- LLM diagnostica: next_question
- LLM report: genera_report
- repository: salva_contesto

Quando i moduli veri sono pubblicati, l'app.py li importa automaticamente
e questi mock smettono di essere chiamati.
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


# ---------- diagnostica ----------

_DOMANDE_MOCK = [
    "Avete già identificato un processo aziendale specifico dove vorreste introdurre l'AI?",
    "Quali dati avete a disposizione per allenare o alimentare un sistema AI?",
    "Esiste in azienda una figura tecnica che possa gestire l'integrazione?",
    "Quali sono i principali vincoli (budget, tempo, compliance) che vedete?",
]


def next_question(assessment_id: int, risposta_precedente: str | None) -> str | None:
    """Mock: ritorna una domanda alla volta finché finisce la lista.

    Usa il numero di Q&A già salvate in tabella Diagnostica per scegliere
    quale domanda mostrare. Salva la Q&A precedente in tabella.
    """
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT COUNT(*) FROM Diagnostica WHERE assessment_id = ?",
            (assessment_id,),
        ).fetchone()[0]

        if risposta_precedente is not None and existing < len(_DOMANDE_MOCK):
            conn.execute(
                """
                INSERT INTO Diagnostica
                    (assessment_id, criterio_id, domanda, risposta_utente, valutazione_llm)
                VALUES (?, NULL, ?, ?, ?)
                """,
                (
                    assessment_id,
                    _DOMANDE_MOCK[existing],
                    risposta_precedente,
                    "mock: valutazione automatica",
                ),
            )
            conn.commit()
            existing += 1

        if existing >= len(_DOMANDE_MOCK):
            return None
        return _DOMANDE_MOCK[existing]


def storia_diagnostica(assessment_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT domanda, risposta_utente
            FROM Diagnostica
            WHERE assessment_id = ?
            ORDER BY idDiagnostica
            """,
            (assessment_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------- report ----------

def genera_report(assessment_id: int) -> str:
    """Mock: report markdown sintetico assemblato dai dati in DB."""
    with get_connection() as conn:
        ass = conn.execute(
            "SELECT idAssessment, ts FROM Assessment WHERE idAssessment = ?",
            (assessment_id,),
        ).fetchone()
        pesi = conn.execute(
            """
            SELECT c.nomeCriterio, pa.livello, pa.peso, pa.motivazione
            FROM peso_assessment pa
            JOIN Criterio c ON c.idCriterio = pa.criterio_id
            WHERE pa.assessment_id = ?
            ORDER BY pa.criterio_id
            """,
            (assessment_id,),
        ).fetchall()
        diagnostica = conn.execute(
            """
            SELECT domanda, risposta_utente
            FROM Diagnostica
            WHERE assessment_id = ?
            ORDER BY idDiagnostica
            """,
            (assessment_id,),
        ).fetchall()

    top = classifica_framework(assessment_id)[:3]

    righe = [
        f"# Report AI Readiness — Assessment #{ass['idAssessment']}",
        "",
        f"_Data: {ass['ts']}_",
        "",
        "> Nota: report generato con mock provvisorio in attesa del modulo LLM.",
        "",
        "## Framework consigliati",
        "",
    ]
    for i, v in enumerate(top, 1):
        righe.append(f"{i}. **{v['nome']}** — punteggio {v['punteggio']:.1f}")
    righe.append("")
    righe.append("## Profilo di importanza dichiarato")
    righe.append("")
    for p in pesi:
        riga = f"- **{p['nomeCriterio']}** → {p['livello']} (peso {p['peso']})"
        if p["motivazione"]:
            riga += f"\n  _\"{p['motivazione']}\"_"
        righe.append(riga)

    if diagnostica:
        righe.append("")
        righe.append("## Diagnostica")
        righe.append("")
        for d in diagnostica:
            righe.append(f"**Q:** {d['domanda']}")
            righe.append(f"**A:** {d['risposta_utente']}")
            righe.append("")

    return "\n".join(righe)


# ---------- contesto azienda ----------

def salva_contesto(assessment_id: int, contesto: dict) -> None:
    """Mock no-op: il backend non ha ancora aggiunto la colonna contesto_azienda.

    Quando la migration ALTER TABLE è applicata e repo.salva_contesto esiste,
    questo fallback smette di essere chiamato.
    """
    return None
