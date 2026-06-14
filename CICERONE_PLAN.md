# Piano Cicerone — Fase 1 Readiness

> Piano strutturale completo per realizzare il primo agente Cicerone (selezione framework Readiness + diagnostica + report).
> Diviso in due parti: **A) Guida tecnica per Flavio** (programmatore, primo progetto Python + SQL), **B) Report per colleghi gestionale** (cosa vedono utente e docente).

**Versione:** 1.0 — 2026-06-14
**Prerequisiti:** Python 3.11+, account Anthropic con API key, account GitHub.

---

# Parte A — Guida per il programmatore

Sequenza ordinata. Ogni fase ha: **obiettivo**, **cosa fare**, **perché**, **note Java→Python** (quando utile), **note SQL beginner** (quando utile), **risultato verificabile**.

Non saltare fasi. Ogni fase deve "girare" prima di passare alla successiva.

---

## Fase 0 — Setup ambiente

**Obiettivo:** avere un progetto Python pulito, riproducibile, versionato.

**Cosa fare:**

1. Installa `uv` (gestore progetto Python moderno):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. Nella cartella `Cicerone/`, inizializza:
   ```bash
   uv init --name cicerone --python 3.11
   ```
   Questo crea `pyproject.toml` (equivalente di `pom.xml` Maven o `build.gradle`).
3. Aggiungi dipendenze base:
   ```bash
   uv add streamlit anthropic python-dotenv pypdf openpyxl
   ```
4. Crea `.gitignore`:
   ```
   .venv/
   .env
   __pycache__/
   *.db
   .DS_Store
   ```
5. Crea `.env.example` (committato) e `.env` (NON committato):
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```
6. `git init`, primo commit.

**Perché:** `uv` gestisce virtualenv automaticamente. `.env` separa segreti dal codice (regola d'oro). `.env.example` mostra ai colleghi cosa devono compilare senza esporre la tua chiave.

**Java→Python:**
- `pyproject.toml` ≈ `pom.xml`
- `uv add X` ≈ aggiungere dipendenza Maven
- `uv run streamlit run ...` ≈ `mvn exec:java`
- Niente `public/private` espliciti, niente `class` obbligatoria a livello top.

**Risultato verificabile:** `uv run python -c "print('ok')"` stampa `ok`.

---

## Fase 1 — Struttura cartelle del progetto

**Obiettivo:** layout di cartelle ordinato che sopravviva alla crescita.

**Cosa fare:** crea questa struttura dentro `Cicerone/`:

```
cicerone/
├── __init__.py
├── main.py                  # entry point Streamlit
├── config.py                # carica .env, costanti globali
├── db/
│   ├── __init__.py
│   ├── schema.sql           # DDL: CREATE TABLE ...
│   ├── seed.py              # popola DB da Excel/Docx
│   ├── connection.py        # apertura connessione sqlite
│   └── repository.py        # funzioni CRUD ad alto livello
├── llm/
│   ├── __init__.py
│   ├── client.py            # wrapper Anthropic SDK
│   ├── prompts.py           # system prompt del consulente
│   └── tools.py             # definizione tool registra_voto
├── mcda/
│   ├── __init__.py
│   └── calcolo.py           # SUMPRODUCT, vincitore
├── ui/
│   ├── __init__.py
│   ├── pagina_onboarding.py
│   ├── pagina_intervista.py
│   ├── pagina_vincitore.py
│   ├── pagina_diagnostica.py
│   └── pagina_report.py
└── data/
    └── cicerone.db          # generato a runtime, gitignored
```

**Perché:** ogni modulo ha responsabilità chiara. Quando aggiungi Fase 2 (Implementation), aggiungi cartelle senza toccare il resto.

**Java→Python:**
- `__init__.py` (anche vuoto) dichiara una cartella come "package" (≈ `package` Java).
- Niente `class` obbligatoria: un modulo Python può essere solo funzioni.

**Risultato verificabile:** `tree cicerone/` mostra la struttura.

---

## Fase 2 — Schema database

**Obiettivo:** tabelle SQLite che reggono tutto il dominio Readiness.

**Cosa fare:** scrivi `cicerone/db/schema.sql`:

```sql
CREATE TABLE sheet (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE      -- 'readiness' | 'implementation'
);

CREATE TABLE criterio (
    id INTEGER PRIMARY KEY,
    sheet_id INTEGER NOT NULL,
    numero INTEGER NOT NULL,        -- 1..10
    nome TEXT NOT NULL,
    definizione TEXT NOT NULL,
    FOREIGN KEY (sheet_id) REFERENCES sheet(id),
    UNIQUE (sheet_id, numero)
);

CREATE TABLE framework (
    id INTEGER PRIMARY KEY,
    sheet_id INTEGER NOT NULL,
    nome TEXT NOT NULL,
    pdf_path TEXT,                  -- path al PDF in repo
    FOREIGN KEY (sheet_id) REFERENCES sheet(id)
);

CREATE TABLE voto (
    framework_id INTEGER NOT NULL,
    criterio_id INTEGER NOT NULL,
    voto REAL NOT NULL,             -- 0 / 2.5 / 5 / 7.5 / 10
    PRIMARY KEY (framework_id, criterio_id),
    FOREIGN KEY (framework_id) REFERENCES framework(id),
    FOREIGN KEY (criterio_id) REFERENCES criterio(id)
);

CREATE TABLE assessment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sheet_id INTEGER NOT NULL,
    contesto_azienda TEXT NOT NULL,  -- JSON con settore, dimensione, etc.
    framework_vincitore_id INTEGER,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sheet_id) REFERENCES sheet(id),
    FOREIGN KEY (framework_vincitore_id) REFERENCES framework(id)
);

CREATE TABLE peso_assessment (
    assessment_id INTEGER NOT NULL,
    criterio_id INTEGER NOT NULL,
    livello TEXT NOT NULL,           -- 'Fondamentale' | 'Importante' | 'Abbastanza importante' | 'Poco importante' | 'Non importante'
    peso REAL NOT NULL,              -- derivato dal livello via mapping fisso (10/7.5/5/2.5/0)
    motivazione TEXT,                -- estratta dal LLM
    trascrizione TEXT,               -- dialogo grezzo
    PRIMARY KEY (assessment_id, criterio_id),
    FOREIGN KEY (assessment_id) REFERENCES assessment(id),
    FOREIGN KEY (criterio_id) REFERENCES criterio(id)
);

CREATE TABLE diagnostica (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id INTEGER NOT NULL,
    criterio_id INTEGER,             -- nullable: diagnostica può essere libera
    domanda TEXT NOT NULL,
    risposta_utente TEXT NOT NULL,
    valutazione_llm TEXT,            -- gap rilevato, livello attuale
    FOREIGN KEY (assessment_id) REFERENCES assessment(id),
    FOREIGN KEY (criterio_id) REFERENCES criterio(id)
);
```

**Note SQL beginner:**
- `PRIMARY KEY` = identificativo unico di una riga. Se è `INTEGER PRIMARY KEY`, SQLite lo auto-incrementa.
- `FOREIGN KEY` = "questa colonna punta all'`id` di un'altra tabella". Garantisce integrità: non puoi inserire un `criterio` con `sheet_id=99` se quello sheet non esiste.
- `UNIQUE` = vieta duplicati. Esempio: `UNIQUE (sheet_id, numero)` significa "non possono esistere due criteri con stesso numero nello stesso sheet".
- `REAL` = numero decimale (in Java ≈ `double`). `TEXT` = stringa. `INTEGER` = intero.
- Nessuna colonna `created_at` automatica come in altri DB: si usa `DEFAULT CURRENT_TIMESTAMP`.

**Perché questo schema:**
- Una `assessment` = una sessione utente. Persistente: se Flavio chiude e riapre browser, può ripartire (Fase 8).
- `peso_assessment` salva sia il numero sia la motivazione LLM e il dialogo: serve a docente per audit.
- `diagnostica` è separata perché può crescere indipendentemente.

**Risultato verificabile:** dopo Fase 3, lanciando `sqlite3 cicerone/data/cicerone.db ".schema"` vedi tutte le tabelle.

---

## Fase 3 — Bootstrap del database (seed)

**Obiettivo:** al primo avvio l'app crea il DB e lo popola con criteri, framework, voti presi dai file Excel/Docx.

**Cosa fare:**

1. `cicerone/db/connection.py`:
   ```python
   import sqlite3
   from pathlib import Path

   DB_PATH = Path(__file__).parent.parent / "data" / "cicerone.db"

   def get_connection() -> sqlite3.Connection:
       DB_PATH.parent.mkdir(parents=True, exist_ok=True)
       conn = sqlite3.connect(DB_PATH)
       conn.execute("PRAGMA foreign_keys = ON")  # SQLite di default NON le applica
       conn.row_factory = sqlite3.Row             # ti permette di leggere col nome colonna
       return conn
   ```

2. `cicerone/db/seed.py`:
   - Apre **`MatriceDB.xlsx`** (template canonico, non il file Freschi) con `openpyxl`.
   - Estrae solo lo sheet `AI Readiness-Maturity`.
   - Estrae nomi criteri (col 2), nomi framework (riga 5, col 5+), voti framework×criterio (righe 6-15, col 5+).
   - **Ignora** le colonne "Livello di importanza" e "Importanza (peso)": sono vuote per design, vengono compilate runtime dall'assessment utente.
   - Apre `Criteri ReadinessMaturity.docx` con `python-docx` (aggiungi: `uv add python-docx`) per le definizioni.
   - Inserisce tutto nel DB **solo se le tabelle sono vuote** (idempotenza).

3. `cicerone/main.py` (skeleton):
   ```python
   from cicerone.db import seed
   seed.run_if_needed()
   # ... resto Streamlit
   ```

**Perché:** il docente e i colleghi devono poter clonare il repo e lanciare l'app senza ricostruire il DB manualmente. Idempotenza = lanciare il seed due volte non rompe nulla.

**Java→Python:**
- `sqlite3` è nella standard library: nessuna dipendenza esterna per il driver.
- `with conn:` (context manager) ≈ `try-with-resources` Java per chiudere connessioni.
- Pattern repository: invece di scrivere `conn.execute("SELECT ...")` sparso nei file UI, centralizza in `repository.py`.

**Note SQL beginner:**
- `PRAGMA foreign_keys = ON` — SQLite, di default, **non applica** le foreign key. Bisogna attivarle ogni connessione. Trabocchetto classico.
- Idempotenza: prima di inserire, fai `SELECT COUNT(*) FROM criterio`. Se > 0, skippa.

**Risultato verificabile:** lanci il seed, apri `cicerone.db` con un viewer (es. DB Browser for SQLite), vedi tutte le righe.

---

## Fase 4 — Layer repository

**Obiettivo:** funzioni Python ad alto livello che il resto del codice usa senza scrivere SQL.

**Cosa fare:** in `cicerone/db/repository.py`, scrivi funzioni tipo:

```python
def lista_criteri_readiness() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT c.id, c.numero, c.nome, c.definizione
            FROM criterio c
            JOIN sheet s ON c.sheet_id = s.id
            WHERE s.nome = 'readiness'
            ORDER BY c.numero
        """).fetchall()
        return [dict(r) for r in rows]

def crea_assessment(contesto_json: str, sheet_nome: str) -> int:
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO assessment (sheet_id, contesto_azienda)
            SELECT id, ? FROM sheet WHERE nome = ?
        """, (contesto_json, sheet_nome))
        conn.commit()
        return cur.lastrowid

def salva_peso(assessment_id: int, criterio_id: int, peso: float,
               motivazione: str, trascrizione: str) -> None:
    ...

def vincitore_readiness(assessment_id: int) -> dict:
    """SUMPRODUCT in SQL: somma peso*voto per ogni framework, ritorna massimo."""
    ...
```

**Perché:** isola il SQL in un solo file. Se domani migri a Postgres, modifichi solo `repository.py`.

**Note SQL beginner:**
- **Parametri**: usa SEMPRE `?` per i valori variabili, MAI concatenare stringhe (`f"WHERE x = {valore}"`). Sennò SQL injection. Stessa regola di `PreparedStatement` Java.
- **JOIN**: in SQL non hai i "navigatori di oggetto" tipo `criterio.getSheet()` di JPA. Devi unire le tabelle a mano con `JOIN ... ON`.
- **`fetchall()`** = tutti i risultati in lista. `fetchone()` = primo o `None`.

**Risultato verificabile:** in console: `python -c "from cicerone.db import repository; print(repository.lista_criteri_readiness())"` stampa 10 criteri.

---

## Fase 5 — Calcolo MCDA

**Obiettivo:** dato un assessment con pesi compilati, determinare il framework vincitore.

**Cosa fare:** `cicerone/mcda/calcolo.py`:

```python
def calcola_vincitore(assessment_id: int) -> dict:
    """
    Per ogni framework Readiness:
      punteggio = sum(peso_criterio_i * voto_framework_criterio_i)
    Ritorna il framework con punteggio massimo + classifica completa.
    """
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT f.id AS framework_id,
                   f.nome AS framework_nome,
                   SUM(p.peso * v.voto) AS punteggio
            FROM peso_assessment p
            JOIN voto v ON v.criterio_id = p.criterio_id
            JOIN framework f ON f.id = v.framework_id
            JOIN criterio c ON c.id = p.criterio_id
            JOIN sheet s ON s.id = c.sheet_id
            WHERE p.assessment_id = ? AND s.nome = 'readiness'
            GROUP BY f.id, f.nome
            ORDER BY punteggio DESC
        """, (assessment_id,)).fetchall()
        classifica = [dict(r) for r in rows]
        return {"vincitore": classifica[0], "classifica": classifica}
```

**Perché:** il calcolo MCDA è **deterministico**. Stessi pesi, stessi voti → stesso vincitore. Niente LLM qui: il docente deve poter verificare il numero con Excel alla mano.

**Note SQL beginner:**
- `GROUP BY` = aggrega righe. Senza, non puoi usare `SUM(...)`.
- `ORDER BY ... DESC` = ordina decrescente.
- Una sola query fa tutto: niente loop Python.

**Risultato verificabile:** crei un assessment a mano con pesi finti, lanci `calcola_vincitore`, confronti con Excel.

---

## Fase 6 — Integrazione Claude (LLM consulente)

**Obiettivo:** il cuore del progetto. L'agente intervista il manager in modo conversazionale, estrae pesi via tool use.

**Cosa fare:**

1. `cicerone/llm/client.py`:
   ```python
   import os
   from anthropic import Anthropic
   from dotenv import load_dotenv

   load_dotenv()
   _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

   MODEL = "claude-opus-4-7"  # quello buono per ragionamento

   def chiama_consulente(messages: list[dict], system: str, tools: list[dict]) -> dict:
       resp = _client.messages.create(
           model=MODEL,
           max_tokens=2048,
           system=system,
           tools=tools,
           messages=messages,
       )
       return resp
   ```

2. `cicerone/llm/prompts.py`:
   ```python
   SYSTEM_CONSULENTE = """Sei Cicerone, consulente AI per PMI italiane.
   Stai intervistando il manager dell'azienda {nome_azienda} (settore: {settore},
   dimensione: ~{dipendenti} dipendenti) per capire quanto sono importanti per loro
   10 criteri di valutazione di framework di AI Readiness.

   REGOLE:
   - Parla italiano naturale, da consulente. NIENTE gergo tecnico (no "MCDA",
     "scala 0-10", "voto", "peso").
   - Una domanda alla volta. Riformula i criteri nel linguaggio del manager.
   - Quando capisci l'importanza, chiama il tool registra_voto.
   - Se la risposta è ambigua, rilancia massimo 2 volte con parole-ancora naturali
     ("diresti che è importante o fondamentale per voi?").
   - Mantieni un tono caldo, professionale, mai paternalistico.

   I 10 criteri da coprire sono (NON elencarli all'utente, gestiscili tu):
   {lista_criteri_con_definizione}
   """
   ```

3. `cicerone/llm/tools.py`:
   ```python
   LIVELLI_IMPORTANZA = ["Fondamentale", "Importante",
                        "Abbastanza importante", "Poco importante", "Non importante"]

   MAPPA_LIVELLO_PESO = {
       "Fondamentale": 10.0,
       "Importante": 7.5,
       "Abbastanza importante": 5.0,
       "Poco importante": 2.5,
       "Non importante": 0.0,
   }

   TOOL_REGISTRA_VOTO = {
       "name": "registra_voto",
       "description": "Registra il livello di importanza che il manager dà a un criterio.",
       "input_schema": {
           "type": "object",
           "properties": {
               "criterio_numero": {"type": "integer", "minimum": 1, "maximum": 10},
               "livello_importanza": {"type": "string", "enum": LIVELLI_IMPORTANZA,
                   "description": "Etichetta scelta in base alla risposta del manager."},
               "motivazione": {"type": "string",
                   "description": "Perché hai scelto questo livello, citando la risposta del manager."},
               "ambiguo": {"type": "boolean",
                   "description": "True se hai dovuto rilanciare per disambiguare."}
           },
           "required": ["criterio_numero", "livello_importanza", "motivazione", "ambiguo"]
       }
   }
   ```
   **Pattern chiave:** Claude sceglie solo l'etichetta. Il backend traduce in peso numerico via `MAPPA_LIVELLO_PESO`. Niente numeri inventati, niente drift fra modello e MCDA.

4. Loop di conversazione (in `ui/pagina_intervista.py`):
   - Mantieni lista `messages` in `st.session_state`.
   - Ogni turno utente: appendi a `messages`, chiami LLM.
   - Se risposta contiene `tool_use` con `registra_voto`: salvi a DB via repository, rispondi al LLM con `tool_result`.
   - Continui finché tutti 10 criteri non hanno un peso registrato.

**Perché:**
- **Tool use** = molto più affidabile del parsing JSON nel testo. Claude garantisce schema rispettato.
- **System prompt parametrico** = lo stesso codice serve ogni azienda.
- **Loop a stato** = niente magia, niente framework di orchestrazione (LangChain & co.): è solo un while.

**Java→Python:**
- `_client` con underscore davanti = convenzione "privato modulo" (non c'è `private` reale).
- Dict come parametri keyword: `chiama_consulente(messages=..., system=..., tools=...)`.
- Niente DTO: i dict sono l'idioma Python.

**Risultato verificabile:** test manuale da Streamlit (Fase 7) — l'agente fa 10 domande, alla fine il DB ha 10 righe in `peso_assessment`.

---

## Fase 7 — UI Streamlit

**Obiettivo:** schermate che guidano l'utente passo passo.

**Cosa fare:**

`cicerone/main.py`:
```python
import streamlit as st
from cicerone.db import seed
from cicerone.ui import (
    pagina_onboarding,
    pagina_intervista,
    pagina_vincitore,
    pagina_diagnostica,
    pagina_report,
)

seed.run_if_needed()

st.set_page_config(page_title="Cicerone", page_icon=None, layout="centered")

# Stato persistente nella sessione browser
if "step" not in st.session_state:
    st.session_state.step = "onboarding"

step = st.session_state.step

if step == "onboarding":
    pagina_onboarding.render()
elif step == "intervista":
    pagina_intervista.render()
elif step == "vincitore":
    pagina_vincitore.render()
elif step == "diagnostica":
    pagina_diagnostica.render()
elif step == "report":
    pagina_report.render()
```

Ogni `pagina_X.render()` disegna una schermata e, quando l'utente preme un bottone "Avanti", aggiorna `st.session_state.step` e chiama `st.rerun()`.

**Contenuto delle pagine:**

| Pagina | Cosa mostra | Cosa salva |
|--------|-------------|------------|
| Onboarding | Form: nome azienda, settore, dipendenti, processi core, obiettivo AI | Crea riga in `assessment`, salva `contesto_azienda` JSON |
| Intervista | Chat con LLM consulente (st.chat_message + st.chat_input) | Riga in `peso_assessment` per ogni `tool_use` |
| Vincitore | Punteggio framework vincitore + classifica completa + spiegazione LLM ("perché ti consigliamo X") | Aggiorna `assessment.framework_vincitore_id` |
| Diagnostica | Domande estratte dal PDF del framework vincitore, chat-style | Righe in `diagnostica` |
| Report | Markdown finale generato dal LLM, con bottone Download (.md) | Persistito come file in `data/reports/` |

**Perché:** Streamlit fa il rerender da capo a ogni interazione. La logica deve vivere in `st.session_state`. Pensa a `session_state` come a una `HashMap` che sopravvive ai render.

**Risultato verificabile:** `uv run streamlit run cicerone/main.py` apre il browser, completi l'onboarding finto.

---

## Fase 8 — Estrazione linee guida dai PDF framework

**Obiettivo:** per la diagnostica, l'agente deve sapere cosa dice il framework Readiness vincitore.

**Strategia consigliata (semplice, Fase 1):**

1. All'avvio diagnostica, leggi il PDF del framework vincitore (`pypdf` → testo grezzo).
2. Passa il testo come **contesto nel system prompt** del LLM diagnostica:
   ```
   Sei il consulente Cicerone. Il framework Readiness scelto è X.
   Ecco il documento integrale del framework:
   ---
   {testo_pdf}
   ---
   Conduci una diagnostica chiedendo al manager quanto la sua azienda copre ogni
   dimensione descritta. Una domanda alla volta. Usa il tool registra_diagnostica.
   ```
3. Se il PDF supera la finestra di contesto (~200k token), tagli a pezzi (chunking) — ma per ora i framework sono brevi, evita complicazione.

**Strategia futura (Fase 2+):** retrieval (RAG) con embeddings. Non ora.

**Risultato verificabile:** la diagnostica produce domande pertinenti al framework, non generiche.

---

## Fase 9 — Generazione report finale

**Obiettivo:** markdown personalizzato che il manager può scaricare.

**Cosa fare:**

`cicerone/llm/prompts.py` aggiungi:
```python
SYSTEM_REPORT = """Sei Cicerone. Scrivi un report finale in markdown per il manager
di {nome_azienda}.

Struttura obbligatoria:
1. Sintesi esecutiva (5 righe max)
2. Profilo dell'azienda (da contesto onboarding)
3. Framework Readiness selezionato e perché (da pesi + classifica MCDA)
4. Diagnostica stato attuale (dalle risposte diagnostica)
5. Gap rispetto allo stato auspicato (dal framework)
6. Piano d'azione: 5-8 passi concreti, priorità, tempi indicativi
7. Prossimi passi consigliati

Tono: pratico, italiano professionale, niente buzzword. Cita numeri e fatti.
"""
```

Il report viene generato passando al LLM:
- Contesto azienda (JSON)
- Tutti i pesi con motivazioni
- Classifica framework + vincitore
- Tutte le righe di diagnostica

Salva il markdown in `data/reports/{assessment_id}.md` e offri download con `st.download_button`.

**Risultato verificabile:** report leggibile, coerente con quanto detto in intervista.

---

## Fase 10 — Demo guidata per docente

**Obiettivo:** il collega può fare una demo live senza che l'LLM diverga in modo imbarazzante.

**Opzioni:**

a) **Demo live**: il collega si finge manager. Rischio: l'LLM può fare risposte inattese. Mitigazione: prove ripetute.
b) **Modalità seed scriptata**: aggiungi una flag `?demo=true` in URL. Se attiva, le risposte utente sono pre-caricate da un file `demo/risposte_seed.json` e simulate. L'LLM gira lo stesso, ma con input controllato. Più sicuro.

**Consiglio:** implementa (b) come fallback, ma punta su (a) se le prove vanno bene.

---

## Fase 11 — README per i colleghi

**Obiettivo:** un collega clona, legge il README, installa, lancia.

**Contenuto minimo:**

```markdown
# Cicerone

Agente AI conversazionale per PMI: seleziona un framework di AI Readiness
adatto alla tua azienda, valuta lo stato attuale, produce piano d'azione.

## Requisiti
- Python 3.11+
- Account Anthropic con API key

## Setup
1. Installa `uv`: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. `uv sync`
3. `cp .env.example .env` e inserisci `ANTHROPIC_API_KEY`
4. `uv run streamlit run cicerone/main.py`
5. Apri http://localhost:8501

## Struttura
(diagramma cartelle)

## Fase 2 (futura)
Agente Implementation: stesso flusso ma su matrice diversa, ricezione contesto Readiness.
```

---

# Parte B — Report per i colleghi di gestionale

> Spiegazione non tecnica di cosa farà Cicerone, cosa vedrà l'utente, cosa otterrà il docente. Da consegnare ai colleghi che presentano il progetto.

## Cos'è Cicerone

Cicerone è un consulente AI conversazionale pensato per piccole e medie imprese italiane che vogliono adottare l'intelligenza artificiale ma non sanno da dove partire. Aiuta il manager a:

1. **Capire quale modello teorico di "AI Readiness" si adatta meglio alla sua azienda** scegliendo tra 11 framework accademici/industriali noti, attraverso una conversazione naturale.
2. **Valutare lo stato attuale** dell'azienda rispetto a quel framework.
3. **Ricevere un piano d'azione personalizzato** in formato leggibile, che indica passi concreti per arrivare allo stato auspicato dal framework.

Una **Fase 2** futura aggiungerà un secondo agente analogo, focalizzato sull'**implementazione operativa dell'AI** (matrice di 3 framework diversi, criteri reinterpretati): per ora questa parte è congelata, il materiale di ricerca resta nel repository.

## Cosa vedrà l'utente (manager PMI)

Il manager apre l'applicazione nel browser. Trova quattro passaggi guidati:

**1. Onboarding (1-2 minuti)**
Un form chiede: nome azienda, settore, numero dipendenti, processi aziendali principali, obiettivo che si vuole raggiungere con l'AI. Niente domande tecniche.

**2. Intervista con il consulente (15-25 minuti)**
Una chat. Cicerone fa domande naturali, una alla volta, parlando il linguaggio del settore del manager. Esempio: invece di chiedere "che importanza assegna al criterio 'Sensibilità al settore'?", chiede "Per voi conta che le linee guida siano tarate sul manifatturiero alimentare, o vi basta uno strumento generale?". Il manager risponde a parole sue. Cicerone, dietro le quinte, traduce queste risposte in pesi numerici.

**3. Risultato della selezione (immediato)**
Cicerone mostra il framework consigliato, la classifica completa degli 11 candidati con i punteggi, e una breve spiegazione del perché quel framework si adatta a quella PMI specifica.

**4. Diagnostica + report (10-15 minuti)**
Cicerone fa domande mirate sullo stato attuale dell'azienda, calibrate sul framework scelto. Alla fine genera un report in markdown scaricabile con: profilo azienda, framework scelto e motivazione, diagnosi dei punti deboli, piano d'azione in 5-8 passi pratici.

**Totale**: ~30-45 minuti per una sessione completa.

## Cosa vedrà il docente

Per dimostrare al docente che il sistema non è una "scatola nera" e che i numeri sono solidi:

- **Calcoli deterministici e verificabili.** La scelta del framework segue il metodo MCDA (Multi-Criteria Decision Analysis) classico: ogni framework è valutato come somma pesata `Σ(peso × voto)`. Stessi input → stesso output. Si può ricontrollare con Excel.
- **Voti dei framework pre-caricati e visibili.** Sono presi dal lavoro di ricerca esistente (`Matrice_Selezione_Freschi.xlsx`) e non vengono mai modificati dal LLM. La parte "soft" è solo come si estraggono i pesi dal dialogo.
- **Pesi tracciabili.** Per ogni peso, il sistema registra: il valore numerico, la motivazione testuale prodotta dal LLM, la trascrizione integrale del dialogo che lo ha generato. Audit completo.
- **Demo riproducibile.** È prevista una modalità "guidata" in cui le risposte simulate del manager sono pre-caricate, per garantire che la demo davanti al docente fili liscia.

## Differenze rispetto all'idea iniziale (e perché)

L'ipotesi originaria prevedeva due agenti distinti, uno per la Readiness e uno per l'Implementation, ciascuno con la sua matrice MCDA. La revisione di team ha portato a una scelta più solida:

- **Fase 1 ora**: un solo agente Readiness, che oltre a scegliere il framework conduce anche una diagnostica e produce il piano d'azione **basato sulle linee guida del framework scelto**. Più coerente con il modo in cui un consulente vero opera.
- **Fase 2 dopo**: secondo agente Implementation, struttura analoga ma criteri reinterpretati. Materiale già raccolto, sviluppo successivo.

## Tecnologie e perché

| Scelta | Perché |
|--------|--------|
| Python | Linguaggio standard per applicazioni AI, ecosistema completo per LLM e dati. |
| Streamlit | Permette di costruire interfacce web senza scrivere HTML/JavaScript: ideale per progetti dimostrativi rapidi. |
| SQLite | Database leggero, contenuto in un singolo file. Zero installazioni richieste ai colleghi. Migrazione a un DB server (PostgreSQL) prevista per evoluzione commerciale. |
| Claude (Anthropic) | Modello LLM più adatto a dialoghi consulenziali in italiano e a output strutturati (tool use). |
| Repository GitHub | Codice pubblico, riproducibile, ogni collega può eseguirlo localmente. |

## Cosa NON fa Cicerone (per gestire aspettative)

- Non si sostituisce a un consulente umano nella decisione finale.
- Non garantisce che il framework scelto sia "oggettivamente il migliore": è il più allineato alle priorità espresse dal manager durante l'intervista.
- Non analizza dati interni dell'azienda (database, ERP, codice sorgente).
- Non implementa soluzioni AI: produce un piano d'azione, non scrive il codice del sistema AI.

## Stato attuale del progetto

In sviluppo. Versione dimostrativa attesa entro [data da concordare]. Il codice sarà disponibile su repository GitHub pubblico al link [da assegnare].

---

# Sequenza temporale consigliata

Ordine in cui Flavio dovrebbe attaccare le fasi, con tempo indicativo (ipotizzando 1-2 ore/giorno):

| # | Fase | Tempo stimato |
|---|------|----------------|
| 1 | Setup ambiente + cartelle (Fase 0-1) | 1 sera |
| 2 | Schema DB + bootstrap seed (Fase 2-3) | 2-3 sere |
| 3 | Repository + calcolo MCDA con dati finti (Fase 4-5) | 2 sere |
| 4 | Integrazione Claude minima — test in console (Fase 6) | 2-3 sere |
| 5 | UI Streamlit onboarding + intervista (Fase 7) | 3-4 sere |
| 6 | Schermata vincitore + diagnostica con PDF (Fase 8) | 2-3 sere |
| 7 | Report markdown finale (Fase 9) | 2 sere |
| 8 | Demo + README (Fase 10-11) | 1-2 sere |
| **Totale** | | **~3-4 settimane** |

---

**Fine piano.** Tieni questo file vivo: aggiornalo se cambia qualcosa.
