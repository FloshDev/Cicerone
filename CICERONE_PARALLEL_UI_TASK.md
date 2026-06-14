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
