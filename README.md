# Cicerone

> La voce che orienta la tua PMI nell'adozione dell'AI.

> ⚠️ **Demo / prototipo in sviluppo attivo.** L'app attuale (`v0.1.3`) è una
> **demo funzionante** costruita rapidamente in stile *vibe coding*: serve a
> dimostrare il flusso end-to-end, non è codice di produzione consolidato. È
> in corso una **riscrittura da zero dell'interfaccia in [Flet](https://flet.dev/)**
> (cartella isolata `flet_ui/`, vedi [`flet_ui/BRIEF-FLET-UI.md`](flet_ui/BRIEF-FLET-UI.md)),
> che sostituirà l'attuale UI Streamlit lasciando il backend (DB, MCDA, LLM)
> intatto. Aspettarsi quindi UI e dettagli soggetti a cambiamenti.
>
> **Copertura attuale:** la demo copre l'intero flusso di **AI Rediness**
> (intervista, MCDA, diagnostica, report) sullo sheet `rediness`. La parte
> dedicata all'**AI Implementation** — secondo sheet di framework, percorso
> parallelo per aziende già pronte che vogliono passare all'adozione effettiva
> — verrà rilasciata in una **seconda fase**. Interfaccia e logica MCDA sono
> già predisposte; mancano i contenuti della knowledge base e i prompt LLM
> specifici.

Cicerone è un agente AI conversazionale che aiuta le PMI europee a valutare
la propria AI Rediness/Maturity scegliendo, fra 11 framework accademici, quello
più adatto al loro contesto. Il flusso guida l'utente attraverso un'intervista
condotta da un LLM, un calcolo MCDA che determina il framework vincitore, una
diagnostica multi-turno sui gap e infine un report markdown personalizzato con
roadmap prioritizzata e KPI da monitorare.

È disponibile sia come web app (Streamlit, eseguita in locale) sia come
applicazione desktop macOS (`.app` / `.dmg`). I modelli usati sono Anthropic
Claude (Haiku per intervista e diagnostica, Sonnet per il report).

## Stack

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) — gestione progetto e dipendenze
- Streamlit — interfaccia web
- SQLite — persistenza locale single-file
- Anthropic SDK — chiamate ai modelli Claude

Lettura del seed da Excel via `openpyxl`; variabili d'ambiente via
`python-dotenv`. Tooling di sviluppo: `ruff` (lint) e `pytest` (test).

## Quickstart (sviluppo)

```bash
# 1. Installa le dipendenze (uv crea automaticamente .venv)
uv sync

# 2. Clona la knowledge base privata dentro knowledge/ (richiede accesso)
#    I file .md dei framework devono finire in knowledge/frameworks/.
git clone <repo-knowledge-privato> knowledge
#    knowledge/ è gitignored: è un repository separato dal pubblico.
#    Senza knowledge base l'app si avvia comunque (intervista + MCDA +
#    classifica), ma diagnostica e report risultano generici.

# 3. Avvia l'app
uv run streamlit run cicerone/ui/app.py
```

L'app apre il browser su `http://localhost:8501`. Al primo avvio lo schema
SQLite viene applicato e il database viene popolato (seed dei criteri, degli
11 framework e dei voti MCDA). Il database locale persiste in
`cicerone/data/cicerone.sqlite` (gitignored).

### ANTHROPIC_API_KEY

Serve una chiave Anthropic per le chiamate ai modelli. Due modi equivalenti:

- **UI (onboarding):** incolla `sk-ant-...` nel campo dedicato. Vale per la
  sessione corrente e non viene mai persistita su disco.
- **`.env` (sviluppo):** copia `.env.example` in `.env` e inserisci la chiave.
  Viene letta automaticamente all'avvio. `.env` è gitignored.

Se entrambe sono presenti, la chiave inserita dalla UI ha precedenza.

## Quickstart (desktop)

Per costruire il bundle macOS (`.app` / `.dmg`) e per il setup della knowledge
base al primo avvio, vedi [`packaging/README.md`](packaging/README.md).

## Struttura del repository

```
cicerone/                  # package Python
├── db/                    # connessione, schema SQL, seed, repository
├── llm/                   # intervista, diagnostica, report, client Anthropic
├── mcda/                  # calcolo MCDA (classifica framework)
├── ui/                    # interfaccia Streamlit attuale (app + _pages + style.css)
├── desktop/               # launcher desktop (launcher, paths, setup knowledge)
└── data/                  # database SQLite a runtime (gitignored)

flet_ui/                   # riscrittura UI in Flet (lavoro isolato, work in progress)
packaging/                 # build .app/.dmg (PyInstaller + pywebview)
resources/                 # asset statici consumati dal seed
├── Criteri_Rediness_Maturity.md  # definizioni dei criteri
└── MatriceDB.xlsx                 # matrice criteri/framework/voti
knowledge/                 # knowledge base privata (clonata a parte, gitignored)
pyproject.toml             # configurazione progetto, dipendenze, ruff
.env.example               # template per ANTHROPIC_API_KEY
```

Per i dettagli su moduli, flusso dati e design system vedi
[`ARCHITECTURE.md`](ARCHITECTURE.md).

## Glossario di dominio

- **Criterio** — dimensione di valutazione dell'AI Rediness (es. competenze,
  dati, governance). I criteri sono fissi e definiti nel seed.
- **Peso** — quanto un criterio è importante per la specifica azienda, inferito
  dall'LLM a partire dalla risposta libera dell'utente in intervista. Espresso
  su una scala discreta (0, 2.5, 5, 7.5, 10) mappata su 5 livelli, da
  "Non importante" a "Fondamentale".
- **Voto** — quanto un framework copre un dato criterio. Valore fisso nel seed,
  sulla stessa scala discreta del peso.
- **Assessment** — una singola sessione di valutazione: contesto azienda, pesi
  raccolti, framework vincitore, diagnostica.
- **Framework** — uno degli 11 modelli accademici di AI Rediness/Maturity tra
  cui Cicerone sceglie il più adatto.
- **Sheet** — categoria che raggruppa criteri e framework (`rediness` /
  `implementation`); il flusso utente lavora sullo sheet `rediness`.
- **Diagnostica** — fase conversazionale multi-turno, successiva al calcolo
  MCDA, in cui l'LLM approfondisce i gap dell'azienda rispetto al framework
  vincitore prima di generare il report.

## Origine del progetto

Cicerone nasce da una **collaborazione spontanea fra studenti** della
[SUPSI](https://www.supsi.ch/) (Scuola Universitaria Professionale della
Svizzera Italiana) e dell'[Università degli Studi dell'Insubria](https://www.uninsubria.it/)
(sede di Varese). Il gruppo si è ritrovato in modo autonomo, fuori dai canali
istituzionali, con l'obiettivo di portare strumenti accademici di AI
Rediness/Maturity — oggi rinchiusi in paper accademici poco accessibili — a
portata di mano delle PMI europee.

Il progetto è guidato da questa collaborazione transfrontaliera e mantiene
un'identità da prototipo accademico in evoluzione: nessuna pretesa di prodotto
commerciale, ma una direzione precisa e una struttura ingegneristica solida.

## Licenza

Codice rilasciato sotto licenza [MIT](LICENSE). Il contenuto della knowledge
base privata è soggetto a termini d'uso separati e non è coperto da questa
licenza.
