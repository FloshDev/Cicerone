# Changelog

Tutte le modifiche rilevanti a questo progetto sono documentate qui.

Il formato segue [Keep a Changelog](https://keepachangelog.com/it/1.1.0/) e il
progetto aderisce al [Versionamento Semantico](https://semver.org/lang/it/).

## [Unreleased]

## [0.2.0] - 2026-06-19

### Changed

- **Layer LLM provider-agnostico (litellm)**: le chiamate ai modelli passano
  ora per `litellm.completion()` tramite l'unico helper `complete()` in
  `cicerone/llm/_client.py`. L'utente può usare la chiave del modello che
  preferisce (Anthropic, OpenAI, Gemini, ...) indicando la stringa modello in
  formato litellm. Un solo modello configurabile per tutti gli step (default
  `anthropic/claude-sonnet-4-6`, override via campo UI o env `CICERONE_MODEL`).
  Verifica chiave e UI di onboarding rese generiche (campo "Modello" + "API
  Key", niente più riferimenti hardcoded ad Anthropic). Rimossi gli structured
  outputs Anthropic-specifici nell'intervista; il parsing JSON difensivo
  esistente resta a garanzia anti-crash.
- **Redesign UI Streamlit in direzione SaaS**: restyle completo di `style.css`
  e dei singoli step (`onboarding`, `intervista`, `vincitore`, `report`),
  rimozione della chrome di default di Streamlit, logo e favicon brandizzati.
- **Intervista guidata dal modello**: è l'LLM a decidere se un criterio è
  coperto o se serve un altro turno (chiarimento/approfondimento), invece di un
  numero di turni fisso.
- **Rebrand terminologia globale Readiness → Rediness**: allineamento su
  schema DB, seed, MCDA, risorse e test.
- **Rename `cicerone/ui/pages/` → `cicerone/ui/_pages/`**: il prefisso `_`
  evita che Streamlit tratti i moduli come pagine multipage automatiche.
- Asset di branding: logo sorgente ed elaborato in `resources/branding/`.

### Fixed

- **Crash al parsing JSON dell'intervista**: risposte del modello non
  serializzabili facevano crashare lo step; parsing reso robusto.
- **Troncamento risposte sui modelli con thinking** (es. Gemini 2.5 Flash): i
  token di ragionamento consumavano `max_tokens` troncando le domande. Ora
  `complete()` passa `reasoning_effort="disable"` ai soli modelli Gemini e i cap
  `max_tokens` sono più ampi.
- **BadRequest su Anthropic**: `reasoning_effort` e system vuoto facevano fallire
  Claude. Il parametro thinking è ora limitato a Gemini e il messaggio system
  vuoto non viene più inviato.
- **Crash su errori del provider** (rate limit, chiave errata, modello
  inesistente): `complete()` mappa le eccezioni litellm in `LLMError` con
  messaggio in italiano e le pagine le mostrano con `llm_guard()` come errore
  pulito, senza traceback.
- **UI onboarding**: chip "Chiave valida/non valida" accanto al bottone e
  centrato; bottone che non va a capo né strozza il testo; campo API key
  mascherato con occhio per rivelarla.

### Changed (UI)

- Sidebar: rimosso il contatore "Criterio X/N" durante l'intervista (le fasi in
  alto bastano).

### Packaging

- Rimossa la dipendenza `anthropic` (sostituita da `litellm`).
- `packaging/cicerone.spec`: bundle di `litellm` e dipendenze (tiktoken, openai,
  tokenizers) via `collect_all` + metadata, per il `.app`/`.dmg`.

### Docs

- Brief di migrazione UI Streamlit → Flet in cartella isolata `flet_ui/`
  (`flet_ui/BRIEF-FLET-UI.md`).
- `ARCHITECTURE.md` e `ROADMAP.md` aggiornati su `_pages/`, intervista a turni,
  redesign SaaS e migrazione Flet pianificata.
- `docs/superpowers/` aggiunta a `.gitignore` (documentazione interna, fuori
  dal repo pubblico).

## [0.1.3] - 2026-06-15

### Fixed

- **DMG "danneggiato" su macOS**: la v0.1.2 mostrava errore "danneggiato,
  spostare nel Cestino" senza nemmeno il prompt Gatekeeper. Cause:
  (1) PyInstaller firma il binario prima del COLLECT, lasciando il seal
  ad-hoc inconsistente; (2) iCloud Drive sul Desktop ri-applicava xattr
  (`com.apple.fileprovider.fpfs#P`, `FinderInfo`) che invalidavano la firma.
  Fix in `packaging/build.sh`: stage del bundle in `/tmp` (fuori da iCloud),
  re-firma ad-hoc deep dopo COLLECT, DMG generato in `/tmp` e poi spostato.

## [0.1.2] - 2026-06-15

### Fixed

- **Bundle PyInstaller incompleto**: `collect_submodules("cicerone")`
  non rilevava i moduli `cicerone.db`, `cicerone.ui`, `cicerone.llm`,
  `cicerone.mcda` in ambienti dove il pacchetto non era installato come
  editable. Sintomo: `ImportError: cannot import name 'seed' from
  'cicerone.db'` all'apertura dell'app.
  Fix: enumerazione esplicita dei moduli dal filesystem in
  `packaging/cicerone.spec` come fallback (belt-and-suspenders).

## [0.1.1] - 2026-06-15

### Added

- **Notifica aggiornamenti in-app**: la sidebar mostra un banner ambrato
  discreto con link diretto alla release quando una versione più recente è
  pubblicata su GitHub. Check via GitHub Releases API, cache 1h, fallback
  silenzioso offline o senza release pubblicate (modulo
  `cicerone.version_check`).
- `.dmg` con layout Finder curato: finestra 640×420, icona `Cicerone.app`
  a sinistra e shortcut `Applications` a destra per drag&drop classico,
  icona volume ambrata (`create-dmg` con `--volicon`).

### Changed

- Refactoring Round 6 (release tecnica): split dei moduli UI in
  `cicerone/ui/pages/` e del launcher desktop in `cicerone/desktop/`.
- Consolidamento della documentazione: README riscritto, nuovi
  `ARCHITECTURE.md`, `CHANGELOG.md` e `ROADMAP.md` in root.

### Removed

- Cleanup di file e dipendenze non più usati (`pypdf`, `python-docx`,
  `cicerone/main.py` stub, `cicerone/ui/_mock.py`).

### Fixed

- `packaging/cicerone.spec` referenziava `_mock.py` cancellato: rimozione
  riferimento, build PyInstaller ora arriva fino a `.dmg` senza errori.
- Lint cosmetici nei moduli LLM (`ruff` zero errori).

### Tests

- Configurazione `ruff` (E/F/I/B/UP/SIM, line-length 100).
- Smoke test `pytest`: 27 test su repository, MCDA e parsing intervista.

### Docs

- Diario storico dei round 1-6 archiviato in `docs/archive/`.

## [0.1.0] - 2026-06-15

Prima release desktop.

### Added

- Web app Streamlit completa end-to-end: onboarding, intervista guidata da LLM,
  calcolo MCDA, diagnostica multi-turno e report markdown finale.
- Bundle desktop macOS `.app` / `.dmg` (PyInstaller + pywebview) con setup della
  knowledge base al primo avvio.
