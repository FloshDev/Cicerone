# Cicerone

> La guida per la tua PMI nell'adozione dell'AI.

**Cicerone** è un agente AI conversazionale che aiuta le PMI italiane ed
europee a valutare la propria **AI Readiness/Maturity** scegliendo il
framework accademico più adatto al loro contesto (11 framework disponibili),
conducendo una diagnostica multi-turno guidata da LLM e producendo un
report finale personalizzato con roadmap prioritizzata e KPI da monitorare.

Progetto universitario, scritto in Python + Streamlit, basato su modelli
Anthropic Claude (Haiku 4.5 e Sonnet 4.6).

---

## Cosa fa

1. **Onboarding** — l'utente inserisce nome azienda, settore, dimensione,
   nazione (EU 27 + Svizzera + UK), uso AI attuale, fatturato.
2. **Intervista LLM** — per ciascuno dei 10 criteri MCDA, Claude genera una
   domanda tarata su settore e contesto. L'utente risponde in libertà,
   l'LLM inferisce il livello di importanza (5 livelli, peso 0-10) e segnala
   eventuali ambiguità.
3. **Calcolo MCDA** — SUMPRODUCT (peso × voto) sui 11 framework: il
   ranking determina il framework vincitore.
4. **Diagnostica multi-turno** — Claude approfondisce con 3-7 domande
   mirate sui gap dell'azienda rispetto al framework vincitore. Su risposte
   vaghe, rifa la stessa domanda in modo più specifico (max 2 re-domande
   per sessione).
5. **Report finale** — markdown personalizzato con: profilo, framework
   consigliato e perché, gap di maturità, roadmap P1/P2/P3 motivata, KPI
   con baseline e target. Scaricabile.

---

## Requisiti

- Python 3.11+
- [`uv`](https://github.com/astral-sh/uv) — gestore di progetto
- Account [Anthropic](https://console.anthropic.com/) con API key (~$5
  di credito sono sufficienti per molti assessment di prova)
- (Opzionale ma raccomandato) Accesso al repo privato `cicerone-knowledge`
  per attivare diagnostica e report con knowledge base completa

---

## Setup (5 minuti)

```bash
# 1. Clona il repo
git clone https://github.com/FloshDev/cicerone.git
cd cicerone

# 2. Installa dipendenze (crea automaticamente .venv)
uv sync

# 3. Clona il knowledge base privato dentro knowledge/ (richiede accesso)
git clone https://github.com/FloshDev/cicerone-knowledge.git knowledge
# Se non hai accesso: salta questo passo. L'app funziona comunque
# (intervista + MCDA + vincitore), ma diagnostica e report saranno generici.

# 4. (Opzionale) crea .env con la tua chiave Anthropic
echo "ANTHROPIC_API_KEY=sk-ant-api03-..." > .env
# In alternativa puoi incollare la chiave direttamente nella UI
# (campo nella sidebar). Non viene mai salvata su disco.

# 5. Avvia l'app
uv run streamlit run cicerone/ui/app.py
```

L'app apre il browser su `http://localhost:8501`.

Al primo avvio:
- Schema SQLite applicato automaticamente
- Seed di 10 criteri + 11 framework + 110 voti MCDA dal `MatriceDB.xlsx`
- DB locale persistente in `cicerone/data/cicerone.sqlite` (gitignored)

---

## Configurazione API key Anthropic

Due modi, equivalenti:

**A) Tramite UI (consigliato per demo / utenti finali)**
- Apri l'app, incolla `sk-ant-api03-...` nel campo della sidebar
- Vale solo per la sessione corrente, mai persistita

**B) Tramite file `.env` (consigliato per sviluppo)**
```bash
echo "ANTHROPIC_API_KEY=sk-ant-api03-..." > .env
```
Letto automaticamente all'avvio. `.env` è gitignored.

Se entrambi presenti, la chiave da UI ha precedenza.

**Stima costo:** una sessione completa (intervista + diagnostica + report)
consuma ~$0.05–0.10 di credito Anthropic. $20 di credito = mesi di utilizzo.

---

## Knowledge base (`cicerone-knowledge`)

Cicerone consulta una base di conoscenza derivata da 11 paper accademici sui
framework di AI Readiness/Maturity. Per ragioni di copyright dei materiali
sorgente, questa knowledge base **non è distribuita pubblicamente** ma vive
in un repo privato separato: `cicerone-knowledge`.

L'accesso è riservato a:
- Sviluppatore del progetto
- Docente relatore
- Colleghi del corso autorizzati

Per richiedere accesso: [ciani.flavio04@gmail.com](mailto:ciani.flavio04@gmail.com).

**Dopo aver ottenuto accesso**, clona il repo dentro `knowledge/` del repo
principale:
```bash
git clone https://github.com/FloshDev/cicerone-knowledge.git knowledge
```

La cartella `knowledge/` è esclusa via `.gitignore` dal repo pubblico —
sono due repository Git indipendenti.

**Cosa succede senza knowledge base**: l'app si avvia comunque (intervista
+ calcolo MCDA + classifica framework funzionano), ma diagnostica e report
generano contenuto generico perché manca il dettaglio del framework
vincitore. Vedi sezione [Senza knowledge base](#senza-knowledge-base).

### Senza knowledge base

Se non hai accesso al repo privato, puoi comunque:
- Esplorare l'intervista LLM-guidata sui 10 criteri
- Vedere il calcolo MCDA e la classifica dei framework
- Sperimentare l'architettura del prodotto

Cosa NON funzionerà bene:
- Diagnostica: domande meno specifiche perché manca il dettaglio del
  framework target
- Report: roadmap e KPI meno calzanti perché manca il modello di maturità
  dettagliato

---

## Struttura del progetto

```
cicerone/                       # package Python
├── ui/
│   └── app.py                  # entry point Streamlit (onboarding,
│                               #   intervista, vincitore, diagnostica, report)
├── db/
│   ├── schema.sql              # DDL 7 tabelle
│   ├── connection.py           # helper get_connection()
│   ├── seed.py                 # popolamento idempotente da Excel
│   └── repository.py           # API CRUD (niente SQL fuori da qui)
├── mcda/
│   └── calcolo.py              # SUMPRODUCT classifica framework
├── llm/
│   ├── _client.py              # client Anthropic condiviso
│   ├── intervista.py           # Q LLM + parse risposta libera
│   ├── diagnostica.py          # multi-turno con re-domanda su risposte vaghe
│   └── report.py               # report markdown personalizzato (Sonnet)
├── data/                       # SQLite runtime (gitignored)
└── main.py                     # stub CLI (entry point package)

knowledge/                      # KB privato (clonato a parte, gitignored)
├── pdfs/                       # 11 paper accademici
├── frameworks/                 # 11 .md strutturati
├── EXTRACTION_PROMPT.md        # system prompt per estrazione LLM
└── _TEMPLATE.md                # template framework

MatriceDB.xlsx                  # template seed criteri/framework/voti
Criteri_Readiness_Maturity.md   # definizioni 10 criteri MCDA
.streamlit/config.toml          # tema Streamlit
pyproject.toml                  # config progetto uv
```

---

## Stack tecnico

- **Linguaggio:** Python 3.11
- **Dependency management:** uv
- **UI:** Streamlit
- **DB:** SQLite (locale, single-file)
- **LLM:** Anthropic Claude (Haiku 4.5 per intervista/diagnostica,
  Sonnet 4.6 per report)
- **Data:** openpyxl (lettura Excel), python-dotenv, pypdf

---

## Troubleshooting

**`error: Failed to spawn: streamlit`**
```bash
uv sync
uv run python -m streamlit run cicerone/ui/app.py
```

**Welcome email di Streamlit blocca il primo avvio**
```bash
mkdir -p ~/.streamlit && printf '[general]\nemail = ""\n' > ~/.streamlit/credentials.toml
```

**`anthropic.AuthenticationError`** — chiave API non valida o non
configurata. Verifica:
- `.env` esiste con `ANTHROPIC_API_KEY=sk-ant-...` (no spazi, no virgolette)
- OPPURE chiave incollata nella sidebar
- Credito Anthropic > 0 (https://console.anthropic.com/settings/billing)

**`FileNotFoundError: MatriceDB.xlsx`** — il seed cerca il file nella root
del repo. Assicurati di lanciare i comandi `uv run ...` dal root, non da
sottocartelle.

**App lenta su intervista/diagnostica** — è normale, ogni domanda implica
una chiamata LLM (~2-4 sec con Haiku). Il report finale usa Sonnet ed è
più lento (~15-30 sec).

---

## Licenza

Codice rilasciato sotto licenza [MIT](LICENSE).

Il contenuto del knowledge base privato (`cicerone-knowledge`) è soggetto
a termini d'uso interno separati — non è coperto dalla licenza MIT di
questo repo.

---

## Contatti

Flavio Ciani — [ciani.flavio04@gmail.com](mailto:ciani.flavio04@gmail.com)
