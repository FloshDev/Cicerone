"""Pagina vincitore: classifica framework, dettaglio per criterio, contesto."""
from __future__ import annotations

import streamlit as st

from cicerone.ui._pages._shared import (
    divider_cicerone,
    header_cicerone,
    mcda,
    vai_a,
)


def _card_framework(medaglia: str, voce: dict) -> str:
    return (
        f'<div class="cic-card">'
        f'<div class="cic-card-medal">{medaglia}</div>'
        f'<div class="cic-card-body">'
        f'<div class="cic-card-name">{voce["nome"]}</div>'
        f'<div class="cic-card-score">{voce["punteggio"]:.1f} pt</div>'
        f'</div>'
        f'</div>'
    )


def pagina_vincitore() -> None:
    assessment_id = st.session_state.assessment_id
    if assessment_id is None:
        st.warning("Nessun assessment attivo. Torna all'onboarding.")
        return

    header_cicerone()
    classifica = mcda.classifica_framework(assessment_id)
    st.subheader("Framework più adatti")
    st.caption("Calcolo basato sulla matrice dei voti per i pesi che hai espresso.")

    if not classifica:
        st.error("Nessun framework disponibile in DB.")
        return

    top3 = classifica[:3]
    medaglie = ["I", "II", "III"]
    cards_html = "".join(_card_framework(m, v) for m, v in zip(medaglie, top3, strict=False))
    st.markdown(f'<div class="cic-cards">{cards_html}</div>', unsafe_allow_html=True)

    divider_cicerone()
    st.subheader("Classifica completa")
    st.dataframe(
        [{"Framework": v["nome"], "Punteggio": round(v["punteggio"], 2)} for v in classifica],
        use_container_width=True,
        hide_index=True,
    )

    divider_cicerone()
    st.subheader("Dettaglio per criterio")
    nomi = [v["nome"] for v in classifica]
    scelto = st.selectbox("Scegli un framework", nomi, index=0)
    framework_id = next(v["framework_id"] for v in classifica if v["nome"] == scelto)
    dettaglio = mcda.breakdown_per_criterio(assessment_id, framework_id)
    st.dataframe(
        [
            {
                "Criterio": d["nome"],
                "Voto framework": d["voto"],
                "Peso utente": d["peso"],
                "Contributo": round(d["contributo"] or 0, 2),
            }
            for d in dettaglio
        ],
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Contesto azienda registrato"):
        st.json(st.session_state.contesto_azienda or {})

    divider_cicerone()
    if st.button("Continua alla diagnostica →", type="primary"):
        st.session_state.diag_domanda_corrente = None
        vai_a("diagnostica")
