# Architecture

Synapse implements [Andrej Karpathy's **LLM Wiki**](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f):
three layers and three operations, plus a runtime that wires agents to it.

## Three layers (Karpathy)

### 1. `raw/` — immutable sources

Projects, docs, conversations, logs, and external sources, captured under `raw/`. Evidence
the agent reads but **never edits** — superseded, not rewritten. Added by `synapse ingest`.

### 2. wiki — compiled knowledge

The LLM-owned Markdown knowledge base derived from `raw/` and from work: frontmatter,
`[[wikilinks]]`, navigation files (`index.md`, `log.md`, `hot.md`). Categories:
`concepts/` `people/` `organizations/` `techniques/` `sources/` `analysis/`, plus the
Synapse extensions `skills/` (rated) `projects/` `journal/`.

### 3. schema — `AGENTS.md`

Conventions, naming, frontmatter, and maintenance rules the agent follows to keep the wiki
coherent. The procedural memory of the system.

## Three operations

- **ingest** — `synapse ingest`: raw source in → summary + revised wiki pages out.
- **query** — `synapse query`: rank notes, synthesize, file good answers back as pages.
- **lint** — `synapse lint` (alias `check`): validate links, orphans, staleness, dedup.

## Runtime

`synapse` shim, global agent files, workflow rules that make agents load the vault.

```text
project -> agent -> synapse -> query wiki -> work -> ingest/distill -> lint
```

## Design Goals

- Portable: plain files and shell scripts.
- Agent-agnostic.
- Obsidian-compatible.
- Conservative: do not intercept normal developer commands.
