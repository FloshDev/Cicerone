# Brief — Nuova UI Flet per Cicerone (lavoro isolato)

Documento di consegna per chi costruisce la nuova interfaccia Flet di Cicerone.
**Da leggere per intero prima di scrivere una riga di codice**, anche dal tuo Claude.

L'app oggi ha una UI in Streamlit. L'obiettivo è ricostruire la stessa UI in
**Flet**, lasciando il backend (DB, MCDA, LLM) **completamente intatto**. Il
backend è già disaccoppiato: si consuma come libreria.

---

## 0. REGOLE DI INGAGGIO (vincolanti — non negoziabili)

Queste regole valgono per te e per il tuo assistente Claude.

1. **Scrivi SOLO dentro la cartella nuova `flet_ui/`** (la crei tu, vedi §2).
   Tutto il codice nuovo, gli asset, il logo, eventuali note → solo lì dentro.

2. **Tutto il resto del repository è SOLA LETTURA.** Puoi *leggere* qualunque
   file di `cicerone/`, `packaging/`, `resources/`, ecc. per capire il
   contratto. **Non modificare, non rinominare, non cancellare NULLA** fuori da
   `flet_ui/`. In particolare NON toccare:
   - `cicerone/` (qualsiasi sottocartella: `db/`, `llm/`, `mcda/`, `ui/`, `desktop/`)
   - `pyproject.toml`, `uv.lock`
   - `packaging/`
   - `.venv/`, `data/`, lo schema o il seed del DB

3. **Niente nuove dipendenze nel progetto.** Non lanciare `uv add`, non editare
   `pyproject.toml`. Flet si usa in modo effimero (vedi §6 "Come avviare").

4. **Niente git distruttivo.** Niente commit, push, reset, checkout, branch
   switch a meno che il proprietario del repo non lo chieda esplicitamente.

5. **Il backend è un contratto fisso.** Le funzioni elencate in §4 si chiamano
   così come sono. Se qualcosa sembra mancare, **fermati e chiedi** — non
   modificare il backend per aggirare il problema.

6. **Design system.** Nel `CLAUDE.md` globale c'è un design system TUI: vale per
   le interfacce `prompt_toolkit`/`rich`, **NON per questa GUI Flet**. Da quel
   documento riusa **solo la palette** (vedi §5). Ignora le regole su
   box-drawing, footer, sfondo trasparente: qui costruisci una GUI desktop
   normale.

---

## 1. Cosa fa l'app (flusso utente)

Assessment "AI Rediness" per PMI, in 5 fasi sequenziali:

```
I  onboarding   → profilo azienda + verifica API key Anthropic
II intervista   → una domanda LLM per criterio, con eventuali chiarimenti
III vincitore   → classifica framework (calcolo MCDA) + dettaglio
IV diagnostica  → domande guidate LLM a catena
V  report       → report markdown generato dall'LLM, scaricabile .md
```

Stato corrente = quale fase + dati raccolti. Oggi vive in `st.session_state`;
nella versione Flet vive in un oggetto `AppState` (vedi §5).

---

## 2. Struttura della cartella

La cartella `flet_ui/` **esiste già** alla radice del repo (sorella di
`cicerone/` e `packaging/`), con dentro questo brief e il logo attuale in
`flet_ui/assets/logo.png`. Lavori solo qui dentro. Struttura attesa:

```
flet_ui/
  main.py              # ft.app(target=main): page config, theme, routing
  app_state.py         # @dataclass AppState (sostituto di st.session_state)
  theme.py             # palette brand + tema Flet
  db_boot.py           # bootstrap schema sicuro (vedi §4, nota importante)
  assets/
    logo.png           # <-- GIÀ PRESENTE (logo attuale di Cicerone)
  views/
    onboarding.py
    intervista.py
    vincitore.py
    diagnostica.py
    report.py
    knowledge_setup.py # opzionale (first-run), vedi §7
  components/
    spinner.py         # overlay ProgressRing durante le call LLM
    stepper.py         # navigazione fasi I–V (rimpiazza la sidebar)
  README.md            # come avviare + eventuali note tue
```

Il logo va in `flet_ui/assets/logo.png`. Nessun asset fuori da qui.

---

## 3. Architettura Flet (linee guida)

- **`ft.Page` unica.** Routing con `page.go(route)` + `page.on_route_change`
  che ricostruisce `page.views` in base alla fase corrente.
- **Stato**: una singola istanza di `AppState` tenuta nell'app, passata alle
  view. "Ricomincia" / "Nuovo assessment" = nuova istanza di `AppState`.
- **CALL LLM ASINCRONE — punto critico.** Ogni chiamata a `cicerone.llm.*`
  (`domanda_per_criterio`, `parse_risposta`, `next_question`, `genera_report`)
  è **bloccante** e può durare anche 20–30 secondi (il report). Eseguila in un
  thread (`page.run_thread`), mostra lo spinner overlay e **disabilita i
  controlli** durante l'attesa, poi `page.update()`. Se la chiami nel thread UI,
  **la finestra si congela**. Questo è l'unico vero scoglio: risolvi il pattern
  una volta in `components/spinner.py` e riusalo ovunque.
- **API key**: `TextField(password=True)` → passi il valore a
  `set_api_key(...)`. Il backend è già pronto a riceverla a runtime.

---

## 4. Contratto del backend (importa, NON modificare)

Il package `cicerone` è già installato in modalità editable: gli `import`
funzionano da `flet_ui/`. Sotto le firme che ti servono. **Trattale come API
fissa.**

### Bootstrap & avvio (nota IMPORTANTE)

C'è un vincolo d'ordine fragile nel DB: `cicerone.db.repository`, **al momento
dell'import**, esegue una migration `ALTER TABLE` che esplode su un DB nuovo
senza tabelle. Quindi lo schema va creato **prima** di importare `repository`.

Nella UI Streamlit questo è gestito da un bootstrap eager. Tu **non puoi
toccarlo né dipendere da `cicerone.ui`** (è Streamlit). Replica il bootstrap in
`flet_ui/db_boot.py` con questa sequenza, da eseguire **all'avvio, prima di
qualsiasi import di `repository`**:

1. apri la connessione con `cicerone.db.connection.get_connection()`;
2. se la tabella `Sheet` non esiste, esegui lo script
   `cicerone/db/schema.sql` (leggilo da disco, è SOLA LETTURA) via
   `conn.executescript(...)` e committa;
3. *solo dopo*, importa `repository` e chiama `seed.run_if_needed()`.

```python
# Avvio sicuro (concettuale):
from cicerone.db import seed
import flet_ui.db_boot            # crea schema se assente, PRIMA di repository
from cicerone.db import repository as repo   # ora è safe
seed.run_if_needed()
```

### `cicerone.db.connection`
- `get_connection() -> sqlite3.Connection`
- `DB_PATH` — da env `CICERONE_DB_PATH`, altrimenti `cicerone/data/cicerone.sqlite`

### `cicerone.db.seed`
- `run_if_needed() -> None` — popola criteri/framework/voti se DB vuoto. Idempotente.

### `cicerone.db.repository`
- `lista_criteri(sheet_nome) -> list[dict]`  — chiavi: `idCriterio`, `nomeCriterio`, `definizione`
- `lista_framework(sheet_nome) -> list[dict]`
- `crea_assessment(sheet_nome) -> int`  (ritorna `assessment_id`)
- `salva_peso(assessment_id, criterio_id, livello, peso, motivazione, trascrizione, ambiguo) -> None`
- `salva_contesto(assessment_id, contesto: dict) -> None`
- `get_contesto(assessment_id) -> dict | None`
- `get_assessment(assessment_id) -> dict | None`
- `set_framework_vincitore(assessment_id, framework_id) -> None`
- `get_framework(framework_id) -> dict | None`
- `salva_diagnostica(...) -> ...`
- `storia_diagnostica(assessment_id) -> list[dict]`  — chiavi per item: `domanda`, `risposta_utente`, `is_riask`
- `update_risposta_diagnostica(diagnostica_id, risposta_utente) -> None`
- `get_diagnostica(assessment_id) -> list[dict]`
- `get_pesi_assessment(assessment_id) -> list[dict]`

### `cicerone.mcda.calcolo`
- `classifica_framework(assessment_id) -> list[dict]`  — chiavi: `nome`, `punteggio`, `framework_id` (ordinata, migliore prima)
- `breakdown_per_criterio(assessment_id, framework_id) -> list[dict]`  — chiavi: `nome`, `voto`, `peso`, `contributo`
- `vincitore(assessment_id) -> dict | None`

### `cicerone.llm.intervista`
- `domanda_per_criterio(criterio: dict, contesto: dict | None) -> str`
- `parse_risposta(criterio: dict, contesto: dict | None, risposta: str, is_retry: bool = False) -> dict`
  — chiavi nel risultato: `needs_clarification` (bool), `clarification_question` (str|None),
  `livello` (str), `peso` (float), `motivazione` (str|None), `ambiguo` (bool)

### `cicerone.llm.diagnostica`
- `next_question(assessment_id, domanda_precedente=None, risposta_precedente=None) -> str | None`
  — ritorna la prossima domanda, oppure **`None` quando la diagnostica è finita**

### `cicerone.llm.report`
- `genera_report(assessment_id) -> str`  — ritorna markdown (lento: 20–30s)

### `cicerone.llm._client`
- `set_api_key(api_key: str | None) -> None`  — imposta la chiave per le call successive
- `get_client() -> Anthropic`

**Verifica chiave** (replica la logica dell'onboarding attuale): chiama
`set_api_key(k)` poi un ping minimo:
`get_client().messages.create(model="claude-haiku-4-5-20251001", max_tokens=10, messages=[{"role":"user","content":"ping"}])`.
Successo = chiave valida; eccezione = mostra il messaggio d'errore (troncato).

---

## 5. Dati di dominio & stato

### Costanti (riusabili — sono in `cicerone/ui/_pages/_shared.py`, solo lettura)
- `SHEET = "rediness"` (l'unico foglio usato)
- `FASI` = lista ordinata `(chiave, etichetta)` delle 5 fasi
- `ROMANI = ["I","II","III","IV","V"]`
- `LIVELLO_PESO` = mappa livello→peso (Fondamentale 10.0 … Non importante 0.0)
- Liste onboarding (in `cicerone/ui/_pages/onboarding.py`): `SETTORI`,
  `FASCE_DIPENDENTI`, `FASCE_FATTURATO`, `USO_AI_OPZIONI`, `NAZIONI_EUROPA`

### `contesto_azienda` (dict) — chiavi attese dal backend:
`nome_azienda`, `settore`, `fascia_dipendenti`, `nazione`, `regione` (opz),
`uso_ai_attuale`, `fascia_fatturato`, `note` (opz).

### `AppState` — campi minimi da replicare (oggi sono in `session_state`):
`step`, `contesto_azienda`, `assessment_id`, `criteri`, `idx_criterio`,
`intervista_*` (domanda corrente, chat per criterio, conteggio chiarimenti,
ultimo parsed), `diag_domanda_corrente`, `report_markdown`, `api_key`,
`api_key_valida`, `fasi_raggiunte`.

### Palette brand (unica cosa da riusare dal design system TUI)
| Ruolo | Colore |
|---|---|
| Accento (oro) | `#E8B84B` |
| Testo | `#D4D4D4` |
| Testo secondario | `#7A7A7A` |
| Bordi | `#3A3A3A` |
| Errore | `#E85B4B` |
| Successo | `#4BE87A` |

Un solo accento per schermata (l'oro). Tema scuro Flet va bene.

---

## 6. Logica per schermata (replica fedele del comportamento attuale)

Riferimenti di lettura (sola lettura): `cicerone/ui/_pages/*.py`.

- **Onboarding** (`onboarding.py`): blocco API key con verifica; form profilo
  azienda; "Avvia intervista" abilitato solo se chiave valida + nome azienda
  presente. Al submit: crea l'assessment **solo se `assessment_id` è None**
  (tornare indietro non deve invalidare il lavoro), salva contesto, vai a
  intervista.
- **Intervista** (`intervista.py`): per ogni criterio genera la domanda
  iniziale; l'utente risponde; `parse_risposta(...)`. Se
  `needs_clarification` **e** chiarimenti usati `< 2` → fai la domanda di
  chiarimento (incrementa il contatore). Altrimenti `salva_peso(...)` e passa al
  criterio successivo. All'ultimo tentativo permesso passa `is_retry=True`.
  Quando l'indice supera il numero di criteri → vai a vincitore.
- **Vincitore** (`vincitore.py`): `classifica_framework(...)`, mostra i primi 3
  come card, poi la classifica completa (tabella) e un dettaglio
  `breakdown_per_criterio(...)` selezionabile per framework.
- **Diagnostica** (`diagnostica.py`): ciclo `next_question(...)` finché ritorna
  `None`; ogni risposta richiama `next_question(assessment_id,
  domanda_precedente, risposta_precedente)`. A `None` → abilita "Genera report".
- **Report** (`report.py`): `genera_report(...)` una volta, render markdown
  (`ft.Markdown`), pulsante per salvare il `.md` (usa `ft.FilePicker`,
  nome file `report_cicerone_<assessment_id>.md`).

---

## 7. First-run knowledge base (opzionale, fai per ultimo)

I moduli LLM (`diagnostica`, `report`) leggono i `.md` dei framework da una
cartella indicata dall'env `CICERONE_KNOWLEDGE_DIR`. In dev, **prima di
sviluppare**, esporta quella variabile puntando alla cartella locale dei
framework (chiedi al proprietario del repo dov'è, oppure lancia una volta l'app
Streamlit esistente per vedere come la risolve). Senza questa cartella,
diagnostica e report falliscono.

La schermata di setup interattivo (clona repo privato via token / scegli
cartella) esiste oggi nel launcher desktop. **Per ora non serve replicarla**:
basta l'env var in dev. Se vorrai impacchettare l'app, la `knowledge_setup.py`
diventerà una view Flet — ma è fuori scope per la prima versione.

---

## 8. Come avviare (senza toccare le dipendenze del progetto)

Flet **non** va aggiunto a `pyproject.toml`. Usalo in modo effimero con `uv`:

```bash
# dalla radice del repo
export CICERONE_KNOWLEDGE_DIR=/percorso/alla/knowledge   # vedi §7
uv run --with flet python flet_ui/main.py
```

`--with flet` installa Flet solo per quella esecuzione, senza modificare
`pyproject.toml` né `uv.lock`. Il package `cicerone` è già editable, quindi gli
import del backend funzionano.

Per non sporcare il DB di sviluppo, puoi puntare a un DB usa-e-getta:
```bash
export CICERONE_DB_PATH=/tmp/cicerone_flet_dev.sqlite
```

---

## 9. Verifica di non-regressione (golden master)

Il backend non cambia: **a parità di input, punteggi MCDA e report devono essere
identici** tra Streamlit e Flet.

1. Esegui un assessment completo sull'app Streamlit esistente
   (`uv run streamlit run cicerone/ui/app.py`) con dati noti. Annota la
   classifica framework e salva il `report.md`.
2. Ripeti **gli stessi input** sulla tua UI Flet (stesso DB o stessi dati).
3. Confronta: la classifica di `classifica_framework` e il contenuto del report
   devono coincidere. Differenze = bug nella tua UI (stai passando male i dati al
   backend), non nel backend.

Verifica anche, schermata per schermata: nessun freeze della finestra durante le
call LLM (significa che lo spinner threaded funziona).

---

## 10. Checklist finale prima di consegnare

- [ ] Tutto il codice nuovo è dentro `flet_ui/`, niente file modificati fuori.
- [ ] `git status` mostra solo aggiunte in `flet_ui/` (nessuna `M` altrove).
- [ ] `pyproject.toml` e `uv.lock` invariati.
- [ ] Le 5 fasi funzionano end-to-end con una API key reale.
- [ ] Nessun freeze UI durante le attese LLM.
- [ ] Golden master: classifica e report coincidono con Streamlit.
- [ ] `flet_ui/README.md` spiega come avviare.
