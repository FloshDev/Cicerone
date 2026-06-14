# Cicerone

> La guida per la tua PMI nell'adozione dell'AI.

Cicerone è un agente AI conversazionale che aiuta le PMI a valutare la propria **AI Readiness** scegliendo il framework di maturità più adatto, diagnosticando lo stato attuale e producendo un report pratico con i passi per arrivare allo stato auspicato.

Progetto universitario in sviluppo, scritto in Python + Streamlit, basato su Claude (Anthropic).

---

## Stato del progetto

**Fase 1 — Readiness assessment** (in corso).
Fase 2 — Implementation assessment (rinviata).

---

## Requisiti

- Python 3.11+
- [`uv`](https://github.com/astral-sh/uv) — gestore di progetto
- Account [Anthropic](https://console.anthropic.com/) con API key
- Accesso al repo privato `cicerone-knowledge` (vedi sezione [Knowledge base](#knowledge-base))

---

## Setup

```bash
# 1. Clona il repo
git clone https://github.com/FloshDev/cicerone.git
cd cicerone

# 2. Installa dipendenze e ambiente virtuale
uv sync

# 3. Configura la tua API key Anthropic
cp .env.example .env
# poi modifica .env e inserisci la tua ANTHROPIC_API_KEY

# 4. Scarica il knowledge base privato dentro knowledge/ (vedi sezione sotto)
git clone https://github.com/FloshDev/cicerone-knowledge.git knowledge

# 5. Avvia l'app
streamlit run cicerone/main.py
```

---

## Knowledge base

Cicerone consulta una base di conoscenza derivata da paper accademici sui framework di AI Readiness/Maturity. Per ragioni di copyright dei materiali sorgente, questa knowledge base **non è distribuita pubblicamente** ma vive in un repo privato separato: `cicerone-knowledge`.

L'accesso al repo privato è riservato a:
- Sviluppatore del progetto
- Docente relatore
- Colleghi del corso autorizzati

Per richiedere accesso: [ciani.flavio04@gmail.com](mailto:ciani.flavio04@gmail.com).

La cartella `knowledge/` non è inclusa nel repo pubblico (è interamente esclusa via `.gitignore`). Dopo aver ottenuto accesso al repo privato, va clonata al suo posto (vedi step 4 del setup).

---

## Struttura del progetto

```
cicerone/                       # package Python (codice tool)
├── main.py                     # entry point Streamlit
├── config.py                   # caricamento .env
├── db/                         # schema, seed, repository SQLite
├── llm/                        # client Anthropic, prompt, tool use
├── mcda/                       # calcolo MCDA (vincitore framework)
├── ui/                         # pagine Streamlit
└── data/                       # DB locale (runtime, gitignored)
knowledge/                      # KB privato (clonato a parte)
MatriceDB.xlsx                  # template seed criteri/framework/voti
Criteri ReadinessMaturity.docx  # definizioni criteri
```

---

## Documentazione

- [`CICERONE_PLAN.md`](CICERONE_PLAN.md) — piano tecnico completo (Fase A) e report colleghi (Fase B)
- [`CICERONE_CONTEXT.md`](CICERONE_CONTEXT.md) — contesto di sessione: decisioni di design, stato sviluppo

---

## Licenza

Codice rilasciato sotto licenza [MIT](LICENSE).

Il contenuto del knowledge base privato (`cicerone-knowledge`) è soggetto a termini d'uso interno separati — non è coperto dalla licenza MIT di questo repo.
