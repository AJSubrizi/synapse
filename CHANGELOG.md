# Changelog

## Unreleased

- README: "Adding content" guide — manual drop into the right folder, then let the agent
  normalize frontmatter/tags/links/index and run `synapse check`; plus agent-driven ingestion
  of an external source (URL, Git repo, document) with provenance in `sources`.
- New starter skill `file-into-vault` — rated procedure for filing a draft or external source
  into the vault; installed alongside `distill-after-work`.

## 0.3.0

- **Multiple vaults**: `synapse vault <name>` switches to (or scaffolds) a named vault under
  `~/Synapse/vaults/<name>`; `synapse vault` lists them; `synapse vault default` returns to the
  default vault. Active vault tracked in `~/Synapse/.active-vault` and resolved dynamically.
- New vaults inherit the engine + workflow from the current vault with an empty knowledge surface.
- `reinit` no longer pins `BRAIN_VAULT` in the shell-rc block, so vault switches apply to the next
  `synapse <cli>` launch without reloading the shell. (Run `synapse reinit` once after upgrading.)
- README: vault visualization screenshot and a "what to put in a vault" guide (skills, security
  rules, legacy-codebase rules).

## 0.2.0 — Synapse

- **Rename** project and GitHub repo to **Synapse** (formerly Agent Brain Runtime).
- **CLI** `synapse`; `brain` installed as symlink for compatibility.
- **Default home** `~/Synapse` (was `~/AI-Brain`); `SYNAPSE_HOME` env var.
- Shell-rc block marker `# >>> Synapse >>>` (strips legacy Agent Brain Runtime block).
- Workflow template: Phase 0-short, meaningful work, staleness, subagents, index >80 rule.
- Hook templates: `session-enforce.sh`, `stop-check.sh`.
- Docs: [CUSTOM-LAYOUT.md](docs/CUSTOM-LAYOUT.md) for monorepo / external skills (no bundled skill library).
- **Consolidate** the active-session flag to a single `BRAIN_LOADED` (dropped the redundant `BRAIN_ACTIVE`); now surfaced in `synapse env`.
- **Align** the home directory variable across scripts: canonical `SYNAPSE_HOME`, internal `BRAIN_ROOT`, with `BRAIN_HOME` kept as a legacy fallback.

## 0.1.1

- `validate.py` knowledge-rot warnings; `_meta/dedup.py`.

## 0.1.0

- Initial public starter kit as Agent Brain Runtime.
