# Roadmap

Lavori futuri non inclusi nel round corrente. Sono idee di direzione, non
impegni con scadenza.

## In corso

- **Riscrittura UI in Flet** — sostituzione dell'interfaccia Streamlit con una
  UI nativa [Flet](https://flet.dev/), sviluppata in isolamento in `flet_ui/`
  (vedi `flet_ui/BRIEF-FLET-UI.md`). Backend (DB, MCDA, LLM) invariato.

## Funzionalità — seconda fase

- **AI Implementation** — secondo sheet di framework (`implementation`):
  percorso parallelo all'AI Readiness per aziende già pronte che passano
  all'adozione effettiva. Interfaccia e logica MCDA già predisposte; mancano i
  contenuti della knowledge base e i prompt LLM specifici.

## Distribuzione

- **Code signing e notarization Apple** — firmare e notarizzare il bundle macOS
  (Apple Developer ID + `codesign` + `notarytool`) per eliminare l'avviso di
  Gatekeeper al primo avvio.
- **Bundle cross-platform** — packaging per Windows e Linux, oltre all'attuale
  bundle macOS.

## Automazione

- **CI/CD con GitHub Actions** — pipeline per lint, test e build automatici.

## Funzionalità

- **Refresh della knowledge in-app** — aggiornare la knowledge base dall'app
  senza re-incollare il token, conservando il PAT nel keyring di sistema.
- **Internazionalizzazione della UI** — supporto multilingua oltre all'italiano.

## Tecnico

- **Refactoring dello schema DB** — rivedere la struttura delle tabelle per
  semplificare query e manutenzione.
