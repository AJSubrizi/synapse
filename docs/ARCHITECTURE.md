# Architecture

Synapse has three layers.

## 1. Raw Sources

Projects, docs, conversations, logs, and external sources. Evidence — not rewritten by the vault.

## 2. Vault

Compiled knowledge base: Markdown, frontmatter, `[[wikilinks]]`. Long-term memory.

## 3. Runtime

`synapse` shim, global agent files, workflow rules that make agents load the vault.

```text
project -> agent -> synapse -> vault notes -> work -> distilled notes
```

## Design Goals

- Portable: plain files and shell scripts.
- Agent-agnostic.
- Obsidian-compatible.
- Conservative: do not intercept normal developer commands.
