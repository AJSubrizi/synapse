# AGENTS.md — Vault Operating Manual

This vault is the long-term memory for AI agents (Synapse).

## Runtime vs. skills

This vault is **runtime memory** (what you know). **Executable procedures live in skills**,
under `$BRAIN_SKILLS_DIR` (default `vault/skills/`). Resolve paths from env — do not
hardcode. For monorepo layouts see Synapse `docs/CUSTOM-LAYOUT.md` in the repository.

## Read recipe (all task types)

Use **Phase 0** or **Phase 0-short** from `_meta/workflow.md`.

1. Read `hot.md`, then `index.md` (if >80 entries, use `synthesis/` hub + `grep` only).
2. Pick 1–3 pages; read `summary:` before bodies.
3. Cite used pages as `[[page-name]]`.
4. Before running any skill, complete Phase 0 or 0-short.

## Write recipe

1. Atomic notes; full frontmatter; tags from `_meta/taxonomy.md`.
2. Cross-link; update `index.md`, `hot.md`, `log.md`.
3. `synapse check` (or `python3 _meta/validate.py`) → 0 errors.
4. Distill only for **meaningful work** (see `_meta/workflow.md`).

## Skill scorecards

```yaml
uses: 0
score: 0.0
votes: 0
last_used: '-'
```

`synapse skill use|rate|list|show` — `brain` symlink works too.

## Categories

`concepts/` · `references/` · `synthesis/` · `skills/` · `projects/` · `entities/` · `journal/`
