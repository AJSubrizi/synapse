# Synapse — Persistent Memory for AI Coding Agents

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Shell](https://img.shields.io/badge/shell-bash%20%7C%20zsh-89e051.svg)](#install)
[![Obsidian compatible](https://img.shields.io/badge/Obsidian-compatible-7c3aed.svg)](https://obsidian.md)

> **Give your AI coding agents long-term memory.** Synapse is an open-source,
> shell-native knowledge base: agents **read an Obsidian-compatible vault before work**
> and **distill what they learn after** — plain Markdown, no database, no lock-in.

Synapse is a lightweight persistent-memory layer for agentic CLIs (Claude Code, Codex,
Gemini, OpenCode, Cursor Agent, and others). It ships a rated **skills library** pattern
(scorecards on Markdown procedures) and pairs well with [RTK](https://github.com/rtk-ai/rtk)
(short-term token savings).

## Contents

- [Install](#install)
- [Quick start](#quick-start)
- [How it works](#how-it-works)
- [Commands](#commands)
- [Skills library](#skills-library-rated)
- [Token cost](#token-cost)
- [Custom layouts](docs/CUSTOM-LAYOUT.md)
- [FAQ](#faq)

## Install

```bash
git clone https://github.com/AJSubrizi/synapse.git
cd synapse
./install.sh
```

Default paths:

```text
~/Synapse/vault          # Obsidian-compatible knowledge base
~/.local/bin/synapse     # CLI (brain -> synapse symlink)
```

Verify:

```bash
synapse doctor
synapse env
```

Point at an existing vault:

```bash
SYNAPSE_HOME="$HOME/My-Brain" BRAIN_VAULT="$HOME/My-Brain/vault" ./install.sh
```

## Quick start

```bash
synapse codex
synapse claude
synapse opencode
```

With shell integration (`synapse reinit`), aliases like `codex` route through Synapse.

## How it works

```text
read vault (Phase 0) -> work with context -> distill if meaningful -> synapse check
```

Exports include `SYNAPSE_HOME`, `BRAIN_VAULT`, `BRAIN_LOADED`, `BRAIN_SESSION_ID`,
`BRAIN_VAULT_HASH`, and Obsidian-compatible paths. Normal dev commands (`git`, `npm`) are
**not** intercepted — only agentic CLIs.

Workflow details: `vault/_meta/workflow.md` (Phase 0, Phase 0-short, meaningful work,
staleness, subagents).

## Commands

```bash
synapse status       # active? vault, session, staleness
synapse check        # validate + dedup (read-only)
synapse doctor       # boot files exist?
synapse skill list   # ranked skills library
synapse reinit       # rewrite shell-rc Synapse block
synapse env
synapse <cli>        # run agent with vault env
```

`brain` remains a symlink to `synapse` for backward compatibility.

## Skills library (rated)

Starter vault includes one example skill (`distill-after-work`). Add your own under
`vault/skills/` or use a [custom layout](docs/CUSTOM-LAYOUT.md) for monorepo skill dirs.

```bash
synapse skill use   distill-after-work
synapse skill rate  distill-after-work 5 "saved a re-derive"
```

## Token cost

On a ~56-page vault, a typical Synapse-aware session is **~5k–7k tokens** (boot +
1–3 selective reads). Use `index → summary → body` and `synthesis/` hubs when the index
grows past ~80 entries.

## Claude Code hooks

Templates in `templates/vault/_meta/hooks/`:

- `session-enforce.sh` — inject bootstrap on SessionStart / SubagentStart
- `stop-check.sh` — `synapse check` only when `vault/` has git changes

## Uninstall

```bash
./uninstall.sh              # keeps ~/Synapse
./uninstall.sh --delete-vault # removes vault too
```

## FAQ

### What is Synapse?

Open-source persistent memory for AI coding agents: a portable vault + `synapse` shell shim.

### Former name?

This project was **Agent Brain Runtime** (`agent-brain-runtime`). Repo and product are now **Synapse**.

### Do I need Obsidian?

No. Markdown files only; Obsidian is optional for graph browsing.

## License

MIT — see [LICENSE](LICENSE).
