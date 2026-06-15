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

## ROUND 4 — fix post-demo 2 (2026-06-15, notte)

Demo 2 fatta. Round 3 fixato la maggior parte ma sono emersi 3 nuovi
problemi lato UI/UX. Backend sta lavorando in parallelo su fix diagnostica
e intervista — NON toccare `cicerone/llm/`.

### Fix da fare (solo UI in `cicerone/ui/app.py` + style.css)

#### 1. Sidebar fasi cliccabili (navigazione)

Attualmente le fasi nella sidebar sono solo label visuali. Renderle
cliccabili così l'utente può tornare indietro alle schede precedenti per
rivedere quello che ha fatto.

Regole:
- Cliccabile SOLO se la fase è stata già raggiunta o è quella corrente
  (no salti in avanti su fasi non ancora attive)
- Click → cambia `st.session_state.step` + `st.rerun()`
- Visualmente: cursor pointer + hover leggero ambrato per le fasi
  disponibili; grigio per quelle non ancora sbloccate
- Quando si torna indietro, le pagine precedenti devono mostrare lo
  STATO già compilato (il DB lo persiste, leggi via repository):
  - Onboarding: pre-riempire campi da `st.session_state.contesto_azienda`
  - Intervista: già supportato via `repo.get_pesi_assessment` (vedi
    codice esistente che usa `precompilato`)
  - Vincitore: ricalcola sempre, è view-only
  - Diagnostica: già mostra storia Q&A via `repo.storia_diagnostica`
  - Report: usa `st.session_state.report_markdown` se già generato

Per sapere quali fasi sono "sbloccate", traccia in session_state:
```python
st.session_state.setdefault("fasi_raggiunte", {"onboarding"})
# Aggiungi a fasi_raggiunte ogni volta che si passa a un nuovo step
```

Implementa come bottoni Streamlit (non markdown) per gestire il click:
`st.sidebar.button(label, key=..., disabled=not raggiunta)`. Puoi
stilarli via CSS custom per integrarli nel design (numero romano +
label).

#### 2. Spinner di caricamento centrato e visibile

Gli spinner attuali (`st.spinner`) sono piccoli e poco visibili. Per le
attese LLM (intervista, diagnostica, report) servono spinner più
prominenti.

Opzioni:
- Usa `st.spinner` con messaggio chiaro + un blocco `st.empty()` /
  overlay CSS che centra un loader animato (SVG inline o CSS pure
  spinner) nel mezzo della pagina
- Oppure usa `st.status(..., expanded=True)` che mostra un container
  con animazione + log step
- Considera componente `streamlit_extras` se già nel progetto, altrimenti
  resta su CSS puro (no nuove deps)

Stile: cerchio ambrato `#E8B84B` rotante su sfondo semi-trasparente,
testo italico sotto con messaggio contestuale. Coerente con identità
Cicerone (sobrio, no caricature).

#### 3. Pagina "Framework vincitore" — titoli leggibili

Bug visibile in screenshot demo 2: nella sezione "Framework più adatti"
mostriamo i 3 podio con `st.metric` che li mette tutti in orizzontale
su 3 colonne. I nomi framework sono lunghi (60-80 char) → si troncano
con "..." rendendo illeggibili.

Fix proposto:
- Sostituire layout `st.columns(3) + st.metric` con un layout VERTICALE
  o a card che permette wrap del titolo su più righe:
  - Opzione A: lista verticale con 3 "card" stacked, ognuna con
    medaglia (1°/2°/3°) + nome completo wrappato + punteggio in
    ambrato grosso
  - Opzione B: 3 colonne ma con `st.container` + markdown invece di
    st.metric, così il testo wrappa
- Sotto resta la "Classifica completa" come tabella che già funziona

### Cosa fa il backend (NON toccare)

- `cicerone/llm/diagnostica.py`: cap `MAX_DOMANDE=5` ora conta SOLO le
  domande "vere" (non re-ask). Re-ask hanno cap separato (`MAX_RIASK=3`).
  Quindi totale possibile: 5 + 3 = 8 turn, ma le 5 vere garantite. Fixa
  il bug "si è bloccato a 7 perché contava re-ask".
- `cicerone/llm/intervista.py`: aggiunta gestione "non capito". Se utente
  risponde vago o esplicitamente "non ho capito", `parse_risposta`
  ritorna `{"needs_clarification": True, "clarification_question": "...",
  ...}`. Tu UI dovrai:
  - Controllare `if parsed.get("needs_clarification"):` PRIMA di
    salvare e avanzare
  - Mostrare `parsed["clarification_question"]` in chat (assistente)
    senza salvare il peso
  - Tracciare in session_state che è già stato fatto 1 chiarimento per
    questo criterio (es. `intervista_clarif_done[criterio_id]`)
  - Al 2° tentativo, accettare comunque il parse normale (anche se
    ambiguo) e procedere

Quando entrambe le parti sono pushate, fai `git pull` e collega le tue
modifiche al nuovo comportamento backend.

### Vincoli round 4

- ❌ NON toccare `cicerone/llm/`, `cicerone/db/`, `cicerone/mcda/`
- ✅ Solo `cicerone/ui/` e `.streamlit/` e `cicerone/ui/style.css`
- ✅ Commit + push appena pronto, anche WIP

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

---

## ROUND 4 — diario UI (2026-06-15, notte)

### File modificati

- **`cicerone/ui/app.py`**: refactor con nuovi helper, navigazione cliccabile, gestione clarification, cards top 3, spinner ambrato.
- **`cicerone/ui/style.css`**: classi per sidebar nav, cards framework, spinner ambrato animato.

### Modifiche per fix

#### 1. Sidebar fasi cliccabili
- Rimossi i `<div class="cic-step">` markdown statici, sostituiti con `st.sidebar.button` veri.
- Tracking in `st.session_state["fasi_raggiunte"]` (set di step raggiunti, default `{"onboarding"}`).
- Helper `vai_a(step)` (riusato in tutte le transizioni delle pagine): aggiunge a `fasi_raggiunte` + cambia `step` + rerun.
- Disabilitazione: il bottone è disabled se `step not in fasi_raggiunte` (fase non ancora raggiunta) o `step == fase_corrente` (no rerun inutili sul punto in cui sei).
- Visivo: prefisso `●` sull'attivo (gli altri spazio), numero romano in colonna fissa, label dopo. CSS nuovo (`[data-testid="stSidebar"] .stButton button`) trasparente con hover ambrato e disabled opaco al 55%.

#### 2. Spinner ambrato centrato
- Nuovo helper `@contextmanager def spinner_cicerone(message: str)`: monta un `st.empty()` con cerchio CSS animato (`@keyframes cic-spin`, 52px, bordo ambrato top-color) + testo italico Cormorant Garamond centrato sotto.
- Sostituito `st.spinner(...)` con `spinner_cicerone(...)` in: verifica chiave API, generazione domanda intervista, parse risposta intervista, generazione domanda diagnostica, parse risposta diagnostica, generazione report.
- Per il report mantenevo `st.status` con log step; semplificato a `spinner_cicerone` per coerenza visiva (vedi punto 2 della task, "considera st.status" → ho preferito un solo pattern visivo).

#### 3. Top 3 framework — cards leggibili
- Sostituiti `st.columns(3) + st.metric` con un blocco HTML iniettato: `<div class="cic-cards">` che contiene tre `cic-card` verticali stacked.
- Ogni card: medaglia romana ambrata (I, II, III) a sinistra, nome framework full-width che wrappa su più righe (`word-wrap: break-word`), punteggio in serif ambrato a destra.
- Layout flex, niente troncamento. La classifica completa sotto resta in `st.dataframe`.

### Backend agganciato

- **`needs_clarification`** in `parse_risposta`: in `pagina_intervista`, dopo il parse controllo `parsed.get("needs_clarification")`. Se True e il criterio NON è in `intervista_clarif_done` (set per criterio_id), aggiungo al set, uso `parsed["clarification_question"]` come nuova `intervista_domanda_corrente`, rerun. Al 2° tentativo (criterio già nel set) accetto il parse con fallback (`livello = "Abbastanza importante"`, `peso = 5.0`, `ambiguo = False`).
- **`is_riask`** in `storia_diagnostica`: già coperto da round 3, etichetta "Approfondimento — " sui re-ask resta.

### Re-popolazione stato onboarding

- Quando si torna su onboarding via sidebar, tutti i widget (text_input, selectbox, radio, text_area) sono pre-popolati da `st.session_state.contesto_azienda`.
- Helper `_idx_o_default(lista, valore, default)` per gli indici dei selectbox.
- Modifica importante: alla resubmit del form NON ricreo un nuovo `assessment_id` se ce n'è già uno attivo. Aggiorno solo il contesto in DB via `salva_contesto`. Quindi tornare indietro per correggere un campo NON invalida i pesi già compilati nell'intervista.

### Tagline aggiornata

- Da "Il framework giusto per la tua AI, scelto bene." a **"La voce che orienta la tua PMI nell'adozione dell'AI."** (scelta dell'utente, opzione D fra 5 proposte: tono narrativo, "voce" richiama l'oratore Cicerone, PMI esplicita, AI come obiettivo).

### Decisioni di design prese da solo

- **Marker fase attiva**: `●` ambrato come prefisso del label di bottone, non più underline o background. Non perfetto come UX, ma con `disabled=(attivo or non_raggiunta)` il bottone attivo non è cliccabile e questo basta a comunicarlo.
- **Card medaglie**: numeri romani al posto di "1°/2°/3°" per coerenza con stepper sidebar.
- **`spinner_cicerone` invece di `st.status` sul report**: un solo linguaggio visivo. `st.status` con i log step era informativo ma rompeva la palette/font. Preferenza per identità coerente.
- **`assessment_id` persistente attraverso navigate-back**: scelta esplicita per non perdere lavoro se utente torna sull'onboarding a correggere un campo.

### Cosa rimane aperto

- **CSS sidebar bottoni**: la regola `[data-testid="stSidebar"] .stButton button` colpisce anche il bottone "Ricomincia". Visivamente coerente (trasparente, hover ambrato), ma il comportamento è azione distruttiva con stile blando. Da valutare se differenziarlo (es. colore rosso muted) — non priorità.
- **Test del flusso clarification reale**: la logica è sbloccabile solo con API key e risposte vaghe. Smoke test fatto via `python -c "from cicerone.ui import app"` (import senza errori). UX end-to-end da validare dal browser.
- **Stepper attivo con `●` ASCII**: sufficiente per ora, in futuro un'icona inline SVG ambrato sarebbe più coerente con l'identità classica.

### Verifica

- `python -c "from cicerone.ui import app"` → OK, tutte le funzioni esistono (`vai_a`, `spinner_cicerone`, `FASI`, `verifica_chiave`).
- `uv run streamlit run cicerone/ui/app.py` → HTTP 200 su `:8501`, nessun errore in log.

---

## ROUND 5 — Wrap desktop macOS + .dmg (2026-06-15)

> **Per il collaboratore:** `git pull` nel repo `cicerone`, apri Claude Code
> nella cartella, incolla TUTTO il contenuto di questa sezione (da
> "Contesto round 5" fino a fine documento) come primo messaggio. Claude
> parte da solo. Lavorerai SOLO su packaging desktop: la UI Streamlit è
> già completa e non va modificata.

### Contesto round 5

Cicerone è oggi una web app Streamlit (`uv run streamlit run cicerone/ui/app.py`).
Obiettivo prima release: **`Cicerone.dmg` distribuibile su macOS**. Doppio click
sul `.dmg` → drag&drop in Applications → doppio click sull'icona → si apre
finestra desktop con dentro l'app Streamlit. Per l'utente finale: zero
terminale, zero `pip install`, zero `streamlit run`.

**Architettura wrap:**

```
Cicerone.app  (bundle macOS)
 └─ launcher Python (bootstrap):
     1. avvia streamlit come subprocess su porta random localhost
     2. attende che il server risponda
     3. apre finestra pywebview puntando a http://localhost:PORT
     4. alla chiusura finestra → killa subprocess streamlit
```

Streamlit gira dentro al bundle. L'utente vede SOLO la finestra desktop,
non sa che dietro c'è un web server locale.

### Vincoli round 5

- ❌ NON toccare `cicerone/ui/` — UI è finita e validata, non riaprire
- ❌ NON toccare `cicerone/llm/`, `cicerone/mcda/`, `cicerone/db/repository.py`,
      `cicerone/db/schema.sql`, `cicerone/db/seed.py`
- ✅ PUOI modificare `cicerone/db/connection.py` SOLO per leggere `DB_PATH`
      da env var `CICERONE_DB_PATH` se presente (necessario per bundle:
      vedi "Pitfall #3" sotto). Una riga di patch.
- ✅ PUOI modificare `cicerone/llm/diagnostica.py` e `cicerone/llm/report.py`
      SOLO per leggere `KNOWLEDGE_DIR` da env var `CICERONE_KNOWLEDGE_DIR`
      se presente (vedi "Knowledge base distribuzione" sotto). Due righe per file.
- ✅ PUOI aggiungere file nuovi in:
   - `cicerone/desktop.py` (launcher)
   - `packaging/` (cartella nuova: spec PyInstaller, script build .dmg, icona)
- ✅ PUOI aggiungere dipendenze `pywebview` e `pyinstaller` a `pyproject.toml`
      come `[dependency-groups]` `packaging` (NON come runtime dep — non vogliamo
      pywebview nel wheel pubblicato)
- ✅ PUOI usare `create-dmg` via Homebrew (`brew install create-dmg`) per
      generare il `.dmg`. Se non disponibile, fallback a `hdiutil` nativo macOS.
- ❌ NO code signing, NO notarization in questo round (prima release dev-only;
      l'utente accetterà il warning Gatekeeper "developer non identificato").

### Stack tecnico raccomandato

| Componente | Scelta | Perché |
|------------|--------|--------|
| Wrapper window | `pywebview` (WKWebView backend) | Più semplice di Tauri/Electron, Python puro, integrato bene con subprocess |
| Bundler | `pyinstaller` (one-folder, NON onefile) | Più affidabile di `py2app` con Streamlit. Onefile rallenta startup di molto. |
| .dmg | `create-dmg` (Homebrew) | Più semplice di hdiutil + AppleScript |
| Python runtime | uv → venv → pyinstaller usa quel Python | Stesso ambiente del dev |

### File da creare

#### 1. `cicerone/desktop.py` — launcher
Cosa fa:
1. Determina porta libera (`socket.socket().bind(('localhost', 0))`).
2. Imposta env var `CICERONE_DB_PATH` a `~/Library/Application Support/Cicerone/cicerone.sqlite` (creando dir se non esiste).
3. Avvia subprocess: `streamlit run <path_app.py> --server.port=<PORT> --server.headless=true --browser.gatherUsageStats=false --server.address=127.0.0.1`.
4. Polling HTTP su `http://127.0.0.1:PORT/_stcore/health` finché 200 (timeout 30s).
5. `webview.create_window("Cicerone", f"http://127.0.0.1:{PORT}", width=1200, height=800)` + `webview.start()`.
6. Su `webview.start()` ritorno (finestra chiusa) → `subprocess.terminate()` + wait.

Punti dolenti da gestire:
- Path di `app.py` dentro il bundle: usa `sys._MEIPASS` se `getattr(sys, 'frozen', False)`, altrimenti path normale dev.
- Path di `streamlit` eseguibile dentro il bundle: NON chiamare `streamlit` come comando shell, usa `streamlit.web.bootstrap.run(...)` direttamente in-process oppure `python -m streamlit run`. Preferibile: `streamlit.web.bootstrap.run(app_path, "", [], {})` in un `threading.Thread` invece del subprocess. Più portabile nel bundle.
- Se preferisci subprocess: trova `sys.executable`, lancia `[sys.executable, "-m", "streamlit", "run", ...]`.

#### 2. `packaging/cicerone.spec` — PyInstaller spec
Punti chiave (Claude, NON copiare ciecamente: leggi la doc PyInstaller corrente e adatta):
- `datas` deve includere:
   - `('cicerone/db/schema.sql', 'cicerone/db')`
   - `('cicerone/ui/style.css', 'cicerone/ui')`
   - `('cicerone/ui/app.py', 'cicerone/ui')` — sì, app.py va trasportata come data per `streamlit run`
   - **NON bundlare `knowledge/frameworks/`** — contenuto privato, va distribuito separatamente (vedi sezione "Knowledge base distribuzione" sotto)
   - `('MatriceDB.xlsx', '.')` — usato dal seed
   - `('.streamlit/config.toml', '.streamlit')`
- `hiddenimports` deve includere streamlit submoduli che PyInstaller non rileva: usa `collect_submodules('streamlit')` e `collect_submodules('anthropic')`.
- `datas += collect_data_files('streamlit')` — Streamlit ha tanti asset statici (frontend bundle React, CSS).
- Target macOS: `BUNDLE(name='Cicerone.app', icon='packaging/icon.icns', bundle_identifier='com.cicerone.desktop', info_plist={...})`.
- `info_plist`: `LSUIElement = False` (app normale), `NSHighResolutionCapable = True`, `CFBundleShortVersionString = '0.1.0'`.

#### 3. `packaging/build.sh` — script orchestrazione
Sequenza:
```bash
#!/bin/bash
set -euo pipefail
rm -rf build dist
uv run pyinstaller packaging/cicerone.spec --clean --noconfirm
# verifica che dist/Cicerone.app esista
test -d dist/Cicerone.app || { echo "Build app fallito"; exit 1; }
# .dmg
create-dmg \
  --volname "Cicerone" \
  --window-size 600 400 \
  --icon "Cicerone.app" 150 200 \
  --app-drop-link 450 200 \
  --no-internet-enable \
  dist/Cicerone.dmg dist/Cicerone.app
```

#### 4. `packaging/icon.icns` — icona Dock
Genera da PNG 1024×1024. Se non hai grafica, chiedi all'utente: minimo serve un file segnaposto.
Comando da PNG: `iconutil -c icns packaging/icon.iconset` dopo aver creato `iconset` con 9 risoluzioni standard (16, 32, 64, 128, 256, 512, 1024 + @2x). In alternativa script Python con `Pillow`. Se l'utente non fornisce PNG, segnala e genera placeholder grigio con scritta "C".

### Pitfall noti — leggili PRIMA di iniziare

#### Pitfall #1 — bundling Streamlit
Streamlit è notoriamente difficile da bundlare. Problemi comuni:
- `streamlit.web.cli` cerca file relativi al package install path → con `--collect-data streamlit` di solito risolto
- Static frontend `streamlit/static/` deve essere presente nel bundle
- Versioni Streamlit ≥ 1.30 hanno meno problemi
Se incontri errori "ModuleNotFoundError" al primo run, aggiungi hiddenimport mancante e ricompila. NON arrenderti al primo errore: aspettati 2-3 cicli di build+test.

#### Pitfall #2 — Anthropic SDK + certificati SSL
`anthropic` usa `httpx` → ha bisogno di `certifi`. PyInstaller di solito lo cattura, ma verifica: `datas += collect_data_files('certifi')`. Senza, le chiamate Claude falliscono con `SSL: CERTIFICATE_VERIFY_FAILED` nel bundle.

#### Pitfall #3 — DB path dentro .app
`cicerone/db/connection.py` ha:
```python
DB_PATH = Path(__file__).parent.parent / "data" / "cicerone.sqlite"
```
Dentro un `.app`, questo path è SOLO LETTURA. SQLite crash a primo write.

**Fix minimo (UNICA modifica permessa fuori da `desktop.py` / `packaging/`):**
```python
import os
DB_PATH = Path(os.environ["CICERONE_DB_PATH"]) if os.environ.get("CICERONE_DB_PATH") else Path(__file__).parent.parent / "data" / "cicerone.sqlite"
```
Il launcher `desktop.py` imposta `CICERONE_DB_PATH` a
`~/Library/Application Support/Cicerone/cicerone.sqlite` prima di avviare
streamlit. Dev mode senza env var → comportamento attuale invariato.

#### Pitfall #4 — Knowledge base FUORI dal bundle
**Decisione architetturale:** la knowledge base resta nel repo privato
`cicerone-knowledge` e NON viene bundlata nel `.dmg`. Distribuzione separata
gestita dal launcher al primo avvio. Vedi sezione dedicata sotto.

#### Pitfall #5 — porta occupata
Se l'utente apre due istanze, la seconda fallisce sulla porta. Soluzione: porta
random ogni volta (`socket.bind(('', 0))` → leggi `.getsockname()[1]`).

#### Pitfall #6 — primo startup lento
Streamlit + Python interpreter dentro un bundle one-folder = 3-5 sec di delay.
Il launcher deve mostrare ALMENO la finestra pywebview con un loader prima che
streamlit risponda, altrimenti l'utente pensa che si sia bloccato. Mostra
finestra subito + polling health in background + redirect quando ready. Oppure
mostra splash HTML inline.

#### Pitfall #7 — Gatekeeper "developer non identificato"
.dmg non firmato → utente al primo apertura vede warning Apple:
"Cicerone non può essere aperto perché lo sviluppatore non può essere
verificato". Fix utente: Sistema → Privacy → "Apri comunque". Documenta
in `packaging/README.md` come istruzione per l'utente.

### Knowledge base — distribuzione separata

Knowledge base = repo privato `cicerone-knowledge` (proprietà utente).
NON va dentro al `.dmg` per due ragioni: (1) contenuto privato non
distribuibile; (2) si aggiorna indipendentemente dall'app.

**Target persistenza:**
```
~/Library/Application Support/Cicerone/
  ├── cicerone.sqlite              ← DB utente
  └── knowledge/
      └── frameworks/
          ├── tortoise.md
          ├── microsoft.md
          └── ... (11 file .md)
```

**Override env var** (analogo a `CICERONE_DB_PATH`):

In `cicerone/llm/diagnostica.py` e `cicerone/llm/report.py`, sostituisci:
```python
KNOWLEDGE_DIR = Path(__file__).parent.parent.parent / "knowledge" / "frameworks"
```
con:
```python
import os
KNOWLEDGE_DIR = Path(os.environ["CICERONE_KNOWLEDGE_DIR"]) if os.environ.get("CICERONE_KNOWLEDGE_DIR") else Path(__file__).parent.parent.parent / "knowledge" / "frameworks"
```
Dev mode senza env var → comportamento invariato (punta a `knowledge/frameworks/` del repo).

**First-run setup nel launcher `desktop.py`:**

All'avvio, prima di lanciare Streamlit, il launcher verifica:
```python
knowledge_dir = Path.home() / "Library/Application Support/Cicerone/knowledge/frameworks"
if not knowledge_dir.exists() or not any(knowledge_dir.glob("*.md")):
    # mostra finestra setup
    run_setup_window(knowledge_dir.parent)
os.environ["CICERONE_KNOWLEDGE_DIR"] = str(knowledge_dir)
```

**Finestra setup** = piccola finestra `pywebview` con HTML inline (no Streamlit).
Due opzioni in tab:

**Opzione A — Clone repo privato GitHub** (preferita):
- Form: input "GitHub Personal Access Token" + input "Repo URL" (default precompilato `https://github.com/FloshDev/cicerone-knowledge.git`)
- Bottone "Scarica knowledge"
- Esegue: `git clone https://<TOKEN>@<URL_SENZA_HTTPS>` dentro `~/Library/Application Support/Cicerone/knowledge_repo/`
- Poi crea symlink o copia `knowledge_repo/frameworks/` → `knowledge/frameworks/`
- Salva token (criptato con `keyring` macOS, NON in plaintext) per refresh futuri

**Opzione B — Cartella locale**:
- Bottone "Scegli cartella" → folder picker nativo (webview.create_file_dialog)
- Utente seleziona cartella esistente con i `.md`
- Launcher copia (o symlinka) i contenuti in `~/Library/Application Support/Cicerone/knowledge/frameworks/`

Dopo setup completato → chiudi finestra setup → procedi col bootstrap Streamlit
normale.

**Refresh knowledge** (futuro, NON in questo round):
- Bottone in app "Aggiorna knowledge" → `git pull` se opzione A usata
- Per ora: utente cancella cartella e riavvia → re-trigger setup

**Dipendenze aggiuntive:**
- `gitpython` (per clone): `uv add --group packaging gitpython`
- OPPURE chiama `git` di sistema via subprocess (più leggero, macOS ha git via Xcode CLT)
- `keyring` per salvare token: `uv add --group packaging keyring`
  - Se complica troppo il bundle, fallback: salva in file `~/Library/Application Support/Cicerone/.token` con `chmod 600`

**Sicurezza token:**
- MAI scrivere il token in chiaro in log/stdout
- MAI committarlo. Path `~/Library/Application Support/Cicerone/` è fuori dal repo per definizione
- Documenta in `packaging/README.md`: utente deve generare PAT con scope `repo:read` solo sul repo `cicerone-knowledge`

### Workflow consigliato (ordine sequenziale)

1. **Esplora codice esistente** (`cicerone/ui/app.py`, `cicerone/db/connection.py`, `cicerone/llm/diagnostica.py`, `cicerone/llm/report.py` per path knowledge).
2. **Aggiungi env var override** a `connection.py` + `llm/diagnostica.py` + `llm/report.py`.
3. **Scrivi `cicerone/desktop.py`** SENZA setup window — solo launch streamlit. Testa: `uv run python -m cicerone.desktop` → finestra pywebview con Streamlit dentro. Itera finché OK in dev, NON bundlare ancora.
4. **Aggiungi setup window** in `desktop.py` (HTML inline pywebview, tab A/B). Testa in dev: cancella `~/Library/Application Support/Cicerone/knowledge/` → riavvia → deve apparire setup. Completa clone con tuo PAT → setup chiude → Streamlit parte. Itera finché flow regge.
5. **Aggiungi deps**: `uv add --group packaging pywebview pyinstaller` (e `gitpython`/`keyring` se decidi di usarle).
6. **Scrivi `packaging/cicerone.spec`** — primo build: `uv run pyinstaller packaging/cicerone.spec --clean`. Aspettati errori. Itera su `hiddenimports` e `datas` finché `dist/Cicerone.app` si lancia.
7. **Genera icona** (anche placeholder).
8. **Scrivi `packaging/build.sh`** + verifica `create-dmg` installato.
9. **Build `.dmg`**: `bash packaging/build.sh`. Apri il `.dmg`, drag in Applications, lancia. Prima esecuzione deve mostrare setup knowledge → chiave API (UI già esistente) → onboarding. Completa flow end-to-end.
10. **Documenta in `packaging/README.md`**: come buildare, warning Gatekeeper, dove finiscono dati utente, come generare PAT GitHub per knowledge.
11. **Commit + push** dopo conferma utente.

### Tempo stimato

2.5h di lavoro mirato (stima rivista per setup knowledge). Distribuzione realistica:
- 15 min: patch env var su `connection.py` + 2 file `llm/`
- 20 min: launcher `desktop.py` base (no setup window)
- 30 min: setup window pywebview (HTML inline, clone repo privato + folder picker)
- 45 min: spec PyInstaller iterativo (qui sta il rischio principale)
- 10 min: icona + build.sh + create-dmg
- 15 min: test end-to-end `.dmg` su cartella `~/Library/Application Support/Cicerone/` pulita
- 10 min: doc packaging

**Se a 1h non hai ancora un `.app` che parte**: ferma, riporta all'utente cosa
blocca. Streamlit + PyInstaller è territorio con trappole — meglio dire "spec
non converge per X" che insistere alla cieca.

### Deliverable

- `dist/Cicerone.dmg` ~150-250 MB (Streamlit + Python + anthropic + knowledge)
- Doppio click `.dmg` → finestra Finder con icona Cicerone + alias Applications
- Drag in Applications → icona compare in Launchpad
- Doppio click icona → finestra Cicerone si apre, flusso end-to-end funziona
- Chiusura finestra → processi streamlit terminati (verifica con Activity Monitor)
- `packaging/README.md` con istruzioni build + warning Gatekeeper per l'utente

### Cosa comunicare a fine round

- Path `.dmg` generato + dimensione
- Quali pitfall hai colpito e come risolti (per documentare per future build)
- Eventuali hiddenimport / collect_data_files aggiunti, così sono nello spec
- Se hai dovuto cambiare qualcosa oltre `desktop.py` / `packaging/` / la riga
  env var in `connection.py` → segnala esplicitamente perché viola i vincoli

Buon lavoro. Niente vibe-build alla cieca: leggi gli errori di PyInstaller
con attenzione, sono verbosi ma puntano al file mancante esatto.


## ROUND 5 — diario packaging (2026-06-15, pomeriggio)

### File creati / modificati

File creati:
- `cicerone/desktop.py` — launcher pywebview + streamlit in-process (thread daemon). Vedi nota signal monkey-patch sotto.
- `packaging/cicerone.spec` — spec PyInstaller one-folder.
- `packaging/icon.icns` — placeholder 1024x1024 generato con Pillow + `iconutil` (cerchio ambrato + "C" serif su crema).
- `packaging/icon.iconset/` — PNG a 9 risoluzioni (16-1024 incluse @2x).
- `packaging/build.sh` — orchestrazione `pyinstaller` + `create-dmg` (con fallback `hdiutil`).
- `packaging/README.md` — istruzioni build + warning Gatekeeper + path dati utente.

File modificati:
- `cicerone/db/connection.py` — UNICA eccezione ai vincoli del round: aggiunto override via `os.environ["CICERONE_DB_PATH"]` per spostare il DB in una location scrivibile quando si gira dentro `.app`. In dev (senza env var) comportamento invariato.
- `pyproject.toml` + `uv.lock` — `uv add --group packaging pywebview pyinstaller`. Gruppo separato, NON nelle runtime deps.

### Cosa è stato fatto

- Scritto `desktop.py` che avvia streamlit in-process dentro un thread daemon e apre una finestra pywebview sul `127.0.0.1:PORTA`. Niente subprocess separato (vedi pitfall 1).
- Generata icona placeholder con Pillow → `iconset` con 9 PNG → `iconutil -c icns` per produrre `icon.icns`.
- Scritto `cicerone.spec` PyInstaller one-folder con `datas` per `app.py`, `Criteri_Readiness_Maturity.md`, metadata dei pacchetti che leggono `importlib.metadata`, e `hiddenimports = collect_submodules("cicerone")`.
- Scritto `build.sh` che fa `pyinstaller packaging/cicerone.spec`, poi tenta `create-dmg` con layout curato e in caso di assenza ricade su `hdiutil` con staging dir (copia `.app` + symlink `/Applications`).
- Scritto `packaging/README.md` con comandi build, prima apertura (Apri comunque per Gatekeeper), path DB utente.
- Build completata: `.app` 231 MB, `.dmg` 102 MB.

### Pitfall colpiti e fix

1. **Fork bomb del subprocess** — il primo `desktop.py` lanciava `sys.executable -m streamlit run`. Dentro il bundle PyInstaller `sys.executable` punta a `.../Contents/MacOS/cicerone` (il launcher), che rieseguiva il main → fork bomb (8+ processi figli). Fix: portato tutto in-process con `streamlit.web.bootstrap.run` in un thread daemon nello stesso processo del launcher.
2. **`signal only works in main thread`** — `bootstrap.run` registra handler con `signal.signal(SIGTERM, …)`, che funziona solo nel main thread. Fix: monkey-patch `signal.signal = lambda *a, **kw: None` dentro la funzione che gira nel thread runner. Effetto collaterale: streamlit non gestisce shutdown via signal, ma il thread è daemon e termina con il processo principale (pywebview) → accettabile.
3. **Streamlit binda 8501 ignorando la porta richiesta** — le env vars `STREAMLIT_SERVER_PORT` non bastano se chiamato via bootstrap. Fix: `bootstrap.load_config_options(flag_options={"server_port": porta, "server_address": "127.0.0.1", ...})` PRIMA di `bootstrap.run`. Attenzione: le chiavi sono in formato CLI (`server_port` con `_`, non `server.port` con `.`).
4. **`PackageNotFoundError: streamlit`** — `streamlit/version.py` chiama `importlib.metadata.version("streamlit")` all'import. Senza `.dist-info` dentro il bundle il pacchetto crasha subito. Fix: nello spec `datas += copy_metadata("streamlit")` e per traslazione anche per `anthropic`, `httpx`, `openpyxl`, `pypdf`, `python-docx`, `python-dotenv` (alcuni leggono la propria versione nello stesso modo).
5. **`ImportError: cannot import name 'seed' from 'cicerone.db'`** — `app.py` è trasportata come `data` (perché lanciata via `streamlit run` interno), quindi PyInstaller non analizza i suoi import (`cicerone.db.seed`, `.mcda`, `.llm`) e non li include. Fix: `hiddenimports += collect_submodules("cicerone")` nello spec per forzare l'inclusione di tutto il package.
6. **`FileNotFoundError: Criteri_Readiness_Maturity.md`** — `seed.py` risolve `ROOT/Criteri_Readiness_Maturity.md` dove `ROOT = Path(__file__).parent.parent.parent`, che nel bundle PyInstaller diventa `Contents/Frameworks/`. Fix: aggiunto `(ROOT/"Criteri_Readiness_Maturity.md", ".")` ai `datas` dello spec così il file finisce nel root atteso.
7. **`create-dmg` non installato** — il package Homebrew non era presente sulla macchina di build. Fix: fallback automatico in `build.sh` a `hdiutil create -volname Cicerone -srcfolder STAGING -ov -format UDZO`, con staging dir contenente `.app` + symlink `Applications`. Risultato funzionale ma layout meno curato (no sfondo, no posizioni icone).

### Verifica finale

- `dist/Cicerone.app` → 231 MB.
- `dist/Cicerone.dmg` → 102 MB (formato UDZO).
- Lancio diretto `Contents/MacOS/cicerone`: 1 solo processo (nessun fork), porta TCP bindata (verificata con `lsof -iTCP -sTCP:LISTEN`).
- `curl http://127.0.0.1:PORTA/` → 200, `/_stcore/health` → `ok`.
- DB scritto in `~/Library/Application Support/Cicerone/cicerone.sqlite` → 57 KB, seed completo (criteri caricati).
- Zero traceback nei log durante avvio e prima richiesta.

### Cosa resta aperto

- **Knowledge base privata**: lo spec include `knowledge/frameworks/*.md` se presenti localmente al momento del build (gitignored). Sulla macchina di build attuale `knowledge/` NON è clonato → il `.dmg` prodotto NON contiene la KB, e diagnostica/report falliranno a runtime quando cercano i file. Prima della release vera: clonare repo privato `cicerone-knowledge` in `knowledge/` e rifare la build.
- **NO code signing / notarization**: alla prima apertura compare il warning Gatekeeper. Documentato in `packaging/README.md` (Ctrl+click → Apri comunque). Per signing serve Apple Developer ID ($99/anno) — fuori scope di questo round.
- **Single-arch**: bundle è `arm64` (build fatta su Apple Silicon). Per universal2 servirebbe `target_arch="universal2"` nello spec + Python universal2 + ricompilazione di tutte le deps native (pyobjc & co.).
- **`create-dmg`**: layout `.dmg` attuale è minimal perché passato via `hdiutil`. Per layout curato: `brew install create-dmg`, rifare build → `build.sh` lo userà automaticamente (il ramo preferito è già scritto).
- **Test UI end-to-end nel bundle**: smoke test passa (HTTP 200, health ok, DB scritto e popolato). Flusso completo onboarding → intervista → vincitore → diagnostica → report richiede API key Anthropic + knowledge base → da validare con app reale dopo clone KB.
- **Release**: NON eseguita da Claude. L'utente farà la release ufficiale dopo aver pullato il branch.

---

## ROUND 6 — REFACTORING TOTALE & CLEANUP (2026-06-15, target Opus 4.7 xhigh)

> **Per il collaboratore:** `git pull` nel repo `cicerone`. Apri Claude Code
> con modello Opus 4.7 xhigh. Incolla TUTTO questo round come primo
> messaggio. Non ci sono limiti di contesto o budget per questa sessione:
> serve un lavoro **completo e autonomo**, non frammentato. Leggi prima
> tutto il piano R1→R7, poi esegui in ordine senza tornare a chiedere
> conferma su micro-decisioni. Comunica solo macro-decisioni (es. "lo
> split di app.py rompe la sessione Streamlit, conviene tenere monolite?")
> e fine sessione.

### Contesto round 6

Cicerone è funzionante end-to-end: web app Streamlit + bundle desktop
macOS con setup knowledge first-run. Ma in 9 round di lavoro si è
accumulato debito:

- file morti (mock fallback obsoleti, stub `main.py`)
- dipendenze inutilizzate (`python-docx`, `pypdf` non importate da nulla)
- `.DS_Store` committati
- 3 doc top-level che si sovrappongono (`CICERONE_CONTEXT.md`,
  `CICERONE_PLAN.md`, `CICERONE_PARALLEL_UI_TASK.md` = 110 KB di markdown)
- `cicerone/ui/app.py` monolitico (721 righe) con try/except fragili
- `cicerone/desktop.py` monolitico (441 righe) con HTML inline
- nessun lint config, nessun test, nessun CI

Obiettivo: codebase pulito, leggero, manutenibile. **Senza rompere
nulla.** Tutto deve continuare a funzionare: dev (`uv run streamlit
run`) e bundle (`bash packaging/build.sh`).

### Esplorazione preliminare (OBBLIGATORIA)

Prima di toccare codice, leggi e fai inventario:

```bash
# Struttura
find . -maxdepth 4 -type f ! -path "./.venv/*" ! -path "*/__pycache__/*" \
  ! -path "./.git/*" ! -path "./build/*" ! -path "./dist/*" \
  ! -path "./knowledge/pdfs/*" | sort

# Dimensioni
wc -l cicerone/**/*.py *.md packaging/*.{py,spec,sh,md}

# Dipendenze: chi importa cosa
grep -rn "^import\|^from" cicerone/ | grep -v "__pycache__"

# Diff dei doc top-level (overlap)
diff <(grep "^#" CICERONE_CONTEXT.md) <(grep "^#" CICERONE_PLAN.md)
```

Mappa mentalmente i confini. Solo dopo, procedi.

### Mappa stato (giugno 2026)

#### Repo `cicerone` (pubblico)

```
cicerone/
├── .streamlit/config.toml          # tema Streamlit
├── .env.example                    # template env (ANTHROPIC_API_KEY)
├── .gitignore
├── LICENSE
├── pyproject.toml                  # deps + script entry
├── uv.lock
├── README.md                       # entry-point doc
├── CICERONE_CONTEXT.md             # obsoleto in parte (vedi R4)
├── CICERONE_PLAN.md                # obsoleto in parte (vedi R4)
├── CICERONE_PARALLEL_UI_TASK.md    # questo file
├── Criteri_Readiness_Maturity.md   # consumato da seed (KEEP)
├── MatriceDB.xlsx                  # consumato da seed (KEEP)
├── cicerone/
│   ├── __init__.py
│   ├── main.py                     # STUB inutile (vedi R1)
│   ├── desktop.py                  # 441 righe, da splittare (R3)
│   ├── data/cicerone.sqlite        # dev DB, gitignored
│   ├── db/
│   │   ├── connection.py           # env var DB_PATH (KEEP)
│   │   ├── repository.py           # 232 righe (KEEP)
│   │   ├── schema.sql
│   │   └── seed.py
│   ├── llm/
│   │   ├── _client.py              # Anthropic wrapper (KEEP)
│   │   ├── intervista.py           # 156 righe (KEEP)
│   │   ├── diagnostica.py          # 239 righe (KEEP, env var KNOWLEDGE_DIR)
│   │   └── report.py               # 156 righe (KEEP)
│   ├── mcda/
│   │   └── calcolo.py              # 62 righe (KEEP)
│   └── ui/
│       ├── app.py                  # 721 righe, da splittare (R3)
│       ├── _mock.py                # 196 righe, FALLBACK MORTO (vedi R2)
│       └── style.css
└── packaging/
    ├── cicerone.spec               # PyInstaller (KEEP)
    ├── build.sh                    # build .app + .dmg (KEEP)
    ├── generate_icon.py            # script icona riproducibile (KEEP)
    ├── icon.icns                   # icona generata (KEEP)
    └── README.md                   # doc packaging (KEEP)
```

#### Repo `cicerone-knowledge` (privato, cloned in `knowledge/` gitignored)

```
cicerone-knowledge/
├── README.md
├── EXTRACTION_PROMPT.md            # system prompt per estrarre framework da PDF
├── _TEMPLATE.md                    # template framework markdown
├── frameworks/*.md                 # 11 framework (consumati da diagnostica/report)
└── pdfs/*.pdf                      # 11 paper originali (riferimento, NON runtime)
```

Il refactoring di questo round tocca **solo** `cicerone`. `cicerone-knowledge`
è già pulito.

### Inventario refactor

#### KEEP (zero modifiche)
- `cicerone/db/schema.sql`, `seed.py`, `connection.py`, `repository.py`
- `cicerone/llm/*` (logica già pulita)
- `cicerone/mcda/calcolo.py`
- `cicerone/ui/style.css`
- `Criteri_Readiness_Maturity.md`, `MatriceDB.xlsx`
- `packaging/cicerone.spec`, `build.sh`, `generate_icon.py`, `icon.icns`, `README.md`
- `pyproject.toml` build-system block

#### REMOVE (eliminazioni nette)
- `cicerone/main.py` — stub `print("Hello from cicerone!")`, mai chiamato da nulla di reale
- `cicerone/ui/_mock.py` — usato solo come fallback nei try/except in `app.py`. I moduli reali esistono e funzionano. Fallback morto.
- `.DS_Store` (×3): `.`, `cicerone/`, `knowledge/`. Aggiungi a `.gitignore` se non c'è già.
- `packaging/icon_preview.png` — già gitignored, ma se accidentalmente trackato rimuovi
- Dipendenze runtime inutilizzate da `pyproject.toml`:
  - `pypdf>=6.13.2` (mai importata in `cicerone/`)
  - `python-docx>=1.2.0` (mai importata in `cicerone/`)
  - `python-dotenv>=1.2.2` — usata SOLO in `_client.py` per dev convenience. Valutare: KEEP se vuoi continuare a leggere `.env` in dev. Default: **KEEP** (dev convenience).

Verifica prima di rimuovere ognuna:
```bash
grep -rn "pypdf\|from pypdf" cicerone/ packaging/ scripts/ 2>/dev/null
grep -rn "docx\|python-docx\|from docx" cicerone/ packaging/ 2>/dev/null
```
Se zero risultati → rimuovi senza esitare.

Dopo rimozione deps: `uv lock` per aggiornare lockfile. Aggiorna anche
`packaging/cicerone.spec`: rimuovi le righe `copy_metadata("pypdf")` e
`copy_metadata("python-docx")` + l'hidden import corrispondente.

#### FIX (refactor in place)
- `cicerone/ui/app.py`:
  - Rimuovi `from cicerone.ui import _mock` e tutti i fallback `getattr(repo, "salva_contesto", _mock.salva_contesto)`. I moduli reali ci sono.
  - Rimuovi i try/except sugli import LLM (righe ~38-65). Ora gli import sono garantiti.
  - Vedi R3 per split opzionale.
- `cicerone/desktop.py`:
  - HTML inline (setup window + splash) → estrai in `cicerone/desktop/_html.py` con costanti `SETUP_HTML` e `SPLASH_HTML`.
  - Logica clone/copy → estrai in `cicerone/desktop/_knowledge_setup.py`.
  - Launcher core (porta, streamlit, webview) resta in `cicerone/desktop/__init__.py` (o `cicerone/desktop/launcher.py` con `__init__.py` che fa `from .launcher import main`).
- `pyproject.toml`:
  - Rimuovi `[project.scripts] cicerone = "cicerone.main:main"` se `main.py` viene cancellato. Oppure punta a un launcher CLI realistico (es. `cicerone = "cicerone.desktop:main"`).

### Phase R1 — Pulizia (30 min)

**Goal:** zero file morti, zero deps morte, gitignore in regola.

```bash
# 1. Rimuovi .DS_Store committati
find . -name ".DS_Store" -not -path "./.venv/*" -not -path "./.git/*" -delete
grep -q "^.DS_Store$" .gitignore || echo ".DS_Store" >> .gitignore

# 2. Verifica deps morte (output deve essere vuoto per pypdf/docx)
grep -rn "import pypdf\|from pypdf" cicerone/ packaging/
grep -rn "import docx\|from docx" cicerone/ packaging/

# 3. Rimuovi deps morte
# Modifica manuale pyproject.toml: togli pypdf, python-docx
uv lock
uv sync

# 4. Cancella main.py stub
git rm cicerone/main.py
# Aggiorna pyproject.toml: rimuovi [project.scripts] o aggiorna entry

# 5. Cancella _mock.py
git rm cicerone/ui/_mock.py
# Poi pulisci gli import in app.py (vedi R2)
```

**Verifica R1:**
- `uv sync` non fallisce
- `uv run streamlit run cicerone/ui/app.py` non rompe
- `git status` mostra solo le rimozioni intenzionali

### Phase R2 — Rimozione mock fallback (45 min)

**Goal:** `cicerone/ui/app.py` senza più try/except sugli import.

In `app.py`:

```python
# PRIMA (fragile)
try:
    from cicerone.mcda import calcolo as mcda
except ImportError:
    mcda = _mock

# DOPO (pulito)
from cicerone.mcda import calcolo as mcda
```

Lo stesso per `llm_intervista`, `llm_diag`, `llm_report`.

Rimuovi anche:
```python
salva_contesto = getattr(repo, "salva_contesto", _mock.salva_contesto)
storia_fn = getattr(repo, "storia_diagnostica", None) or getattr(_mock, "storia_diagnostica", lambda _: [])
```
→
```python
salva_contesto = repo.salva_contesto
storia_fn = repo.storia_diagnostica
```

Verifica che le funzioni esistano davvero in `repository.py`. Se mancano, aggiungile prima di rimuovere i fallback.

**Verifica R2:**
```bash
uv run python -c "from cicerone.ui import app; print(dir(app))" | grep -v "_mock"
# Nessuna menzione di _mock attesa
uv run streamlit run cicerone/ui/app.py
# Flow end-to-end: onboarding → intervista → vincitore → diagnostica → report
```

### Phase R3 — Split moduli (1.5h)

**Goal:** moduli sotto le 300 righe, responsabilità separate.

#### R3.1 — `cicerone/ui/app.py` (721 → ~250 + pages)

Streamlit gestisce single-file naturalmente. Lo split funziona se mantieni
`app.py` come orchestratore che chiama funzioni delle pagine. Struttura:

```
cicerone/ui/
├── app.py              # entry-point + state machine + sidebar (~250 righe)
├── style.css
└── pages/
    ├── __init__.py
    ├── onboarding.py   # pagina_onboarding (~140 righe)
    ├── intervista.py   # pagina_intervista (~150 righe)
    ├── vincitore.py    # pagina_vincitore (~100 righe)
    ├── diagnostica.py  # pagina_diagnostica (~120 righe)
    ├── report.py       # pagina_report (~80 righe)
    └── _shared.py      # helper UI: spinner_cicerone, vai_a, header (~80 righe)
```

`app.py` esempio:
```python
from cicerone.ui.pages.onboarding import pagina_onboarding
from cicerone.ui.pages.intervista import pagina_intervista
...

def main():
    init_state(); inject_style(); sidebar_navigation()
    step = st.session_state.step
    {
        "onboarding": pagina_onboarding,
        "intervista": pagina_intervista,
        ...
    }[step]()
```

**Attenzione:** lo `st.session_state` è globale, non passare nulla
esplicitamente; le pagine lo leggono direttamente. Gli helper condivisi
(`spinner_cicerone` ecc.) vivono in `_shared.py`.

**Test obbligatorio dopo split:** lancia `uv run streamlit run cicerone/ui/app.py`
e completa un assessment intero. Streamlit caching e session_state
possono rompersi se uno split è fatto male.

#### R3.2 — `cicerone/desktop.py` (441 → ~150 + helpers)

```
cicerone/desktop/
├── __init__.py             # re-export main
├── launcher.py             # main(), avvia streamlit, orchestratore (~150 righe)
├── setup_knowledge.py      # clone/copy logica + JS API (~120 righe)
├── _html.py                # SETUP_HTML, SPLASH_HTML costanti (~100 righe)
└── paths.py                # APP_SUPPORT, KNOWLEDGE_TARGET, _base_path (~40 righe)
```

`cicerone/desktop/__init__.py`:
```python
from cicerone.desktop.launcher import main
__all__ = ["main"]
```

**Verifica:** `uv run python -m cicerone.desktop` apre finestra come prima.
Poi `bash packaging/build.sh` deve continuare a buildare correttamente
(verifica che `packaging/cicerone.spec` punti a `cicerone/desktop/__init__.py`
o `cicerone/desktop/launcher.py` come entry).

#### R3.3 — `cicerone/llm/diagnostica.py` (239 righe) — OPZIONALE

Sotto le 300, accettabile così. Solo se la logica `_carica_framework_md`
+ `FRAMEWORK_MD` mapping cresce, valuta `cicerone/llm/_knowledge.py`
estratto. Per ora SKIP.

### Phase R4 — Consolidamento doc (1h)

**Goal:** un solo doc autorevole sul progetto, niente sovrapposizioni.

Stato attuale:
- `README.md` (8 KB) — overview, setup, getting started
- `CICERONE_CONTEXT.md` (25 KB) — contesto storico/dominio, parzialmente stale
- `CICERONE_PLAN.md` (29 KB) — piano fasi, fasi ormai chiuse
- `CICERONE_PARALLEL_UI_TASK.md` (58 KB) — task parallele round 1-6, diario
- `packaging/README.md` (5 KB) — build .dmg, KEEP separato

Azione:

1. **Estrarre da `CICERONE_CONTEXT.md` solo ciò che è ancora vero**
   (palette, regole architetturali, modello di dominio) → migrare in
   sezioni nuove del `README.md` principale OPPURE in `ARCHITECTURE.md` nuovo.
2. **Archiviare `CICERONE_PLAN.md` e `CICERONE_PARALLEL_UI_TASK.md`** in
   `docs/archive/` (cartella nuova). Storico utile, non più operativo.
   Aggiungi `docs/archive/README.md` che spiega cosa c'è dentro.
3. **Aggiornare `README.md`** con:
   - Cos'è Cicerone (1 paragrafo)
   - Stack (Python 3.11+, uv, Streamlit, Anthropic SDK)
   - Quickstart dev (`uv sync`, knowledge clone, `uv run streamlit run …`)
   - Quickstart desktop (link a `packaging/README.md`)
   - Struttura repo (alberato 1 livello)
   - Domini/glossario sintetico (criterio, peso, voto, assessment, framework)
   - Link a `ARCHITECTURE.md` se creato
4. **Nuovo `CHANGELOG.md`** (Keep a Changelog format) con sezioni
   `[0.1.0] - 2026-06-15 — prima release desktop` riassuntiva.

**Non eliminare i doc senza archiviarli.** `git mv` in `docs/archive/`,
non `git rm`.

### Phase R5 — Lint baseline (30 min)

**Goal:** ruff configurato, codebase passa.

`pyproject.toml`:
```toml
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM"]
ignore = ["E501"]
```

Esegui:
```bash
uv add --group dev ruff
uv run ruff check .
uv run ruff format --check .
```

Sistema gli errori (probabilmente import non usati post-cleanup R1/R2,
qualche f-string vuota, qualche `else` ridondante). NON applicare
`ruff format` su file mai toccati senza review (rischio churn enorme):
applica solo sui file effettivamente modificati in questo round.

### Phase R6 — Smoke test baseline (45 min)

**Goal:** test minimi che girano in <10s, per non riaprire bug già chiusi.

```
tests/
├── __init__.py
├── test_repository.py    # lista_criteri, lista_framework, salva_peso UPSERT
├── test_mcda.py          # classifica_framework con assessment fittizio
└── test_intervista_parse.py  # parse_risposta: ramo A vs B, is_retry
```

NO test di Streamlit UI (troppo flaky). NO test LLM end-to-end (costano).
Solo unit puri su DB, MCDA e parsing.

Setup:
```bash
uv add --group dev pytest
mkdir -p tests
```

Per `test_intervista_parse.py` usa monkeypatch sul client Anthropic con
risposte JSON canned.

Esegui:
```bash
uv run pytest -v
```

### Phase R7 — Finalizzazione (30 min)

**Goal:** branch pronto per merge + release v0.2.0.

1. **Branch:** lavora su `refactor/round-6` (NON main, lezione dal round 5).
2. **Commit granulari** per phase: `R1 cleanup`, `R2 rimozione mock`, ecc.
3. **Verifica finale completa:**
   ```bash
   uv sync
   uv run pytest -v
   uv run ruff check .
   uv run streamlit run cicerone/ui/app.py  # completa 1 assessment end-to-end
   bash packaging/build.sh                  # rebuild .dmg
   open dist/Cicerone.dmg                   # smoke test desktop
   ```
4. **PR description** (no merge automatico, lascia review utente):
   - Diff stats per phase
   - File rimossi
   - Test aggiunti
   - Verifica desktop bundle OK
5. **Tag e release**: NON da te. Utente farà `git tag v0.2.0` dopo merge.

### Vincoli round 6

- ❌ NIENTE nuove feature. Solo refactor, cleanup, doc, test.
- ❌ NIENTE modifiche a `schema.sql` o seed (DB stabile)
- ❌ NIENTE modifiche alla logica LLM (prompt invariati)
- ❌ NIENTE modifiche al flow UX (ordine pagine, sequenza intervista)
- ✅ PUOI cambiare moduli/file/cartelle (split, rename) PURCHÉ funzionalità invariata
- ✅ PUOI riscrivere doc (README, archivio)
- ✅ DEVI mantenere compatibilità: `uv run streamlit run` + `bash packaging/build.sh` devono funzionare a fine round

### Cosa comunicare a fine round

1. **Diff stats globali**: righe rimosse, righe aggiunte, file cancellati
2. **Lista deps rimosse**
3. **Lista doc archiviati**
4. **Risultati test (`pytest -v` summary)**
5. **Risultati lint (`ruff check` count)**
6. **Conferma smoke test desktop**: `.dmg` rebuild + apertura OK
7. **Eventuali decisioni macro prese in autonomia**
8. **Cosa rimane aperto**

### Tempo stimato totale

| Phase | Tempo | Cumulativo |
|-------|-------|------------|
| R1 Pulizia | 30 min | 0:30 |
| R2 Mock fallback | 45 min | 1:15 |
| R3 Split moduli | 1.5h | 2:45 |
| R4 Doc | 1h | 3:45 |
| R5 Lint | 30 min | 4:15 |
| R6 Test | 45 min | 5:00 |
| R7 Finalizzazione | 30 min | 5:30 |

**5-6 ore di lavoro mirato.** Opus 4.7 xhigh può chiuderlo in una
sessione singola se procede senza distrazioni.

### Escape hatches

- Se lo split di `app.py` introduce bug session_state difficili da
  diagnosticare in <30 min → **rollback dello split, lascia monolite,
  procedi con R4-R7.** Meglio refactor parziale che refactor rotto.
- Se ruff produce >50 errori dopo il fix → applica solo `--fix` automatico
  + format sui file modificati, NON push su tutto il codebase senza review.
- Se pytest scopre regressioni → STOP, segnala all'utente prima di fixare.

### Cosa NON è in questo round (rimandato a futuro)

- Code signing/notarization (`.dmg` firmato Apple Developer ID)
- CI/CD GitHub Actions
- Cross-platform (Windows/Linux bundle)
- Refresh knowledge via "aggiorna knowledge" in app (richiede keyring per PAT)
- Refactor schema DB
- Internazionalizzazione UI

Documenta queste come "Future work" in `CHANGELOG.md` o `ROADMAP.md` nuovo.

