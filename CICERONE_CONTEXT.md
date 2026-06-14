# Cicerone — Contesto Sessione

> File vivo: leggere all'inizio di ogni sessione, aggiornare alla fine.
> Riassume decisioni di design prese e stato corrente del brainstorming/sviluppo.

**Ultimo aggiornamento:** 2026-06-14 (aggiunto flusso distribuzione PDF/KB)

---

## Identità del progetto

**Nome:** Cicerone
**Tagline:** "La guida per la tua PMI nell'adozione dell'AI"
**Obiettivo (Fase 1 — focus attuale):** agente AI conversazionale Readiness che aiuta una PMI a:
1. Selezionare il framework di AI Readiness/Maturity più adatto (MCDA con pesi estratti via dialogo LLM)
2. Effettuare diagnostica sullo stato attuale rispetto alle linee guida del framework vincitore
3. Produrre report pratico in markdown: stato attuale → stato auspicato dal framework → passi per arrivarci

**Fase 2 (rinviata):** secondo agente Implementation, struttura analoga (MCDA + diagnostica + report) ma su:
- Matrice 3 framework Implementation (`AI IMPLEMENTATION/`)
- Criteri con stessi nomi ma **interpretazione semantica diversa** (vedi `Criteri Ai Implementation.docx`)
- Riceve come input lo stato Readiness già acquisito (no doppio onboarding)

Per ora Fase 2 congelata: materiale resta nel repo come riferimento futuro.

**Contesto:** progetto universitario di Flavio. Colleghi di ingegneria gestionale lo presenteranno al docente. Possibile evoluzione commerciale verso PMI reali.

**Caso applicativo di riferimento (esempio):** Freschi SA, PMI manifatturiera ~50-60 dipendenti.

---

## Decisioni di design confermate

### Stack tecnico

- **Linguaggio:** Python 3.11+ (Flavio impara Python via questo progetto)
- **UI:** Streamlit (browser, no HTML/JS, dev veloce)
- **DB:** SQLite per ora → Postgres futuro (multi-tenant). SQL al 95% portabile.
- **LLM:** Claude (Anthropic API)
- **Gestore progetto:** `uv` + `pyproject.toml`
- **Segreti:** `.env` (gitignored). API key per ogni utente.

### Repo GitHub pubblico

Setup target per colleghi e docente:
```
git clone <repo>
cd cicerone
uv sync
cp .env.example .env   # inserisci propria ANTHROPIC_API_KEY
streamlit run cicerone/main.py
```

Al primo avvio: bootstrap automatico DB (schema + seed criteri/framework/voti).

### Architettura conversazione — CONSULENTE LLM (Fase 1 Readiness)

| Step | Modalità | LLM coinvolto? |
|------|----------|----------------|
| Onboarding (dati azienda) | Form Streamlit (settore, dimensione, processi core, obiettivo) | No raccolta — sì come contesto per sessione successiva |
| Intervista pesi Readiness (10 criteri) | Dialogo libero in stile consulente, sessione LLM unica multi-criterio | **Sì** — estrazione pesi via tool use |
| Calcolo vincitore Readiness | SQL `SUMPRODUCT` equivalente sui pesi estratti × voti seed | No |
| Diagnostica vs framework vincitore | Domande su stato attuale rispetto a linee guida estratte dal PDF del framework | **Sì** |
| **Report finale markdown** | Stato attuale → stato auspicato → passi pratici | **Sì, pesante** — qui sta il valore |

**Architettura LLM-driven:** l'agente si comporta da consulente. Adatta linguaggio al settore/dimensione PMI, evita gergo tecnico AI/MCDA. Mappa interno (scala 0/2.5/5/7.5/10) **nascosto** all'utente. Quando l'estrazione del peso è ambigua, rilancia con parole-ancora ("importante", "abbastanza importante", "fondamentale") in modo naturale — max 2 rilanci per criterio.

**Tool use Claude:** ogni peso estratto via function call strutturata `registra_voto(criterio_id, voto, motivazione, ambiguo: bool)`. Trascrizione + motivazione salvate a DB → auditabilità per docente, riproducibilità per demo.

### Schema DB (alto livello)

- `sheet` — readiness | implementation (campo già previsto per Fase 2)
- `criterio` — numero, nome, definizione, sheet_id
- `framework` — nome, sheet_id
- `voto` — framework_id, criterio_id, voto (FISSI, da seed)
- `assessment` — sessione utente, contesto azienda, sheet_id, timestamp
- `peso_assessment` — pesi estratti via LLM per quella sessione, con motivazione + trascrizione

Fase 1 popola solo righe con `sheet=readiness`. Fase 2 (futura) aggiungerà `sheet=implementation`.

### Dominio (10 criteri × 2 sheet)

Criteri (nome identico, semantica diversa fra Readiness e Implementation):
1. Completezza dimensionale
2. Capacità di guidare l'azione
3. Adattabilità e usabilità per PMI
4. Sensibilità e adattamento al settore
5. Granularità e profondità di analisi
6. Facilità d'uso
7. Modularità applicativa dell'assessment
8. Orientamento al valore di business
9. Protezione dei dati e compliance (Privacy & Security)
10. Evidenza empirica e referenze di successo

Scale (uguali per pesi e voti): **0 / 2.5 / 5 / 7.5 / 10**.

**Pattern coppia "Livello di importanza" + "Importanza (peso)"** (fonte: `MatriceDB.xlsx`):
ogni colonna numerica ha una colonna gemella testuale. Etichetta umana ↔ valore fisso.
LLM e utente parlano **etichette**; DB salva entrambi; MCDA usa il peso.

Mapping etichette importanza (pesi):
- Fondamentale = 10
- Importante = 7.5
- Abbastanza importante = 5
- Poco importante = 2.5
- Non importante = 0

Mapping etichette copertura (voto framework):
- Completa + funzionalità aggiuntive = 10
- Copertura completa = 7.5
- Coperto in parte = 5
- Coperto in parte ma con problemi = 2.5
- Mancante = 0

Punteggio framework = Σ(peso_i × voto_i) per i = 1..10. Vincitore = max.

**Framework presenti nella matrice:**
- Readiness: 11 framework (vedi `Matrice_Selezione_Freschi.xlsx`, sheet "AI Readiness-Maturity") — **focus Fase 1**
- Implementation: 3 framework (sheet "AI Implementation") — **Fase 2, congelato**

### Distribuzione & copyright PDF framework (deciso 2026-06-14)

**Problema:** PDF dei framework Readiness/Implementation sono materiale protetto (copyright editori). Estrarli in qualsiasi formato leggibile (testo, JSON, SQLite) costituisce ridistribuzione. Repo pubblico non può contenere né i PDF né loro derivati testuali.

**Threat model:** estraneo che naviga GitHub pubblico, NON colleghi/docente (uso accademico privato).

**Soluzione a tre layer:**

| Layer | Contenuto | Visibilità |
|-------|-----------|------------|
| Repo pubblico `cicerone` | Solo codice tool + script ingest + `knowledge/README.md` segnaposto | Mondo |
| Repo privato `cicerone-knowledge` | KB SQLite pre-estratto (chunks markdown + metadati + pesi) | Flavio + docente + colleghi |
| Macchina Flavio | PDF originali in `~/Desktop/Coding/Cicerone-sources/` (fuori dal repo) | Solo Flavio |

**PDF mai distribuiti.** Restano solo sulla macchina di Flavio come sorgente di verità.

**Formato KB scelto:** SQLite con chunks markdown + metadati (framework, sezione, pagina, hash PDF sorgente, versione ingest). Non PDF, non JSON sciolto. Motivi: parsing fatto una sola volta da Flavio, output identico per tutti, AI-friendly, piccolo da distribuire, query strutturate, allineato a schema MatriceDB twin-column.

**Flusso manutenzione (Flavio):**
1. PDF in `~/Desktop/Coding/Cicerone-sources/` (mai dentro repo)
2. `uv run cicerone ingest --pdf-dir ...` → genera `knowledge/frameworks.sqlite`
3. Copia SQLite in checkout locale `cicerone-knowledge`
4. Commit + push repo privato

**Flusso setup (collega/docente):**
```
git clone https://github.com/FloshDev/cicerone.git
cd cicerone
uv sync
cp .env.example .env   # inserisce ANTHROPIC_API_KEY propria
git clone https://github.com/FloshDev/cicerone-knowledge.git knowledge
streamlit run cicerone/main.py
```

**Update KB (collega):** `cd knowledge && git pull`.

**Scelte chiave:**
- Repo privato **separato**, NON git submodule (zero friction, no PAT obbligatori al clone iniziale, docente non deve conoscere submodule)
- `knowledge/` nel repo pubblico gitignored tranne `README.md` segnaposto con istruzioni accesso
- Nessuna cifratura nel repo pubblico (cifratura + chiave in `.env` = comunque ridistribuzione, complessità inutile)
- KB versionato in git → storico, rollback, diff tra release
- Repo pubblico contiene solo codice originale di Flavio (no PDF, no testo estratto, no contenuto di terzi)

**Aspetto legale:**
- PDF mai online → zero ridistribuzione pubblica
- KB = derivata trasformata distribuita solo a soggetti autorizzati per uso accademico
- Disclaimer: verificare licenze singoli paper (IEEE/Springer/ACM spesso tollerano uso interno educational, ma da controllare caso per caso)

### Cosa NON è stato deciso ancora (Fase 1)

- Struttura concreta delle schermate Streamlit
- Chunking strategy ingest PDF (per pagina / per sezione / per token window) — da decidere quando si scrive `extract.py`
- Embedding semantico nel KB sì/no (per Phase 1 retrieval keyword/section può bastare; valutare `sqlite-vec` se serve dopo)
- System prompt + tool schema del "consulente" (gestione ambiguità, max rilanci, formato motivazione)
- Strategia prompt engineering per generazione report finale
- Gestione interruzione/ripresa sessione utente
- Export Excel finale come allegato (sì/no)
- Modalità demo guidata per docente (live con collega che simula PMI vs scripted con risposte seed)
- Politica multilingua (IT, EN, …) — futuro

---

## Stato del brainstorming

**Conversazioni completate:**
1. Chiarito ruolo agente: deterministico per calcoli MCDA + LLM per intervista pesi, diagnostica e report
2. Scelto Python al posto di Java
3. Scelto Streamlit al posto di CLI/TUI
4. Scelto SQLite (con piano migrazione Postgres futura)
5. Scelto nome: Cicerone
6. **Rivisto stile conversazione:** da ibrido rigido a **LLM-consulente** con tool use, mappa interna nascosta, rilanci ambiguità con parole-ancora
7. Definito profilo utente target: manager PMI generico
8. **Scope ristretto a Fase 1 (Readiness only).** Implementation rinviata a secondo agente Fase 2.
9. Diagnostica Implementation rimpiazzata da: diagnostica vs linee guida del framework Readiness vincitore + report pratico verso stato auspicato

**Tema aperto al prossimo turno:**
- **Flusso completo schermata-per-schermata** in Streamlit per Fase 1: onboarding → intervista pesi LLM → vincitore → diagnostica vs framework → report. Cosa vede utente, cosa salviamo a DB quando, cosa chiediamo a LLM quando.

---

## Stato sviluppo concreto

**Sessione 2026-06-14 — Fase 0 Setup ambiente, in corso:**

Fatto:
- `uv` installato (versione 0.11.2)
- `uv init --name cicerone --python 3.11` in `/Users/flosh/Desktop/Coding/Cicerone` → creati `pyproject.toml`, `main.py`, `README.md` (vuoto), `.python-version`
- `uv add streamlit anthropic python-dotenv pypdf openpyxl python-docx` → dipendenze installate, `.venv/` creato, `uv.lock` generato
- `.gitignore` scritto (ignora `.venv`, `.env`, `*.db`, `cicerone/data/`, OS junk, lockfile Excel)
- `.env.example` scritto (placeholder `ANTHROPIC_API_KEY=sk-ant-...`)

Da fare al prossimo avvio sessione:
1. `cp .env.example .env` + inserire vera API key Anthropic in `.env`
2. Step 6 — `git init` + primo commit (chore: bootstrap)
3. Step 7 — verifica `gh --version`, creazione repo GitHub pubblico `cicerone`, push
4. Step 8 — scrittura README minimo per colleghi (setup istruzioni)
5. Poi Fase 1 — struttura cartelle progetto (vedi `CICERONE_PLAN.md` Fase 1)

Trabocchetti incontrati (per non ripetere):
- `uv init` lanciato per errore da `~`, generato `pyproject.toml` in home → conflitto workspace "Two workspace members named cicerone". Risolto rimuovendo residui (`~/pyproject.toml`, `~/main.py`, `~/README.md`). Lezione: verificare sempre `pwd` prima di `uv init`.
- `cd X uv add ...` su una sola riga non funziona: shell interpreta tutto come argomenti di cd. Usare due comandi separati o `&&`.

Eliminato dal repo: `Matrice_Selezione_Freschi.xlsx` (era caso d'esempio compilato, ridondante rispetto a `MatriceDB.xlsx`). Materiale Fase 2 (sheet Implementation) verrà fornito dai colleghi quando partirà Fase 2.

---

## Come collaborare con Flavio

- Fase brainstorming: solo conversazione, no codice/JSON/schema. Un tema alla volta.
- Quando chiede opinioni: dare consigli motivati, non liste neutre.
- Background Java forte → ponti Java→Python aiutano a spiegare Python.
- Termini italiani ok in dominio e codice (criterio, peso, voto, assessment).
- Riassumere a fine turno cosa è stato deciso + anticipare prossimo tema.

---

## Riferimenti

- `MatriceDB.xlsx` — **template canonico per seed DB**: criteri + framework + voti seed Readiness. Colonne importanza/peso/punteggio vuote per design (compilate runtime da assessment utente). Sheet "AI Implementation" assente: verrà fornita dai colleghi quando partirà Fase 2.
- `Criteri ReadinessMaturity.docx` — definizioni criteri Readiness
- `Criteri Ai Implementation.docx` — definizioni criteri Implementation (riferimento Fase 2)
- `READINESS:MATURITY/` — 11 PDF framework Readiness
- `AI IMPLEMENTATION/` — 3 PDF framework Implementation (Fase 2)
