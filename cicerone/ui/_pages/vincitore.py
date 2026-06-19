"""Pagina vincitore: framework in evidenza, classifica con barre, breakdown."""
from __future__ import annotations

import html

import streamlit as st

from cicerone.ui._pages._shared import (
    mcda,
    vai_a,
    wizard_header,
)


def _hero_html(voce: dict, max_punteggio: float, perche: str) -> str:
    pct = int(round((voce["punteggio"] / max_punteggio) * 100)) if max_punteggio else 0
    return (
        f'<div class="cic-hero">'
        f'<div class="cic-hero-label">Framework consigliato</div>'
        f'<div class="cic-hero-name">{html.escape(voce["nome"])}</div>'
        f'<div class="cic-hero-score">{voce["punteggio"]:.1f} <small>pt</small></div>'
        f'<div class="cic-rank-bar"><div class="cic-rank-bar-fill" '
        f'style="width:{pct}%"></div></div>'
        f'<div class="cic-hero-why">{html.escape(perche)}</div>'
        f'</div>'
    )


def _rank_row_html(rank: int, voce: dict, max_punteggio: float) -> str:
    pct = int(round((voce["punteggio"] / max_punteggio) * 100)) if max_punteggio else 0
    dot_cls = "cic-rank-dot cic-rank-first" if rank == 1 else "cic-rank-dot"
    return (
        f'<div class="cic-rank-row">'
        f'<div class="{dot_cls}">{rank}</div>'
        f'<div class="cic-rank-name">{html.escape(voce["nome"])}</div>'
        f'<div class="cic-rank-bar"><div class="cic-rank-bar-fill" '
        f'style="width:{pct}%"></div></div>'
        f'<div class="cic-rank-score">{voce["punteggio"]:.1f} pt</div>'
        f'</div>'
    )


def _breakdown_html(dettaglio: list[dict]) -> str:
    righe = ""
    for d in dettaglio:
        contributo = round(d["contributo"] or 0, 2)
        righe += (
            f'<tr>'
            f'<td>{html.escape(str(d["nome"]))}</td>'
            f'<td class="cic-num">{d["voto"]}</td>'
            f'<td class="cic-num">{d["peso"]}</td>'
            f'<td class="cic-num cic-contrib">{contributo}</td>'
            f'</tr>'
        )
    return (
        f'<table class="cic-breakdown">'
        f'<thead><tr>'
        f'<th>Criterio</th>'
        f'<th class="cic-num">Voto</th>'
        f'<th class="cic-num">Peso</th>'
        f'<th class="cic-num">Contrib.</th>'
        f'</tr></thead>'
        f'<tbody>{righe}</tbody>'
        f'</table>'
    )


def pagina_vincitore() -> None:
    assessment_id = st.session_state.assessment_id
    if assessment_id is None:
        st.warning("Nessun assessment attivo. Torna all'onboarding.")
        return

    wizard_header("vincitore")
    classifica = mcda.classifica_framework(assessment_id)

    if not classifica:
        st.error("Nessun framework disponibile in DB.")
        return

    max_punteggio = max((v["punteggio"] for v in classifica), default=0) or 1
    vincitore = classifica[0]

    # "Perché": sintesi MCDA — il criterio che contribuisce di più al punteggio
    # del vincitore. Nessun campo motivazione nei dati: lo deriviamo dal breakdown.
    dettaglio_vincitore = mcda.breakdown_per_criterio(assessment_id, vincitore["framework_id"])
    perche = "Punteggio più alto sui pesi che hai espresso."
    contribuenti = [d for d in dettaglio_vincitore if (d["contributo"] or 0) > 0]
    if contribuenti:
        top = max(contribuenti, key=lambda d: d["contributo"] or 0)
        perche = f"Spinto soprattutto dal criterio «{top['nome']}» (contributo {round(top['contributo'] or 0, 1)})."

    st.markdown(_hero_html(vincitore, max_punteggio, perche), unsafe_allow_html=True)

    st.markdown('<div class="cic-card-header">Classifica completa</div>', unsafe_allow_html=True)
    st.caption("Calcolo basato sulla matrice dei voti per i pesi che hai espresso.")
    righe = "".join(
        _rank_row_html(n, v, max_punteggio) for n, v in enumerate(classifica, start=1)
    )
    st.markdown(f'<div class="cic-rank-list">{righe}</div>', unsafe_allow_html=True)

    st.markdown('<div class="cic-card-header">Dettaglio per criterio</div>', unsafe_allow_html=True)
    nomi = [v["nome"] for v in classifica]
    scelto = st.selectbox("Scegli un framework", nomi, index=0)
    framework_id = next(v["framework_id"] for v in classifica if v["nome"] == scelto)
    dettaglio = mcda.breakdown_per_criterio(assessment_id, framework_id)
    st.markdown(_breakdown_html(dettaglio), unsafe_allow_html=True)

    with st.expander("Contesto azienda registrato"):
        st.json(st.session_state.contesto_azienda or {})

    if st.button("Continua alla diagnostica →", type="primary"):
        st.session_state.diag_domanda_corrente = None
        vai_a("diagnostica")
