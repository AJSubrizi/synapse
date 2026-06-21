# CLAUDE.md — Synapse bootstrap

Read and follow `~/AGENTS.md`.

The vault is an **LLM Wiki** (Karpathy's pattern): immutable `raw/` sources → an LLM-owned
wiki → a schema in `$BRAIN_VAULT/AGENTS.md`. Operations: ingest → query → lint.

Before any project action, query `$BRAIN_VAULT/index.md` and relevant vault notes per
`$BRAIN_VAULT/_meta/workflow.md` (Phase 0 or Phase 0-short).

After meaningful work, ingest external sources (`synapse ingest`) and distill reusable
knowledge back into the wiki. If you modified the vault, run `synapse lint` before closing.
