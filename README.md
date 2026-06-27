# Cicerone

> La voce che orienta la tua PMI nell'adozione dell'AI.

> ⚠️ **Demo / prototipo in sviluppo attivo.** L'app attuale (`v0.2.0`) è una
> **demo funzionante** costruita rapidamente in *vibe coding*: serve a
> dimostrare il flusso end-to-end, non è codice di produzione consolidato. È
> in corso una **riscrittura da zero dell'interfaccia in [Flet](https://flet.dev/)**
> (cartella isolata `flet_ui/`, vedi [`flet_ui/BRIEF-FLET-UI.md`](flet_ui/BRIEF-FLET-UI.md)),
> che sostituirà l'attuale UI Streamlit lasciando il backend (DB, MCDA, LLM)
> intatto. Aspettarsi quindi UI e dettagli soggetti a cambiamenti.
>
> **Copertura attuale:** la demo copre l'intero flusso di **AI Readiness**
> (intervista, MCDA, diagnostica, report) sullo sheet `readiness`. La parte
> dedicata all'**AI Implementation** — secondo sheet di framework, percorso
> parallelo per aziende già pronte che vogliono passare all'adozione effettiva
> — verrà rilasciata in una **seconda fase**. Interfaccia e logica MCDA sono
> già predisposte; mancano i contenuti della knowledge base e i prompt LLM
> specifici.

Cicerone è un agente AI conversazionale che aiuta le PMI europee a valutare
la propria AI Readiness/Maturity scegliendo, fra 11 framework accademici, quello
più adatto al loro contesto. Il flusso guida l'utente attraverso un'intervista
condotta da un LLM, un calcolo MCDA che determina il framework vincitore, una
diagnostica multi-turno sui gap e infine un report markdown personalizzato con
roadmap prioritizzata e KPI da monitorare.

È disponibile sia come web app (Streamlit, eseguita in locale) sia come
applicazione desktop macOS (`.app` / `.dmg`). Le chiamate ai modelli passano
per [litellm](https://docs.litellm.ai/), quindi puoi usare la chiave del
**modello che preferisci** (Anthropic, OpenAI, Gemini, ecc.) indicando la
stringa modello nel formato litellm. Il progetto è stato sviluppato e testato
con modelli Anthropic Claude (storicamente Haiku per intervista/diagnostica e
Sonnet per il report), che restano i default suggeriti.

## Stack

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) — gestione progetto e dipendenze
- Streamlit — interfaccia web
- SQLite — persistenza locale single-file
- [litellm](https://docs.litellm.ai/) — layer LLM multi-provider (chiamate al modello scelto)

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

### Configurazione del modello e della API key

Cicerone è **provider-agnostico**: le chiamate passano per
[litellm](https://docs.litellm.ai/), quindi puoi usare il modello che preferisci
(Anthropic, OpenAI, Google Gemini, ecc.). Lo **stesso modello** viene usato per
intervista, diagnostica e report.

**La stringa modello** è nel formato litellm `provider/nome-modello`:

| Provider           | Esempio di stringa modello       | API key (provider)   |
|--------------------|----------------------------------|----------------------|
| Anthropic (Claude) | `anthropic/claude-sonnet-4-6`    | Anthropic Console    |
| OpenAI             | `openai/gpt-4o`                  | OpenAI Platform      |
| Google Gemini      | `gemini/gemini-2.5-flash`        | Google AI Studio     |

Il prefisso (`anthropic/`, `openai/`, `gemini/`, …) indica il provider; dopo lo
slash va il nome del modello come lo trovi nella console del provider. Elenco
completo per provider: <https://docs.litellm.ai/docs/providers>. Se non imposti
nulla, il default è **`anthropic/claude-sonnet-4-6`**.

> ℹ️ La chiave deve corrispondere al provider della stringa modello: una chiave
> Google funziona solo con un modello `gemini/...`, una chiave Anthropic solo con
> `anthropic/...`, ecc.

Due modi per configurare (i valori della UI hanno precedenza):

- **UI (onboarding):** scrivi la stringa modello nel campo **Modello** e incolla
  la chiave nel campo **API Key**. Valgono per la sessione corrente, non vengono
  mai salvate su disco.
- **`.env` (sviluppo):** copia `.env.example` in `.env`. Imposta la chiave del
  provider (litellm legge le env var standard: `ANTHROPIC_API_KEY`,
  `OPENAI_API_KEY`, `GEMINI_API_KEY`, …) e, opzionalmente, il modello con
  `CICERONE_MODEL`. `.env` è gitignored.

> ⚠️ Attenzione ai limiti del provider: i piani gratuiti (es. Gemini free tier,
> ~20 richieste/giorno) si esauriscono in fretta durante un assessment completo;
> l'app mostra un messaggio chiaro in caso di rate limit.

## Quickstart (desktop)

Per costruire il bundle macOS (`.app` / `.dmg`) e per il setup della knowledge
base al primo avvio, vedi [`packaging/README.md`](packaging/README.md).

## Struttura del repository

```
cicerone/                  # package Python
├── db/                    # connessione, schema SQL, seed, repository
├── llm/                   # intervista, diagnostica, report, client LLM (litellm)
├── mcda/                  # calcolo MCDA (classifica framework)
├── ui/                    # interfaccia Streamlit attuale (app + _pages + style.css)
├── desktop/               # launcher desktop (launcher, paths, setup knowledge)
└── data/                  # database SQLite a runtime (gitignored)

flet_ui/                   # riscrittura UI in Flet (lavoro isolato, work in progress)
packaging/                 # build .app/.dmg (PyInstaller + pywebview)
resources/                 # asset statici consumati dal seed
├── Criteri_Readiness_Maturity.md  # definizioni dei criteri
└── MatriceDB.xlsx                 # matrice criteri/framework/voti
knowledge/                 # knowledge base privata (clonata a parte, gitignored)
pyproject.toml             # configurazione progetto, dipendenze, ruff
.env.example               # template per API key del provider + CICERONE_MODEL
```

Per i dettagli su moduli, flusso dati e design system vedi
[`ARCHITECTURE.md`](ARCHITECTURE.md).

## Glossario di dominio

- **Criterio** — dimensione di valutazione dell'AI Readiness (es. competenze,
  dati, governance). I criteri sono fissi e definiti nel seed.
- **Peso** — quanto un criterio è importante per la specifica azienda, inferito
  dall'LLM a partire dalla risposta libera dell'utente in intervista. Espresso
  su una scala discreta (0, 2.5, 5, 7.5, 10) mappata su 5 livelli, da
  "Non importante" a "Fondamentale".
- **Voto** — quanto un framework copre un dato criterio. Valore fisso nel seed,
  sulla stessa scala discreta del peso.
- **Assessment** — una singola sessione di valutazione: contesto azienda, pesi
  raccolti, framework vincitore, diagnostica.
- **Framework** — uno degli 11 modelli accademici di AI Readiness/Maturity tra
  cui Cicerone sceglie il più adatto.
- **Sheet** — categoria che raggruppa criteri e framework (`readiness` /
  `implementation`); il flusso utente lavora sullo sheet `readiness`.
- **Diagnostica** — fase conversazionale multi-turno, successiva al calcolo
  MCDA, in cui l'LLM approfondisce i gap dell'azienda rispetto al framework
  vincitore prima di generare il report.

## Origine del progetto

Cicerone nasce da una **collaborazione spontanea fra studenti** della
[SUPSI](https://www.supsi.ch/) (Scuola Universitaria Professionale della
Svizzera Italiana) e dell'[Università degli Studi dell'Insubria](https://www.uninsubria.it/)
(sede di Varese). Il gruppo si è ritrovato in modo autonomo, fuori dai canali
istituzionali, con l'obiettivo di portare strumenti accademici di AI
Readiness/Maturity — oggi rinchiusi in paper accademici poco accessibili — a
portata di mano delle PMI europee.

Il progetto è guidato da questa collaborazione transfrontaliera e mantiene
un'identità da prototipo accademico in evoluzione: nessuna pretesa di prodotto
commerciale, ma una direzione precisa e una struttura ingegneristica solida.

## Licenza

Codice rilasciato sotto licenza [MIT](LICENSE). Il contenuto della knowledge
base privata è soggetto a termini d'uso separati e non è coperto da questa
licenza.
