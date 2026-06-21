# GEMINI.md — Synapse bootstrap

Read and follow `~/AGENTS.md`.

The vault is an **LLM Wiki** (Karpathy's pattern): immutable `raw/` sources → wiki → schema.
Operations: ingest → query → lint.

Before any project action, query the vault per `$BRAIN_VAULT/_meta/workflow.md`. After
meaningful work, ingest sources (`synapse ingest`) and distill into the wiki. Run
`synapse lint` if vault files changed.
