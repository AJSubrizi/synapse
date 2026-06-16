# Changelog

## Unreleased

## 0.2.0 — Synapse

- **Rename** project and GitHub repo to **Synapse** (formerly Agent Brain Runtime).
- **CLI** `synapse`; `brain` installed as symlink for compatibility.
- **Default home** `~/Synapse` (was `~/AI-Brain`); `SYNAPSE_HOME` env var.
- Shell-rc block marker `# >>> Synapse >>>` (strips legacy Agent Brain Runtime block).
- Workflow template: Phase 0-short, meaningful work, staleness, subagents, index >80 rule.
- Hook templates: `session-enforce.sh`, `stop-check.sh`.
- Docs: [CUSTOM-LAYOUT.md](docs/CUSTOM-LAYOUT.md) for monorepo / external skills (no bundled skill library).

## 0.1.1

- `validate.py` knowledge-rot warnings; `_meta/dedup.py`.

## 0.1.0

- Initial public starter kit as Agent Brain Runtime.
