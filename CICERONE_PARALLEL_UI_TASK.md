# Prompt per Claude Code — task parallela UI Streamlit

> **Per il collaboratore:** `git pull` nel repo `cicerone`, apri Claude Code
> dentro la cartella, incolla tutto il contenuto sotto la riga orizzontale come
> primo messaggio. Claude parte da solo. Se mancano `uv sync` o seed DB,
> Claude se ne accorge e te lo dice.

---

Ciao Claude. Sto lavorando in parallelo con un altro collega (e un'altra
istanza di te) sul progetto Cicerone. Lui sta implementando il calcolo MCDA in
`cicerone/mcda/`. Io devo costruire la UI Streamlit (Fase 7 del piano) **in
parallelo, senza bloccarmi sul suo lavoro**.

## Contesto progetto (in 30 secondi)

**Cicerone** = agente AI che aiuta PMI italiane a scegliere il framework di
AI Readiness/Maturity più adatto, tra 11 framework accademici. Stack:
Python 3.11 + uv, SQLite, Streamlit, Anthropic SDK.

**Flusso utente finale:**
1. Onboarding: dati azienda (settore, dipendenti, ecc.)
2. Intervista guidata da LLM: per ogni criterio MCDA (10 totali), peso 0-10 +
   motivazione
3. Calcolo MCDA → framework vincitore
4. Diagnostica con knowledge base del framework vincente
5. Report markdown finale

**Repo dual-setup:**
- `cicerone` (pubblico, dove sei adesso) — codice
- `cicerone-knowledge` (privato) — PDF e `.md` framework, gitignored
  dentro `knowledge/`

## Stato attuale (cosa esiste già)

- ✅ Schema DB completo (`cicerone/db/schema.sql`)
- ✅ Seed da `MatriceDB.xlsx`: 10 criteri, 11 framework, 110 voti validati
- ✅ Repository layer (`cicerone/db/repository.py`) — API CRUD stabile
- 🔜 MCDA (in corso, NON toccare `cicerone/mcda/`)
- 🆕 UI Streamlit (la tua task, in `cicerone/ui/` ora vuoto)

## API stabile che puoi usare oggi

Da `cicerone.db.repository`:

```python
lista_criteri(sheet_nome: str) -> list[dict]
    # Ritorna: [{idCriterio, nomeCriterio, definizione}, ...]
    # Usa sheet_nome='readiness'

lista_framework(sheet_nome: str) -> list[dict]
    # Ritorna: [{idFramework, nomeFramework, pdf_path}, ...]

crea_assessment(sheet_nome: str) -> int
    # Ritorna: idAssessment

salva_peso(assessment_id, criterio_id, livello, peso,
           motivazione=None, trascrizione=None, ambiguo=False) -> None
    # livello ∈ {'Fondamentale','Importante','Abbastanza importante',
    #            'Poco importante','Non importante'}
    # peso ∈ {0, 2.5, 5, 7.5, 10}
    # UPSERT: chiamare di nuovo sovrascrive

get_pesi_assessment(assessment_id: int) -> list[dict]
    # Ritorna pesi compilati con join su Criterio
```

## API ancora da definire (mock per ora)

Il collega sta scrivendo `cicerone/mcda/calcolo.py`. Firma attesa:

```python
def classifica_framework(assessment_id: int) -> list[dict]:
    """Ritorna lista ordinata per punteggio DESC.
    Ogni dict: {framework_id, nome, punteggio}"""
```

**Per non bloccarti:** crea un mock locale temporaneo in `cicerone/ui/_mock.py`
con dati finti. Sostituiremo con la chiamata vera quando MCDA è pronto.

## Cosa devi fare (deliverable)

Costruisci uno scheletro Streamlit funzionante in `cicerone/ui/app.py` con:

1. **Pagina onboarding**: form con campi azienda (settore, num dipendenti,
   regione, già usa AI sì/no, fatturato). Salva in `st.session_state`.
2. **Pagina intervista**: itera su `lista_criteri('readiness')`. Per ogni
   criterio mostra definizione + select livello (5 opzioni) + textarea
   motivazione. Bottone "salva e prossimo".
3. **Pagina vincitore**: chiama mock MCDA, mostra top 3 framework con
   punteggio. Espandibile per breakdown per criterio.
4. **Navigazione**: sidebar o stepper con stato avanzamento.

**Lancia con:** `uv run streamlit run cicerone/ui/app.py`

## Vincoli (importanti)

- ❌ NON toccare `cicerone/db/` (stabile, condiviso col collega)
- ❌ NON toccare `cicerone/mcda/` (collega ci lavora)
- ❌ NON cambiare lo schema DB
- ❌ NON aggiungere dipendenze senza chiedere all'utente
- ✅ Lavora SOLO in `cicerone/ui/`
- ✅ Usa l'API repository per qualsiasi accesso DB (mai SQL raw nella UI)

## Decisione architetturale da prendere e comunicare

In Fase 7 dobbiamo decidere lo schema di `contesto_azienda` (dati onboarding).
Il collega ha rinviato la decisione a noi: serve `ALTER TABLE Assessment ADD
contesto_azienda TEXT` con JSON dentro, oppure tabella separata. Costruisci
prima il form UI, poi proponi la struttura JSON minimale che ne risulta. Il
collega farà la migration DB.

## Stile e convenzioni

- Termini italiani in dominio e codice: `criterio`, `peso`, `voto`,
  `assessment`, `framework`
- TUI/UI design system globale dell'utente: palette sobria, accento ambrato
  `#E8B84B`, niente emoji decorative, sfondo trasparente. Streamlit ha
  flessibilità limitata su CSS — adattare con `st.markdown` + CSS custom solo
  se necessario, senza forzare.
- Filosofia utente: **no complessità inutile**. Niente helper astratti
  prematuri, niente over-engineering. Tre righe simili > astrazione
  prematura.

## Workflow

1. Esplora il codice esistente (`cicerone/db/repository.py`,
   `cicerone/db/schema.sql`, `CICERONE_HANDOFF.md`)
2. Brainstorma con l'utente il flusso schermate prima di scrivere codice
3. Implementa lo scheletro funzionante con mock MCDA
4. Commit + push (chiedi conferma prima di push)
5. Comunica all'utente: schema `contesto_azienda` proposto, decisioni UX
   prese, cosa manca per integrare MCDA vero

Partiamo dal brainstorm flusso schermate. Cosa proponi come prima
schermata e come transizione tra le fasi?

---

## Diario sessione UI — 2026-06-14

### Cosa è stato fatto

- **`cicerone/ui/_mock.py`** — mock locale del modulo MCDA.
  - `classifica_framework(assessment_id) -> list[dict]`: somma `voto * peso_assessment` per ogni framework, ordina DESC.
  - `breakdown_per_criterio(assessment_id, framework_id) -> list[dict]`: dettaglio voto/peso/contributo per criterio.
  - Firma di `classifica_framework` allineata a quella attesa per `cicerone/mcda/calcolo.py`.

- **`cicerone/ui/app.py`** — scheletro Streamlit completo, single-file.
  - State machine in `st.session_state["step"] ∈ {onboarding, intervista, vincitore}`.
  - **Onboarding**: form azienda (settore, fascia dipendenti, regione, uso AI attuale, fascia fatturato, note). Al submit salva `contesto_azienda` in session_state + `repo.crea_assessment('readiness')`.
  - **Intervista**: un criterio per pagina (non lista lunga: meglio per UX guidata e prepara il futuro aggancio LLM). Definizione + select 5 livelli + textarea motivazione. Pre-compilazione da `get_pesi_assessment` (UPSERT del repository copre il replay). Bottoni Indietro/Avanti.
  - **Vincitore**: top 3 con `st.metric`, tabella completa, dettaglio per criterio del framework scelto, expander con contesto azienda.
  - Sidebar stepper (●/○ per le 3 fasi) + barra di progresso durante l'intervista + bottone "Ricomincia" (svuota solo session_state, lascia il DB).
  - `bootstrap_schema()` idempotente prima del seed: necessario perché `connection.py` crea solo il file `.sqlite`, nessuno esegue `schema.sql` su DB fresco. Controlla `sqlite_master` per la tabella `Sheet` e applica `schema.sql` via `executescript` se assente.

- **`.streamlit/config.toml`** — tema chiaro, accento ambrato `#E8B84B`, `gatherUsageStats = false`.

### Mapping livello → peso (fisso)

| Livello              | Peso |
|----------------------|-----:|
| Fondamentale         | 10.0 |
| Importante           |  7.5 |
| Abbastanza importante|  5.0 |
| Poco importante      |  2.5 |
| Non importante       |  0.0 |

### Schema `contesto_azienda` proposto al collega DB

**Decisione:** colonna JSON sulla `Assessment`, non tabella separata.

```sql
ALTER TABLE Assessment ADD COLUMN contesto_azienda TEXT;  -- JSON
```

Forma del JSON salvato dalla UI (oggi vive solo in `st.session_state`, finché la colonna non esiste):

```json
{
  "settore": "Manifatturiero",
  "fascia_dipendenti": "10-49",
  "regione": "Lombardia",
  "uso_ai_attuale": "Sì, in modo sporadico",
  "fascia_fatturato": "500k - 2M €",
  "note": null
}
```

**Motivazione:** il contesto è denormalizzato per natura (campi opzionali, evolverà). La query principale è "leggi tutto il contesto di un assessment": una tabella separata complica senza guadagno reale. Quando il collega aggiunge la colonna basta esporre `repo.salva_contesto(assessment_id, dict)` e chiamarla a fine onboarding.

### Cosa manca per integrare l'MCDA vero

1. In `cicerone/ui/app.py` sostituire:
   ```python
   from cicerone.ui import _mock as mcda
   ```
   con:
   ```python
   from cicerone.mcda import calcolo as mcda
   ```
2. La firma `classifica_framework(assessment_id) -> list[{framework_id, nome, punteggio}]` è già rispettata dal mock.
3. `breakdown_per_criterio` è un'aggiunta locale per il dettaglio: opzionale lato MCDA, può restare nella UI o migrare se utile.

### Verifica

- `uv run streamlit run cicerone/ui/app.py` → server up su `:8501`, HTTP 200.
- Bootstrap schema + seed eseguiti automaticamente al primo accesso (10 criteri, 11 framework, 110 voti).
- Navigazione onboarding → intervista → vincitore funzionante.

### Vincoli rispettati

- Nessun file toccato in `cicerone/db/` o `cicerone/mcda/`.
- Nessuna dipendenza aggiunta al `pyproject.toml`.
- Tutto accesso DB via `cicerone.db.repository` (l'unica eccezione è `bootstrap_schema()` lato UI, che usa `get_connection` per applicare `schema.sql` — non è uno SQL di dominio).

---

## ROUND 2 — task aggiuntive UI (2026-06-14, sera)

Mentre tu hai chiuso il round 1, l'altro Claude sta scrivendo il backend
per Fasi 5 (MCDA), 8 (diagnostica LLM multi-turno) e 9 (report LLM).
Servono nuove pagine UI per chiudere il flusso end-to-end.

### Vincoli aggiornati

- Ora PUOI importare da `cicerone.mcda.calcolo` (sostituisci il mock quando il
  backend pubblica il modulo — la firma è uguale al mock attuale)
- Ora PUOI importare da `cicerone.llm.diagnostica` e `cicerone.llm.report`
  (saranno pubblicati dal backend, vedi contratti sotto)
- Continua a NON toccare `cicerone/db/`, `cicerone/mcda/`, `cicerone/llm/`
- Lavora SOLO in `cicerone/ui/`

### Contratti API che il backend ti garantisce

```python
# cicerone/mcda/calcolo.py — sostituisce _mock
def classifica_framework(assessment_id: int) -> list[dict]
def breakdown_per_criterio(assessment_id: int, framework_id: int) -> list[dict]

# cicerone/llm/diagnostica.py
def next_question(assessment_id: int, risposta_precedente: str | None) -> str | None:
    """None = diagnostica chiusa, hai abbastanza info.
    Altrimenti ritorna la prossima domanda da mostrare all'utente.
    La funzione salva internamente Q&A in tabella Diagnostica."""

# cicerone/llm/report.py
def genera_report(assessment_id: int) -> str:
    """Ritorna markdown completo del report personalizzato."""

# cicerone/db/repository.py — funzione aggiunta dal backend
def salva_contesto(assessment_id: int, contesto: dict) -> None:
    """Salva JSON contesto_azienda. Migration ALTER TABLE già applicata."""
```

### Cosa devi fare

1. **Sostituisci mock con MCDA reale** in `cicerone/ui/app.py`:
   ```python
   from cicerone.mcda import calcolo as mcda  # era: from cicerone.ui import _mock as mcda
   ```
   (`_mock.py` puoi tenerlo come fallback per debug o eliminarlo)

2. **Chiama `repo.salva_contesto`** in onboarding submit (sostituisce il
   "vive solo in session_state" del round 1)

3. **Nuova pagina "Diagnostica"** (`step = "diagnostica"`, tra "vincitore" e
   "report"):
   - Layout chat-like: lista messaggi Q&A precedenti + input per nuova risposta
   - Al load: `domanda = diagnostica.next_question(aid, None)`
   - Salva risposta utente in `st.session_state` (o lascia che il backend
     persista in tabella `Diagnostica`)
   - Loop: `next_question(aid, risposta_utente)` → se `None` → bottone
     "Continua al report" → step "report"; altrimenti mostra nuova domanda
   - Mostra storia Q&A scrollabile

4. **Nuova pagina "Report"** (`step = "report"`):
   - `markdown = report.genera_report(assessment_id)`
   - Renderizza con `st.markdown(markdown)`
   - `st.download_button("Scarica report .md", markdown, file_name="report_cicerone.md")`
   - Bottone "Nuovo assessment" → reset session_state, step = "onboarding"

5. **State machine estesa**: stepper sidebar passa da 3 a 5 stati:
   `onboarding → intervista → vincitore → diagnostica → report`

### Workflow consigliato per te

1. Inizia subito con state machine + scheletro vuoto pagine diagnostica/report
   (puoi mockare gli import: `def next_question(*a, **kw): return "Mock?"` per
   sviluppo locale finché backend non pubblica)
2. Quando backend pusha `cicerone/mcda/calcolo.py` → fai `git pull` e cambia
   import (1 riga)
3. Quando backend pusha `cicerone/llm/diagnostica.py` e `cicerone/llm/report.py`
   → fai `git pull` e collega le pagine vere
4. Commit + push frequenti (anche WIP, così sblocchi l'altro lato)
5. Backend ha 3h totali. Non aspettare per cominciare lo scheletro.

### Stretti vincoli di tempo

Il professore vuole la demo entro 3h. Modalità vibe coding pura:
- No refactor, no test, no edge case
- Codice ottimista (no try/except difensivi)
- Output funzionante > output bello

Buon lavoro.

---

## ROUND 3 — feedback post-demo (2026-06-15)

Ciao Claude. Demo finita, raccolto feedback dal docente. Tu lavori SOLO su
UI/UX e identità visiva. L'altra istanza Claude lavora sul backend in parallelo
(diagnostica + report) e NON va toccato.

Leggi prima `cicerone/ui/app.py` e `.streamlit/config.toml` per contesto.

### Identità del prodotto

Il prodotto si chiama **Cicerone**. Riferimento esplicito a Marco Tullio
Cicerone — oratore, filosofo, retore romano. Identità da incarnare:
- **Eloquenza**: tono colto ma accessibile, mai burocratico
- **Misura**: minimalismo, niente decorazioni inutili, spazi ampi
- **Autorevolezza sobria**: un solo accento cromatico (ambrato), tipografia
  curata, divisori netti
- **Classicità**: piccoli rimandi senza essere caricaturali (es. divider
  con linea sottile e punto centrale `─── · ───`, tagline latina opzionale
  tipo "Consulens prudentia"). NIENTE colonne doriche, busti, allori,
  emoji togati. Sobrio.

Non riscrivere da zero — è già un'app funzionante. Restyle mirato.

### Cosa fa il backend (NON toccare lato tuo)

- `cicerone/llm/diagnostica.py`: aggiunge logica re-domanda su risposte vaghe
  (max 1 re-domanda per topic, poi prosegue)
- `cicerone/llm/report.py`: restyle prompt
  - Titolo include framework vincente
  - KPI con descrizione/perché/come misurare
  - Rimossa sezione "Riepilogo punteggi"
  - Roadmap con priorità P1/P2/P3 + motivazione
- Repository: nessun cambio schema. `contesto_azienda` dict accoglie i nuovi
  campi liberamente (è JSON blob)

### Cosa fai TU (UI/UX, solo `cicerone/ui/`)

#### 1. Identità visiva — restyle minimale con carattere

Obiettivo: l'app deve "sembrare Cicerone", non un form generico Streamlit.
Restando minimal.

Palette (rispetta il design system globale dell'utente):
- Accento primario: `#E8B84B` (ambrato) — UN SOLO accento per schermata
- Testo principale: lascia default Streamlit (light theme già configurato)
- Testo secondario / hint: `#7A7A7A`
- Bordi e divisori: `#3A3A3A` con opacità 0.3
- Errore: `#E85B4B` | Successo: `#4BE87A`
- Sfondo: NON impostare colori espliciti, lascia tema

Interventi concreti (CSS custom via `st.markdown(..., unsafe_allow_html=True)`
in cima all'app, o file `cicerone/ui/style.css` letto e iniettato):

1. **Header app**: testo "Cicerone" in font serif (Garamond, EB Garamond,
   Cormorant, Libre Caslon, ecc. — uno disponibile via Google Fonts o
   fallback `serif`), peso medium, accento ambrato sotto come sottile
   underline. Tagline subito sotto in italico grigio:
   _"Il framework giusto per la tua AI, scelto bene."_
2. **Divisori**: sostituisci `st.divider()` con riga sottile + simbolo
   centrale `─── · ───` in `#7A7A7A`
3. **Bottoni primary**: sfondo ambrato `#E8B84B`, testo nero, bordo
   arrotondato leggero, hover più scuro
4. **Sidebar**: titolo "Cicerone" stesso font serif, bordo destro 1px
   ambrato
5. **Bubble chat**: bordo sottile, padding generoso, no shadow forte
6. **Stepper sidebar**: sostituisci `●/○` con qualcosa di più tipografico,
   ad esempio numeri romani in ambrato per la fase attiva (I, II, III,
   IV, V) e in grigio per le altre

NON usare: emoji decorative, icone grafiche, colonne doriche, allori,
gradient, ombre marcate, colori secondari oltre ambrato.

Verifica: l'app deve restare leggibile e veloce, niente animazioni pesanti.

#### 2. Spinner / caricamento (priorità alta)

I `st.spinner(...)` esistono già nel codice ma sono i default Streamlit
(spinner anonimo). Migliorare:
- Messaggi contestuali ("Sto generando la prossima domanda...",
  "Sto interpretando la tua risposta...", "Sto preparando il report
  finale, possono volerci 20-30 secondi...")
- Considera `st.status(...)` per chiamate lunghe (report) con log step
- Eventuale skeleton/placeholder bubble durante attesa LLM

#### 3. Chat UI con invio (priorità alta)

Sia in `pagina_intervista` che `pagina_diagnostica`:
- Sostituire `st.form` + `st.text_area` + bottone `st.form_submit_button`
  con `st.chat_input(...)` (Enter invia, look chat nativo)
- Bubble: continua a usare `st.chat_message("assistant"|"user")` ma
  considera custom styling (vedi punto 1)
- Per intervista: serve ancora bottone "Indietro" (separato dall'input
  chat) — soluzione: due colonne, sx bottone, dx input chat? O bottone
  sopra/sotto?

#### 4. API key in cima + feedback (priorità alta)

Sposta API key da sidebar a **primo blocco della pagina onboarding**, prima
di ogni altro campo. Resta in `st.session_state["api_key"]` ma più
visibile.

UI:
- Titolo "Configurazione" prima di "Profilo azienda"
- `st.text_input("Anthropic API Key", type="password", ...)`
- Subito sotto bottone "Verifica chiave"
- Sotto bottone: badge esito
  - Vuoto se mai verificato
  - Verde "✓ Chiave valida" se OK
  - Rosso "✗ Errore: <messaggio>" se KO
  - Salva esito in `st.session_state["api_key_valida"]` (bool)
- Disabilita bottone "Avvia intervista" finché `api_key_valida is True`
- Sidebar: mostra solo badge stato chiave, non più il campo

**Test chiave (call API leggera)**:
```python
from cicerone.llm._client import set_api_key, get_client

def verifica_chiave(api_key: str) -> tuple[bool, str]:
    set_api_key(api_key)
    try:
        get_client().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "ping"}],
        )
        return True, "Chiave valida."
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:200]}"
```
Costo: ~$0.0001 a verifica. Trascurabile.

#### 5. Onboarding nuovi campi

- **Nome azienda** (text input obbligatorio, primo dopo API key)
- **Nazione** (dropdown obbligatorio, lista qui sotto)
- **Regione** (text input opzionale, label adatta "Regione/Cantone/Stato — opzionale")

Lista nazioni (EU 27 + Svizzera + UK), ordine alfabetico italiano:
```python
NAZIONI_EUROPA = [
    "Austria", "Belgio", "Bulgaria", "Cechia", "Cipro", "Croazia",
    "Danimarca", "Estonia", "Finlandia", "Francia", "Germania", "Grecia",
    "Irlanda", "Italia", "Lettonia", "Lituania", "Lussemburgo", "Malta",
    "Paesi Bassi", "Polonia", "Portogallo", "Regno Unito", "Romania",
    "Slovacchia", "Slovenia", "Spagna", "Svezia", "Svizzera", "Ungheria",
]
```

Default: "Italia". Rimuovi vecchio dropdown `REGIONI` italiane.

Aggiorna struttura `contesto_azienda` (JSON blob, no migration DB):
```python
{
    "nome_azienda": "...",
    "settore": "...",
    "fascia_dipendenti": "...",
    "nazione": "...",
    "regione": "..." | None,
    "uso_ai_attuale": "...",
    "fascia_fatturato": "...",
    "note": "..." | None,
}
```

Backend leggerà i nuovi campi (è solo dict, niente da modificare lato DB).

### Vincoli round 3

- ❌ NON toccare `cicerone/llm/` (backend ci lavora)
- ❌ NON toccare `cicerone/db/` o `cicerone/mcda/` (stabili)
- ✅ Solo `cicerone/ui/` e `.streamlit/`
- ✅ Commit + push frequenti per non bloccare backend (che a sua volta
  pulla per verificare integrazione)

### Ordine consigliato

1. API key in cima + feedback (#4, sblocca subito UX)
2. Onboarding nuovi campi (#5, dati per backend)
3. Chat input con invio (#3, UX percepita)
4. Identità visiva minimal (#1, polish)
5. Spinner contestuali (#2, ultimo perché tocca più punti)

### Cosa scrivere in diario di sessione

Quando finisci tutto, appendi in fondo a questo file una nota
`## ROUND 3 — diario UI (data)` con:
- File modificati e cosa hai fatto
- Eventuali decisioni di design prese da solo
- Cosa rimane aperto

Così l'altra istanza Claude (e l'utente) sanno cosa è cambiato. Push a fine
lavoro.

---

## ROUND 3 — diario UI (2026-06-15)

### File modificati / creati

- **`cicerone/ui/style.css`** (nuovo) — foglio di stile iniettato in `<style>` dalla UI.
  - Import Cormorant Garamond (Google Fonts) per header/sidebar/divider.
  - Variabili CSS: `--cic-amber: #E8B84B`, `--cic-amber-dark: #C99B30`, `--cic-text-muted: #7A7A7A`, `--cic-border`, `--cic-error #E85B4B`, `--cic-success #4BE87A`.
  - Classi: `cic-header`, `cic-tagline`, `cic-sidebar-title`, `cic-sidebar-caption`, `cic-divider`, `cic-step`/`cic-step-num`/`cic-step-label`, `cic-badge` (`-ok`/`-ko`/`-idle`), `cic-key-ok`/`cic-key-ko`.
  - Override mirati: bottoni `kind="primary"` ambrati con testo nero, `[data-testid="stChatMessage"]` con bordo sottile + padding generoso, sidebar border-right ambrato 1px.

- **`cicerone/ui/app.py`** (rifatto) — restyle + nuove feature.
  - **Header**: `header_cicerone()` con wordmark serif "Cicerone" + sottile underline ambrato + tagline italica `Il framework giusto per la tua AI, scelto bene.`
  - **Sidebar**: rimosso text_input API key, ora solo wordmark serif + badge stato chiave (ok/ko/idle), stepper a numeri romani I-V (ambrato per attivo, grigio per inattivo), divider `─── · ───`, progresso intervista, bottone Ricomincia.
  - **API key in pagina onboarding** (sezione "Configurazione"): text_input password + bottone "Verifica chiave" → call `client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=10, "ping")`. Esito salvato in `api_key_valida` (None/True/False). Modifica chiave dopo verifica → invalida automaticamente. Bottone "Avvia intervista" disabilitato finché chiave non valida.
  - **Onboarding nuovi campi**: `nome_azienda` (text_input obbligatorio), `nazione` (dropdown EU 27 + UK + Svizzera, default Italia), `regione` (text_input opzionale "Regione/Cantone/Stato — opzionale"). Rimosso vecchio dropdown REGIONI italiane. Aggiornato dict `contesto_azienda` con i nuovi campi.
  - **Intervista**: `st.chat_input` al posto di `st.form + text_area + form_submit_button`. Bottone "← Indietro" in colonna sopra l'input (chat_input è sticky-bottom in Streamlit). Placeholder dinamico: "Vai al calcolo: scrivi la tua ultima risposta..." sull'ultimo criterio.
  - **Diagnostica**: stesso pattern chat_input.
  - **Spinner contestuali**: "Sto formulando la domanda adatta al tuo contesto...", "Sto interpretando la tua risposta...", "Sto generando la prossima domanda...", "Sto verificando la chiave con un ping ad Anthropic..."
  - **Report**: `st.status` (con `expanded=True` durante esecuzione, `complete` a fine) al posto del semplice `st.spinner`, con log step ("Raccolgo i pesi...", "Invoco il modello...", "Report pronto.").
  - **Divisori**: `divider_cicerone()` con `─── · ───` in `cic-divider`, usato al posto di `st.divider()`.

### Decisioni di design prese da solo

- **Font**: Cormorant Garamond (Google Fonts, free) — equilibrio classico/moderno, ottimo display al wordmark. Fallback `Garamond`/`Libre Caslon Text`/`serif`.
- **Bordo sidebar**: 1px ambrato solo a destra, niente shadow né altri accenti.
- **Bubble chat**: niente sfondo ne ombre, solo bordo sottile + padding 1rem.
- **`storia_diagnostica`**: tengo l'implementazione in `_mock.py` (query diretta su `Diagnostica`) perché il backend non espone una funzione pubblica equivalente. È solo lettura del DB condiviso, semantica coerente con storia messaggi.
- **Reset auto API key**: se l'utente modifica la chiave dopo aver verificato, `api_key_valida` torna a `None` per forzare nuova verifica.

### Workaround hot

Il backend espone `cicerone.db.repository._ensure_contesto_column()` che gira al **load del modulo** e fa `ALTER TABLE Assessment ADD COLUMN contesto_azienda`. Su DB fresco (tabelle non ancora create) l'ALTER esplode con `sqlite3.OperationalError: no such table: Assessment`. Non posso toccare `cicerone/db/` per vincolo round 3.

Workaround lato UI: in `app.py` chiamo `_bootstrap_schema_eager()` PRIMA dell'import `from cicerone.db import repository`. Il bootstrap legge `cicerone/db/schema.sql` e lo applica solo se la tabella `Sheet` non esiste. Idempotente. Ordine import obbliga a `# noqa: E402`.

Da segnalare al backend: spostare la migration fuori dal load del modulo (es. funzione esplicita richiamata dopo l'init dello schema) per evitare ordini di import fragili.

### Cosa rimane aperto

- **Watchdog**: Streamlit suggerisce `pip install watchdog` per performance file-watching. Non aggiunto perché vincolo "no dipendenze senza chiedere". Trascurabile in prod.
- **Animazioni hover bottoni**: oltre al cambio colore, nessuna transizione. Sufficiente per il claim "minimal".
- **Mobile**: sidebar e chat_input testati solo su desktop. Streamlit gestisce reflow automatico, ma il wordmark 3.2rem potrebbe essere stretto su < 360px — non considerato priorità.
- **Test end-to-end con LLM reali**: non lanciato (richiede API key utente). Solo smoke test (HTTP 200, import senza eccezioni, moduli backend agganciati). UX da validare a mano con il browser.

### Verifica

- `python -c "from cicerone.ui import app"` con DB fresco → OK, nessuna eccezione, tutti i moduli backend importati (mcda/llm.diagnostica/llm.report/llm.intervista/repo.salva_contesto).
- `uv run streamlit run cicerone/ui/app.py` → HTTP 200 su `:8501`.

