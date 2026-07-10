# Synapse continuous loop (OpenCode instructions)

Include this file from `opencode.json` (`instructions`) or rely on project `AGENTS.md`.

## Every non-trivial turn

1. Skim `$SYNAPSE_BOOTSTRAP_PATH` when present (session bootstrap).
2. `synapse query "<topic>"` (or `synapse search` if no index).
3. Read `summary:` on top hits; open full notes only when needed.
4. Reuse vault knowledge; cite `[[page-name]]`.

## After meaningful work

1. Search before create: `synapse search "<topic>"`.
2. `synapse file <category> <title>` or `synapse file update <stem>`
   (near-dups refused unless `--force`).
3. `synapse lint --strict` → fix → re-run until clean.

Vault: `$BRAIN_VAULT` (default `~/Synapse/vault`). Schema: `$BRAIN_VAULT/AGENTS.md`.
