# Architettura

Questo documento descrive il modello di dominio, i confini dei moduli, il flusso
dati e le scelte di configurazione e design di Cicerone. Per setup e uso vedi
[`README.md`](README.md).

## Modello di dominio

Lo schema SQLite (`cicerone/db/schema.sql`) è costruito attorno a sette tabelle:

- **Sheet** — categoria che raggruppa criteri e framework (`rediness` /
  `implementation`). Il flusso utente lavora sullo sheet `rediness`.
- **Criterio** — dimensione di valutazione (nome, definizione, sheet).
- **Framework** — uno degli 11 modelli accademici (nome, sheet).
- **Voto** — quanto un framework copre un criterio. Chiave composta
  `(framework_id, criterio_id)`; valore in `{0, 2.5, 5, 7.5, 10}`. Dato fisso
  dal seed.
- **Assessment** — una sessione di valutazione: sheet, framework vincitore,
  contesto azienda (JSON), timestamp.
- **peso_assessment** — per ogni assessment e criterio: livello (5 valori, da
  "Non importante" a "Fondamentale"), peso in `{0, 2.5, 5, 7.5, 10}`,
  motivazione, trascrizione e flag `ambiguo`. È l'output dell'intervista.
- **Diagnostica** — coppie domanda/risposta raccolte nella fase diagnostica,
  legate all'assessment (con eventuale criterio e valutazione LLM).

Il punteggio MCDA di un framework è la somma, su tutti i criteri, di
`voto × peso` (SUMPRODUCT). I pesi mancanti contano come 0.

## Confini dei moduli

- **`cicerone/db/`** — accesso ai dati.
  - `connection.py`: helper `get_connection()` (apre SQLite, abilita le foreign
    key, `row_factory` a `sqlite3.Row`).
  - `schema.sql`: DDL delle sette tabelle.
  - `seed.py`: popolamento idempotente di criteri, framework e voti.
  - `repository.py`: API CRUD. Tutto l'SQL applicativo vive qui (eccetto le
    query di calcolo in `mcda/`).
- **`cicerone/llm/`** — interazione con i modelli Claude.
  - `_client.py`: client Anthropic condiviso. `set_api_key()` permette
    l'override della chiave da runtime (UI); `get_client()` usa l'override se
    presente, altrimenti legge `ANTHROPIC_API_KEY` dall'ambiente.
  - `intervista.py`: genera una domanda per criterio tarata sul contesto e
    parsa la risposta libera in `(livello, peso, motivazione, ambiguo)`,
    chiedendo un chiarimento quando la risposta è inutilizzabile.
  - `diagnostica.py`: diagnostica multi-turno post-MCDA. Carica la knowledge
    del framework vincitore, pone da 3 a 5 domande (una alla volta) e rifà la
    domanda in modo più mirato sulle risposte vaghe.
  - `report.py`: aggrega contesto, pesi, classifica, Q&A diagnostica e
    knowledge del vincitore in un report markdown finale.
- **`cicerone/mcda/`** — calcolo.
  - `calcolo.py`: `classifica_framework()`, `breakdown_per_criterio()` e
    `vincitore()`. Implementano lo SUMPRODUCT come query SQL.
- **`cicerone/ui/`** — interfaccia Streamlit.
  - `app.py`: entry point e orchestrazione del flusso a step.
  - `pages/`: i singoli step (onboarding, intervista, vincitore, diagnostica) e
    helper condivisi.
  - `style.css`: identità visiva (vedi Design system).
- **`cicerone/desktop/`** — launcher desktop (entry point `cicerone.desktop:main`,
  esportato dal package `__init__.py`).
  - `launcher.py`: avvio del bundle (porta locale, override path, Streamlit
    in-process in thread daemon, finestra pywebview). Espone `main()`.
  - `paths.py`: risoluzione dei path in dev e dentro il bundle PyInstaller;
    forza il database su una location scrivibile.
  - `setup_knowledge.py`: funzioni pure per il setup first-run della knowledge
    base (clone del repo privato via PAT, oppure import da cartella locale).
  - `_html.py`: markup della finestra di setup pywebview.

## Flusso dati (5 step)

1. **Onboarding** — l'utente fornisce il profilo azienda (nome, settore,
   dimensione, nazione, ecc.) e la `ANTHROPIC_API_KEY`. Viene creato un
   `Assessment` con il contesto.
2. **Intervista** — per ciascun criterio l'LLM (`llm/intervista.py`) genera una
   domanda contestualizzata; la risposta libera viene parsata in livello/peso e
   salvata in `peso_assessment`. Su risposte non comprensibili l'LLM chiede un
   chiarimento prima di accettare.
3. **Calcolo MCDA** — `mcda/calcolo.py` classifica gli 11 framework per
   `Σ(voto × peso)` e determina il vincitore, salvato sull'assessment.
4. **Diagnostica** — `llm/diagnostica.py` carica la knowledge del framework
   vincitore e conduce 3-5 domande mirate sui gap; ogni Q&A è salvata in
   `Diagnostica`.
5. **Report** — `llm/report.py` aggrega tutto e produce il report markdown
   finale (profilo, motivazione del framework, gap, roadmap prioritizzata,
   KPI), scaricabile dall'utente.

## Configurazione via variabili d'ambiente

- **`CICERONE_DB_PATH`** — override del path del database SQLite. Se assente,
  `cicerone/db/connection.py` usa `cicerone/data/cicerone.sqlite` nel repo.
  Nel bundle desktop il launcher la imposta a una directory utente scrivibile
  (`~/Library/Application Support/Cicerone/`).
- **`CICERONE_KNOWLEDGE_DIR`** — override della cartella della knowledge base.
  Se assente, `cicerone/llm/diagnostica.py` usa `knowledge/frameworks/` nel
  repo. Nel bundle il launcher la imposta alla cartella risolta al setup.

## Knowledge base fuori dal bundle

La knowledge base (i `.md` strutturati dei framework, derivati da paper
accademici) non è distribuita pubblicamente né inclusa nel bundle desktop, per
ragioni di copyright dei materiali sorgente. Vive in un repository privato
separato.

- **In sviluppo:** si clona dentro `knowledge/` del repo (gitignored); i `.md`
  vanno in `knowledge/frameworks/`.
- **Nel desktop:** al primo avvio l'app mostra una finestra di setup che
  installa la knowledge nella user data dir, clonando il repo privato tramite un
  Personal Access Token GitHub (mai salvato su disco) oppure importandola da una
  cartella locale. Il bundle PyInstaller non include la knowledge. Vedi
  [`packaging/README.md`](packaging/README.md) per i dettagli.

## Design system

L'identità visiva (`cicerone/ui/style.css`) è minimalista, con un solo colore di
accento.

- **Accento ambrato:** `#E8B84B` (variante scura per hover: `#C99B30`).
- **Testo muted:** `#7A7A7A` (tagline, caption, divisori).
- **Font header:** serif Cormorant Garamond per wordmark, titoli e accenti
  editoriali; il resto resta sul font di sistema.
- **Principio:** un solo accento, divisori sottili, niente ombre forti né
  decorazioni superflue.
