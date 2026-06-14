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

