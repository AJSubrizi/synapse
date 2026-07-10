# GEMINI.md — Synapse bootstrap

Read and follow `~/AGENTS.md` when present.

The vault is an **LLM Wiki** (Karpathy's pattern): immutable `raw/` sources → an LLM-owned
wiki → a schema in `$BRAIN_VAULT/AGENTS.md`. Operations: ingest → query → lint.

## Continuous loop

**Before meaningful work:** skim `$SYNAPSE_BOOTSTRAP_PATH` if set; then
`synapse query "<topic>"` (or `synapse search`). Open `$BRAIN_VAULT/hot.md` and
top-ranked notes (`summary:` first). Reuse instead of re-deriving.

**After meaningful work:** search before create; `synapse file` / `synapse file update`
(near-dups refused unless `--force`); then `synapse lint --strict` until clean.

**Skip** Phase 0 / distillation for typos and purely executional tasks.

Schema + workflow: `$BRAIN_VAULT/AGENTS.md`, `$BRAIN_VAULT/_meta/workflow.md`.
