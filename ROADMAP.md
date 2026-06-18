# Synapse — Roadmap

> Da una lista di consigli a un piano prioritizzato. Ogni voce è ancorata allo stato
> attuale del repo (CLI `synapse` con `vault/status/check/skill/doctor/...`, vault
> Markdown Obsidian-compatibile, `_meta/validate.py`, `_meta/skill.py`, niente DB).
>
> **Principio guida invariato:** il core resta file-based, plain Markdown, no lock-in.
> Tutto ciò che è qui sotto deve essere *opzionale* e non rompere un vault che gira
> con la sola intelligenza dell'agente + wikilinks.

## Priorità in sintesi

| # | Tema | Impatto | Sforzo | Rischio per la filosofia | Quando |
|---|------|---------|--------|--------------------------|--------|
| 1 | Retrieval più intelligente | Alto | Medio-Alto | Medio (va tenuto opzionale) | Ora |
| 2 | Distillation più robusta | Alto | Basso-Medio | Nessuno | Ora |
| 3 | Integrazioni `synapse setup <agent>` | Alto | Basso | Nessuno | Ora |
| 4 | Skills system (deps, versioning, auto-suggest) | Medio | Medio | Basso | Dopo 1–3 |
| 5 | Documentazione e demo | Alto (adozione) | Basso | Nessuno | In parallelo |
| 6 | Idee veloci (Git, layout, backend) | Variabile | Variabile | Variabile | Opportunistico |

L'ordine consigliato d'attacco: **2 → 3 → 5 → 1 → 4 → 6**. I consigli mettono il
retrieval al primo posto per *impatto*, ma distillation, integrazioni e demo hanno
sforzo molto più basso e sbloccano adozione subito; il retrieval semantico è il
lavoro più grosso e più rischioso per la filosofia "no DB", quindi va fatto bene e
non per primo.

---

## 1. Retrieval più intelligente

**Problema oggi.** Il recupero si appoggia all'intelligenza dell'agente + `[[wikilinks]]`
e a `index.md`/`hot.md`. Funziona finché il vault è piccolo o ben cross-linkato; degrada
quando cresce o quando un nodo non è linkato (`validate.py` già segnala gli orphan, segno
che il problema è reale).

**Obiettivo.** Un layer di ricerca *opzionale*, attivabile, che non introduce un database.

Fasi, dalla più sicura alla più impegnativa:

1. **`synapse search <query>` basato su ripgrep** (zero dipendenze nuove). Cerca su
   titoli, tag, `summary` di frontmatter e corpo; ordina per match nel frontmatter >
   corpo. È il 70% del valore con il 10% dello sforzo e resta 100% file-based.
2. **Indice di summary leggero.** Genera un singolo file (`_meta/index.tsv` o
   `_meta/digest.md`) con `stem · category · tags · summary` per dare all'agente una
   "mappa" compatta da leggere in Phase 0 invece dell'intero vault. Rigenerabile da
   `synapse check`/`reinit`.
3. **Embeddings locali opzionali in file** (`synapse index --embeddings`). Salvati come
   plain file (es. `_meta/embeddings.jsonl`), modello locale, attivazione esplicita.
   Mai richiesto per il funzionamento base. Documentare costo/benefici e come
   rigenerarli quando le note cambiano (legare a Git staleness — vedi §6).

**Note di design.** Tenere ogni livello dietro un flag/sottocomando; se Python o il
modello non ci sono, degradare a ripgrep senza errori. Aggiungere a `doctor` un check
sullo stato dell'indice.

**Definition of done.** `synapse search` funziona senza dipendenze extra; embeddings
puramente opt-in; un vault senza indice continua a funzionare identico a oggi.

---

## 2. Distillation più robusta

**Problema oggi.** La qualità della memoria dipende dai prompt/template di distillation
(`skills/distill-after-work.md`, `concepts/workflow.md`). Sono buoni ma minimali (4 step);
`validate.py` cattura errori strutturali ma non la qualità della distillazione.

**Azioni.**

1. **Template di distillation più strutturati.** Estendere `distill-after-work.md` con
   criteri espliciti: cosa è "atomico", quando creare vs aggiornare una nota, come
   scegliere category/tag dalla taxonomy, regole di cross-linking minimo. Aggiungere
   esempi positivi e negativi nel template (gli agenti seguono meglio con esempi).
2. **`synapse check` più severo (opzionale `--strict`).** Oltre agli orphan/broken link
   già presenti, aggiungere warning per: `summary` mancante o troppo lungo, note senza
   tag noti, note non in `index.md`, `updated` più vecchio di N mesi (staleness),
   duplicati semantici (estendere `_meta/dedup.py`).
3. **Loop di auto-correzione.** Documentare il pattern "distilla → `synapse check` →
   correggi i warning → ricontrolla" come parte del workflow, così l'agente chiude da
   solo i problemi che `check` segnala.

**Definition of done.** Un agente che segue il template aggiornato produce note che
passano `synapse check --strict` senza intervento umano nella maggioranza dei casi.

---

## 3. Integrazioni più facili — `synapse setup <agent>`

**Problema oggi.** Esistono template per `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` e hook
(`session-enforce.sh`, `stop-check.sh`), ma il wiring verso ogni agente è manuale.

**Azione.** Comando `synapse setup <target>` (claude-code | cursor | codex | gemini |
opencode) che installa il file di contesto giusto e gli hook nel posto giusto per quel
tool, in modo idempotente. È sforzo basso (i template ci sono già) e impatto alto
sull'adozione — è il "memanto connect" citato nei consigli.

**Passi.**
1. Censire, per ogni target, dove va il file di contesto e quali hook supporta.
2. `synapse setup <target>` copia/linka i template, sostituisce i path del vault attivo,
   ed è ri-eseguibile senza duplicare.
3. `synapse setup` senza argomenti elenca i target disponibili e quelli già configurati.
4. Aggiungere un check in `doctor` ("integrazione X configurata: sì/no").

**Definition of done.** Da clone a "agente che legge il vault" in un comando per i
target principali.

---

## 4. Skills system — dipendenze, versioning, auto-suggest

**Stato oggi (punto di forza).** `_meta/skill.py` implementa già le scorecard
(`uses/score/votes/last_used`), `skill use/rate/list/show`, e log in `_ratings.log`.
Buona base su cui costruire.

**Estensioni (in ordine).**
1. **Dipendenze tra skill.** Campo frontmatter `requires: [[...]]`; `skill show` mostra
   la catena; `check` segnala dipendenze rotte (riusa la logica wikilink di `validate.py`).
2. **Auto-suggest.** `synapse skill suggest <contesto/query>` propone la skill più
   rilevante per score/uses/tag — si appoggia naturalmente al retrieval del §1.
3. **Versioning delle skill.** Campo `version` nel frontmatter + changelog in coda alla
   skill; legare a Git (vedi §6) per individuare skill modificate/stale.

**Definition of done.** Le skill si possono comporre (deps), scoprire (suggest) ed
evolvere in modo tracciabile (version), senza database.

---

## 5. Documentazione e demo

**Problema oggi.** Il README è solido e c'è già lo screenshot del grafo Obsidian, ma
manca una demo end-to-end che mostri il loop "impara → scrive note".

**Azioni.**
1. **GIF/video di un workflow completo** (es. "Claude Code + Synapse impara e scrive
   note"), linkata in cima al README.
2. **Esempi concreti di distillation**: prima/dopo (input grezzo → note atomiche +
   wikilink + frontmatter) sotto `examples/`.
3. **Screenshot aggiuntivi del vault in Obsidian** per più scenari (skills library,
   regole di sicurezza, knowledge di progetto).
4. **Quickstart di 60 secondi** in testa al README che rimanda a `synapse setup`.

**Definition of done.** Un nuovo utente capisce il valore in <2 minuti senza installare.

---

## 6. Idee veloci (opportunistiche)

- **Git esplicito per versioning e staleness.** Usare la data dell'ultimo commit per
  derivare `updated`/staleness invece di affidarsi solo al frontmatter; `synapse check`
  può segnalare note non toccate da N mesi. Alimenta §1 (re-index) e §4 (skill stale).
- **Layout personalizzati.** Già supportati via `docs/CUSTOM-LAYOUT.md` — mantenere e
  testare con i nuovi comandi (`search`, `setup`) perché rispettino layout custom.
- **Backend avanzati opzionali** (es. Moorcheh o altro): consentirli *dietro
  interfaccia*, mantenendo il core file-based come default. Da valutare solo dopo che
  §1 ha definito un'astrazione di retrieval pulita; rischio di lock-in se anticipato.

---

## Cosa NON fare (per proteggere la filosofia)

- Nessun database richiesto nel percorso base.
- Nessuna dipendenza pesante obbligatoria: ripgrep/Python opzionali, degradazione
  pulita se assenti.
- Nessuna feature che renda un vault illeggibile come semplici file Markdown in Obsidian.
