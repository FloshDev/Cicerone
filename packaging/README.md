# Packaging — Cicerone macOS .app + .dmg

Bundle desktop di Cicerone per macOS. L'utente finale apre il `.dmg`,
trascina `Cicerone.app` in `Applications`, doppio click. Nessun terminale,
nessun `pip install`, nessun `streamlit run`.

## Architettura

```
Cicerone.app
 └─ launcher (cicerone/desktop.py):
     1. porta libera localhost
     2. CICERONE_DB_PATH → ~/Library/Application Support/Cicerone/
     3. risolve knowledge: env var | user data dir | dev fallback | SETUP
        - SETUP first-run: finestra HTML pywebview (clone repo privato
          via PAT GitHub OPPURE folder picker locale) prima di Streamlit
     4. CICERONE_KNOWLEDGE_DIR → cartella risolta
     5. streamlit.web.bootstrap.run in thread daemon (NON subprocess:
        in bundle sys.executable rieseguirebbe il launcher → fork bomb)
     6. polling /_stcore/health finché 200
     7. webview.create_window con splash → window.load_url(URL)
     8. webview.start() blocca finché finestra non si chiude
     9. processo termina, thread streamlit daemon muore con esso
```

## Requisiti macchina di build

- macOS (Apple Silicon o Intel — il bundle è single-arch)
- Python 3.11+ via uv
- `uv sync --group packaging` per installare `pyinstaller` e `pywebview`
- Knowledge base NON serve al build. Lo spec NON la bundla. La knowledge
  viene installata al primo avvio sulla macchina utente (setup window).
- (opzionale) `brew install create-dmg` per layout `.dmg` più curato;
  altrimenti fallback automatico su `hdiutil` (single icon + alias Applications).

## Build

```bash
bash packaging/build.sh
```

Output:
- `dist/Cicerone.app` (~230 MB)
- `dist/Cicerone.dmg` (~100 MB compresso)

Tempo: ~50-60 sec su Apple Silicon.

## Dove finiscono i dati utente

```
~/Library/Application Support/Cicerone/
  ├── cicerone.sqlite                ← DB assessment
  ├── knowledge/frameworks/*.md      ← knowledge base installata al setup
  └── knowledge_repo/                ← clone .git completo (solo se opzione A)
```

Per cancellare lo stato: rimuovi l'intera cartella. Al riavvio l'app
ripropone il setup knowledge.

## Setup knowledge al primo avvio

Al primo lancio (o se la cartella `knowledge/frameworks/` è vuota), l'app
mostra una finestra di configurazione con due opzioni:

**A) Clone repo privato GitHub** (preferito):
1. Genera un Personal Access Token su GitHub con scope `repo:read` SOLO
   sul repo `cicerone-knowledge`. Settings → Developer settings → Personal
   access tokens → Fine-grained tokens.
2. Incolla il token nel campo, lascia l'URL repository di default.
3. Click "Scarica knowledge". Il clone va in
   `~/Library/Application Support/Cicerone/knowledge_repo/`, i `.md`
   vengono copiati in `knowledge/frameworks/`.

Il token NON viene salvato sul disco. Serve solo a quel clone una tantum.
Per refresh futuri: cancella `knowledge_repo/` e rilancia l'app
(re-incolla token).

**B) Cartella locale**:
- Usa il file picker o incolla un path.
- L'app cerca automaticamente la sottocartella con i `.md` (accetta sia
  `<path>/frameworks/*.md` sia `<path>/*.md`).
- I file vengono COPIATI nella user data dir (no symlink: l'app resta
  indipendente dalla sorgente).

## Warning Gatekeeper al primo avvio

Il `.dmg` non è firmato né notarizzato. Alla prima apertura macOS mostra:

> «Cicerone» non può essere aperto perché Apple non può verificare che
> non contenga malware.

Workaround utente (solo prima volta):
1. Finder → click destro su `Cicerone.app` → **Apri** → conferma
2. **oppure** Impostazioni di Sistema → Privacy e Sicurezza → tasto
   "Apri comunque" accanto a Cicerone

Dopo la prima conferma macOS non chiederà più.

Soluzione definitiva (futura): Apple Developer ID + `codesign` +
`notarytool` — richiede account Apple Developer ($99/anno). Non in scope
per questa release.

## Aggiornare l'app

Build nuova → drag in Applications → "Sostituisci". I dati utente in
`Application Support` restano (file SQLite separato dal bundle).

## Aggiungere/togliere dipendenze runtime

Se aggiungi una dep `runtime` al `pyproject.toml`, aggiorna lo spec:

```python
hiddenimports += collect_submodules("nuova_lib")
datas += copy_metadata("nuova_lib")        # se usa importlib.metadata
datas += collect_data_files("nuova_lib")   # se trasporta asset
```

Senza, al primo avvio del bundle vedrai uno di questi:
- `ModuleNotFoundError`
- `importlib.metadata.PackageNotFoundError`
- `FileNotFoundError` su un asset

## Note tecniche

- **Streamlit in-process** (non subprocess): `streamlit.web.bootstrap.run`
  in thread daemon + monkey-patch di `signal.signal` a no-op (i signal
  handler di streamlit girano solo nel main thread; nel nostro caso lo
  shutdown lo gestisce pywebview alla chiusura della finestra).
- **DB path override**: `cicerone/db/connection.py` legge
  `CICERONE_DB_PATH` se presente; il launcher la imposta a una directory
  scrivibile. In dev senza env var il comportamento è invariato.
- **Single-arch**: il bundle è arm64 (se buildi su Apple Silicon) o x86_64
  (se buildi su Intel). Per universal2 servirebbe ricompilare tutto con
  `--target-arch=universal2` e Python universal2.
- **Watchdog assente**: `--server.fileWatcherType=none` perché in bundle
  l'auto-reload non serve.
