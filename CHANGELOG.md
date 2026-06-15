# Changelog

Tutte le modifiche rilevanti a questo progetto sono documentate qui.

Il formato segue [Keep a Changelog](https://keepachangelog.com/it/1.1.0/) e il
progetto aderisce al [Versionamento Semantico](https://semver.org/lang/it/).

## [Unreleased]

### Changed

- Refactoring Round 6: split dei moduli UI in `cicerone/ui/pages/` e del
  launcher desktop in `cicerone/desktop/`, per separare meglio le
  responsabilità.
- Consolidamento della documentazione: README riscritto, nuovi `ARCHITECTURE.md`,
  `CHANGELOG.md` e `ROADMAP.md` in root.

### Removed

- Cleanup di file e dipendenze non più usati.

### Added

- Configurazione lint con `ruff` e smoke test con `pytest`.

### Docs

- Diario storico dei round 1-6 archiviato in `docs/archive/`.

## [0.1.0] - 2026-06-15

Prima release desktop.

### Added

- Web app Streamlit completa end-to-end: onboarding, intervista guidata da LLM,
  calcolo MCDA, diagnostica multi-turno e report markdown finale.
- Bundle desktop macOS `.app` / `.dmg` (PyInstaller + pywebview) con setup della
  knowledge base al primo avvio.
