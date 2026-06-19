"""Unit test per cicerone.mcda.calcolo: classifica + breakdown.

Strategia deterministica: NON assumiamo i voti reali della MatriceDB.
Assegniamo pesi noti su tutti i criteri e verifichiamo proprietà invarianti:
- la classifica è ordinata per punteggio DESC;
- il punteggio di un framework == somma dei contributi del suo breakdown;
- ogni contributo == voto * peso;
- il vincitore coincide con la testa della classifica.
"""
from cicerone.db import repository
from cicerone.mcda import calcolo


def _pesa_tutti(assessment_id, peso=10.0, livello="Fondamentale"):
    """Assegna lo stesso peso a tutti i criteri rediness."""
    for c in repository.lista_criteri("rediness"):
        repository.salva_peso(assessment_id, c["idCriterio"], livello, peso)


def test_classifica_ordinata_desc(assessment_id):
    _pesa_tutti(assessment_id, peso=10.0)
    classifica = calcolo.classifica_framework(assessment_id)

    assert len(classifica) == len(repository.lista_framework("rediness"))
    for r in classifica:
        assert set(r.keys()) == {"framework_id", "nome", "punteggio"}

    punteggi = [r["punteggio"] for r in classifica]
    # Ordinamento decrescente per punteggio.
    assert punteggi == sorted(punteggi, reverse=True)
    # Con pesi tutti = 10 e voti >= 0, almeno un framework deve avere punteggio > 0.
    assert max(punteggi) > 0


def test_classifica_senza_pesi_tutti_zero(assessment_id):
    """Nessun peso salvato -> COALESCE/LEFT JOIN -> punteggi 0, ma righe presenti."""
    classifica = calcolo.classifica_framework(assessment_id)
    assert len(classifica) == len(repository.lista_framework("rediness"))
    assert all(r["punteggio"] == 0 for r in classifica)


def test_breakdown_coerente_con_classifica(assessment_id):
    _pesa_tutti(assessment_id, peso=7.5, livello="Importante")
    classifica = calcolo.classifica_framework(assessment_id)
    vincitore = classifica[0]

    breakdown = calcolo.breakdown_per_criterio(assessment_id, vincitore["framework_id"])
    assert len(breakdown) > 0
    for riga in breakdown:
        assert set(riga.keys()) == {"criterio_id", "nome", "voto", "peso", "contributo"}
        # contributo == voto * peso (peso = 7.5 ovunque qui).
        assert riga["peso"] == 7.5
        assert riga["contributo"] == riga["voto"] * riga["peso"]

    # Somma contributi del breakdown == punteggio del framework in classifica.
    somma = sum(r["contributo"] for r in breakdown)
    assert somma == vincitore["punteggio"]


def test_breakdown_peso_mancante_e_none(assessment_id):
    """Se non ci sono pesi, peso e contributo sono None (LEFT JOIN)."""
    framework = repository.lista_framework("rediness")[0]
    breakdown = calcolo.breakdown_per_criterio(assessment_id, framework["idFramework"])
    assert len(breakdown) > 0
    for riga in breakdown:
        assert riga["peso"] is None
        assert riga["contributo"] is None
        assert riga["voto"] is not None


def test_vincitore_e_testa_classifica(assessment_id):
    _pesa_tutti(assessment_id, peso=5.0, livello="Abbastanza importante")
    classifica = calcolo.classifica_framework(assessment_id)
    vinc = calcolo.vincitore(assessment_id)
    assert vinc == classifica[0]


def test_pesi_diversi_cambiano_ordine(assessment_id):
    """Verifica che il punteggio dipende effettivamente dai pesi:
    classifiche con pesi diversi producono punteggi diversi (non degenere)."""
    _pesa_tutti(assessment_id, peso=10.0, livello="Fondamentale")
    alti = {r["framework_id"]: r["punteggio"] for r in calcolo.classifica_framework(assessment_id)}

    _pesa_tutti(assessment_id, peso=2.5, livello="Poco importante")
    bassi = {r["framework_id"]: r["punteggio"] for r in calcolo.classifica_framework(assessment_id)}

    # Con peso 1/4, ogni punteggio diventa 1/4 (stessi voti).
    for fid, p_alto in alti.items():
        assert bassi[fid] == p_alto / 4
