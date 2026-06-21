# AGENTS.md — Vault Operating Manual (the schema)

This vault is an **LLM Wiki** (Andrej Karpathy's pattern) and the long-term memory for
AI agents (Synapse). It has three layers and three operations.

## Three layers

1. **`raw/`** — immutable sources (articles, transcripts, papers, captured docs). Read,
   never edit. Supersede a source with a newer one rather than changing it in place.
2. **wiki** — the Markdown you own and maintain, derived from `raw/` and from work:
   `concepts/` · `people/` · `organizations/` · `techniques/` · `sources/` · `analysis/`
   plus Synapse extensions `skills/` · `projects/` · `journal/`.
3. **schema** — this file: conventions, naming, frontmatter, and the maintenance rules
   the agent follows so the wiki stays coherent.

Navigation: `index.md` (catalog), `log.md` (append-only history), `hot.md` (recent/active).

## Three operations

### Ingest (raw → wiki)
`synapse ingest <path-or-url>` records the source under `raw/`, then:
1. Read the raw source; note the takeaways.
2. Write a summary page under `sources/` that cites the raw file as provenance.
3. Revise affected `concepts/` `people/` `organizations/` `techniques/` `analysis/` pages
   (a single source often touches several).
4. Update `index.md` and append to `log.md`.
5. `synapse lint` → 0 errors.

### Query (ask the wiki)
1. Read `hot.md`, then `index.md` (if >80 entries, use an `analysis/` hub + `grep`).
2. `synapse query "<question>"` for ranked retrieval; read `summary:` before bodies.
3. Synthesize an answer and cite used pages as `[[page-name]]`.
4. If the answer is reusable, **file it back**: `synapse file <category> <title>` creates
   the page + index entry + log line; then fill the body (knowledge compounds).
5. Complete Phase 0 / 0-short from `_meta/workflow.md` before running any skill.

### Lint (health-check)
`synapse lint` (alias `synapse check`) runs validate + dedup + skill deps: broken links,
orphans, missing index entries, stale/contradictory claims, frontmatter gaps. Run it
before closing any session that modified the vault.

## Write recipe (distillation)

1. Atomic notes; full frontmatter; tags from `_meta/taxonomy.md`.
2. Cross-link; update `index.md`, `hot.md`, `log.md`.
3. `synapse lint` (or `python3 _meta/validate.py`) → 0 errors.
4. Distill only for **meaningful work** (see `_meta/workflow.md`).

## Runtime vs. skills

This vault is **runtime memory** (what you know). **Executable procedures live in skills**,
under `$BRAIN_SKILLS_DIR` (default `vault/skills/`). Resolve paths from env — do not
hardcode. For monorepo layouts see Synapse `docs/CUSTOM-LAYOUT.md` in the repository.

## Skill scorecards

```yaml
uses: 0
score: 0.0
votes: 0
last_used: '-'
```

`synapse skill use|rate|list|show` — `brain` symlink works too.
