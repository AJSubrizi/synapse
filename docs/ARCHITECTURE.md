# Architecture

Agent Brain Runtime has three layers.

## 1. Raw Sources

Projects, docs, conversations, logs, and external sources. These are not rewritten by
the brain. They are evidence.

## 2. Vault

The compiled knowledge base. Markdown files with frontmatter and `[[wikilinks]]`.
This is the long-term memory.

## 3. Runtime

Shell wrapper, global agent files, and workflow rules that make agents load the vault.

```text
project -> agent -> brain shim -> vault notes -> work -> distilled notes
```

## Design Goals

- Portable: plain files and shell scripts.
- Agent-agnostic: works with any CLI that can read instructions or inherit env.
- Obsidian-compatible: no database required.
- Conservative: do not intercept normal developer commands.

