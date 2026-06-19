"""Unit test per cicerone.db.repository (CRUD su DB temporaneo seedato)."""
from cicerone.db import repository


def test_lista_criteri_rediness():
    criteri = repository.lista_criteri("rediness")
    # Il seed inserisce esattamente N_CRITERI = 10 criteri per 'rediness'.
    assert len(criteri) == 10
    primo = criteri[0]
    assert set(primo.keys()) == {"idCriterio", "nomeCriterio", "definizione"}
    assert all(c["nomeCriterio"] for c in criteri)
    # Ordinati per idCriterio crescente.
    ids = [c["idCriterio"] for c in criteri]
    assert ids == sorted(ids)


def test_lista_criteri_sheet_inesistente_vuoto():
    assert repository.lista_criteri("non_esiste") == []


def test_lista_framework_rediness():
    framework = repository.lista_framework("rediness")
    assert len(framework) > 0
    primo = framework[0]
    assert set(primo.keys()) == {"idFramework", "nomeFramework", "pdf_path"}
    ids = [f["idFramework"] for f in framework]
    assert ids == sorted(ids)


def test_crea_assessment_ritorna_id_crescente():
    a1 = repository.crea_assessment("rediness")
    a2 = repository.crea_assessment("rediness")
    assert isinstance(a1, int)
    assert a2 > a1
    rec = repository.get_assessment(a1)
    assert rec is not None
    assert rec["sheet_nome"] == "rediness"


def test_crea_assessment_sheet_inesistente_solleva():
    import pytest

    with pytest.raises(ValueError):
        repository.crea_assessment("non_esiste")


def test_salva_peso_inserisce(assessment_id):
    criterio = repository.lista_criteri("rediness")[0]
    repository.salva_peso(
        assessment_id,
        criterio["idCriterio"],
        livello="Importante",
        peso=7.5,
        motivazione="motivazione iniziale",
        trascrizione="risposta utente",
        ambiguo=False,
    )
    pesi = repository.get_pesi_assessment(assessment_id)
    assert len(pesi) == 1
    p = pesi[0]
    assert p["criterio_id"] == criterio["idCriterio"]
    assert p["livello"] == "Importante"
    assert p["peso"] == 7.5
    assert p["motivazione"] == "motivazione iniziale"
    assert p["trascrizione"] == "risposta utente"
    assert p["ambiguo"] == 0


def test_salva_peso_upsert_sovrascrive(assessment_id):
    """La seconda salva_peso sullo stesso (assessment, criterio) deve fare
    UPDATE (UPSERT), non creare una seconda riga."""
    criterio = repository.lista_criteri("rediness")[0]
    cid = criterio["idCriterio"]

    repository.salva_peso(
        assessment_id, cid, livello="Poco importante", peso=2.5,
        motivazione="vecchia", trascrizione="vecchia trasc", ambiguo=True,
    )
    repository.salva_peso(
        assessment_id, cid, livello="Fondamentale", peso=10.0,
        motivazione="nuova", trascrizione="nuova trasc", ambiguo=False,
    )

    pesi = repository.get_pesi_assessment(assessment_id)
    assert len(pesi) == 1  # una sola riga: riscrittura, non append
    p = pesi[0]
    assert p["livello"] == "Fondamentale"
    assert p["peso"] == 10.0
    assert p["motivazione"] == "nuova"
    assert p["trascrizione"] == "nuova trasc"
    assert p["ambiguo"] == 0


def test_salva_peso_isolato_per_assessment():
    """Pesi di assessment diversi non si mescolano."""
    a1 = repository.crea_assessment("rediness")
    a2 = repository.crea_assessment("rediness")
    criteri = repository.lista_criteri("rediness")
    repository.salva_peso(a1, criteri[0]["idCriterio"], "Importante", 7.5)
    repository.salva_peso(a2, criteri[1]["idCriterio"], "Fondamentale", 10.0)

    assert len(repository.get_pesi_assessment(a1)) == 1
    assert len(repository.get_pesi_assessment(a2)) == 1
    assert repository.get_pesi_assessment(a1)[0]["criterio_id"] == criteri[0]["idCriterio"]


def test_salva_e_get_contesto_roundtrip(assessment_id):
    contesto = {
        "settore": "manifatturiero",
        "dimensione": "50 dipendenti",
        "note": "città: Brescià — apostrofo's & accenti",
    }
    repository.salva_contesto(assessment_id, contesto)
    letto = repository.get_contesto(assessment_id)
    assert letto == contesto


def test_get_contesto_none_se_non_settato(assessment_id):
    assert repository.get_contesto(assessment_id) is None
