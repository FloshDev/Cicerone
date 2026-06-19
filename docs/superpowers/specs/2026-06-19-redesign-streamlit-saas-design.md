# Redesign UI Cicerone — direzione "tool SaaS moderno" (Streamlit)

**Data:** 2026-06-19
**Scope:** restyle dell'app Streamlit esistente (no cambio framework). Tocca
principalmente `cicerone/ui/style.css`, `cicerone/ui/app.py` (sidebar) e i micro-render
delle pagine in `cicerone/ui/_pages/*.py`. Backend, stato, logica delle fasi: **intatti**.

---

## 1. Obiettivo e diagnosi

L'app oggi sembra "Streamlit di default con un logo serif sopra". Problemi concreti
osservati nello screenshot dell'onboarding:

1. **Doppia personalità tipografica** — wordmark serif elegante (Cormorant) contro
   titoli di sezione neri sans pesanti. Due identità in conflitto.
2. **Gerarchia debole nel corpo** — input grigi piatti, nessun raggruppamento, divisore
   decorativo `─── · ───` che galleggia nello spazio morto tra "Configurazione" e "Profilo".
3. **Nessun senso di wizard** — l'area principale non comunica "passo X di 5 / cosa viene
   dopo". Tutta la navigazione è scaricata sulla sidebar.
4. **Controlli datati** — bottone oro piatto, select generiche.
5. **Sidebar sbilanciata** — logo enorme, molto spazio verticale vuoto, nav sottile.

## 2. Direzione approvata

**Tool SaaS moderno** (riferimento Linear / Stripe), deciso con l'utente:

- Sans-serif uniforme per tutto il corpo e i titoli di sezione.
- **Il serif Cormorant resta SOLO come wordmark del logo** in sidebar. Mai nei titoli di sezione.
- **Oro `#E8B84B` ridotto ad accento funzionale**: bottone primario, step attivo, focus ring
  degli input, punteggi/contributi MCDA, barra di progresso. Mai oro decorativo (via i divisori
  `─── · ───`, la riga oro sotto il wordmark grande, ecc.).
- Densità medio-alta, card nitide, input bianchi.

Palette invariata (dal design system): oro `#E8B84B`, oro scuro per testo su bianco
`#B8881F`, testo `#1F2329`, muted `#6b6b6b`, bordo `#e2dccd`/`#cfc9ba`, errore `#E85B4B`,
successo `#2ea043`. Tema base resta `light`.

## 3. Decisioni di layout (validate a mockup)

### 3.1 Shell — opzione A "sidebar ridisegnata"
Si tiene la sidebar a sinistra (cambio minimo, rischio basso) ma ripulita:

- Logo più piccolo + wordmark "Cicerone" serif + caption "AI Readiness" (sans, uppercase, muted).
- Badge stato chiave API come pill sobria.
- **Stepper a pallini numerati**: ogni fase è una riga `[n] Etichetta`. Il numero è un
  cerchietto: pieno oro col numero scuro se è la fase attiva, grigio (`#ece8dd`) se non attiva.
  Niente più numeri romani serif. Le regole di sblocco/back-nav restano quelle attuali
  (`fasi_raggiunte`, `disabled`).
- **La progress bar "Criterio X/N" si sposta in cima all'area contenuto**, non più solo in sidebar
  (vedi 3.4). In sidebar resta opzionale e discreta.

### 3.2 Contenuto — opzione C "compatta a due colonne"
Per le schermate con form (onboarding):

- Campi affiancati in due colonne via `st.columns` (dentro il `st.form` esistente), meno scroll,
  tutto su una schermata.
- **Input bianchi** (`#fff`) con bordo tenue e **focus ring oro** (`box-shadow 0 0 0 3px rgba(232,184,75,.18)`),
  al posto del riempimento grigio attuale.
- **Niente divisore decorativo** tra Configurazione e Profilo: i due blocchi diventano due
  `st.container(border=True)` (card) con micro-header sans bold.
- Titoli di sezione: sans bold ~15px, non `st.subheader` serif-ibrido.

### 3.3 Vincitore — opzione A "vincitore in evidenza + classifica con barre"
La schermata risultato (il momento "wow"):

- **Card hero per il #1**: bordo oro a sinistra (3–5px), label "Framework consigliato" (uppercase
  muted), nome nero grande, punteggio oro scuro grande, barra di punteggio piena, riga "perché"
  (motivazione breve dal modello / sintesi MCDA).
- **Classifica completa a righe**: cerchietto rank (oro pieno per il 1°), nome nero, barra di
  punteggio proporzionale, punteggio a destra. Riga cliccabile → aggiorna il breakdown.
- **Breakdown per criterio** come tabella sotto: colonne CRITERIO / VOTO / PESO / CONTRIB.,
  header con regola, contributo in oro scuro. Dati da `breakdown_per_criterio(assessment_id, framework_id)`.
- **Leggibilità**: nomi `#1F2329` pieni, punteggi `#B8881F`, righe alte ~40px. (Nota appresa coi
  mockup: forzare sempre il colore testo scuro, non affidarsi all'ereditato.)

### 3.4 Altre schermate — stesso sistema, per principio
- **Intervista** (chat): mantiene `st.chat_message`/`st.chat_input`. Aggiungi in cima la barra
  "Passo 2 di 5" + progress "Criterio i/N" e un header sezione sans. Bubble chat con bordo tenue
  uniforme (già quasi così). Il pannello "Livello inferito" usa i colori successo/warning della palette.
- **Diagnostica** (chat a catena): identico trattamento chat dell'intervista; barra "Passo 4 di 5".
- **Report** (markdown): header "Passo 5 di 5", `ft`/`st.markdown` del report in un container con
  larghezza di lettura comoda, bottone download primario oro. Tipografia del markdown leggibile
  (line-height ~1.5).

### 3.5 Header globale di pagina
Sostituire l'attuale `header_cicerone()` (wordmark serif gigante + tagline italico + riga oro)
nell'area principale con un **breadcrumb di wizard sobrio**: una riga `Passo X di 5 · <Nome fase>`
(label uppercase muted) + titolo fase sans bold + thin progress bar oro a larghezza piena.
Il wordmark serif vive ormai solo in sidebar.

## 4. Impatto sui file (mappa di implementazione)

- `cicerone/ui/style.css` — riscrittura mirata: input bianchi + focus ring; rimozione stili
  decorativi oro (`.cic-divider`, riga sotto `.cic-header`); nuovi stili `.cic-step` a pallino
  numerato; `.cic-card`/hero/track/rank/breakdown per il vincitore; stepper-top + progress.
  Drop `@import` Cormorant dai titoli di sezione (resta per `.cic-sidebar-title`).
- `cicerone/ui/app.py` — `sidebar_stepper()`: pallini numerati invece dei bottoni con `●`+romani;
  logo più piccolo; badge pill. Eventuale helper `wizard_header(fase)` per il breadcrumb in cima.
- `cicerone/ui/_pages/_shared.py` — `header_cicerone()` → `wizard_header(step)` (breadcrumb +
  progress); `divider_cicerone()` deprecato/rimosso dagli usi; helper card se utile.
- `cicerone/ui/_pages/onboarding.py` — due `st.container(border=True)` (Config, Profilo); campi in
  `st.columns`; via `divider_cicerone()`.
- `cicerone/ui/_pages/vincitore.py` — render hero + righe classifica + tabella breakdown (HTML via
  `st.markdown(unsafe_allow_html=True)` per le barre, come già fatto per le card).
- `cicerone/ui/_pages/intervista.py`, `diagnostica.py`, `report.py` — sostituire `header_cicerone()`
  con `wizard_header(...)`; nessuna modifica alla logica.

**Vincoli duri:** nessun cambio a backend (`db/`, `llm/`, `mcda/`), nessuna nuova dipendenza,
nessun cambio al contratto di stato `st.session_state`. Solo presentazione.

## 5. Criteri di successo

1. Identità tipografica coerente: serif solo nel wordmark sidebar, sans ovunque nel corpo.
2. Onboarding: due card, input bianchi con focus oro, due colonne, niente divisore galleggiante.
3. Ogni schermata mostra "Passo X di 5" + progress in cima al contenuto.
4. Vincitore: hero #1 + classifica con barre + breakdown, tutto pienamente leggibile.
5. Oro presente solo come accento funzionale.
6. Zero regressioni funzionali: le 5 fasi funzionano end-to-end come prima (stesso stato, stesso backend).

## 6. Fuori scope

- Migrazione a Flet (resta nel brief `flet_ui/`, progetto separato e futuro).
- Tema scuro.
- Nuove schermate o cambi di flusso.
- Modifiche a copy/contenuti oltre quelle necessarie agli header di wizard.
