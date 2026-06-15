# Agent Brain Runtime — Persistent Memory for AI Coding Agents

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Shell](https://img.shields.io/badge/shell-bash%20%7C%20zsh-89e051.svg)](#install)
[![Obsidian compatible](https://img.shields.io/badge/Obsidian-compatible-7c3aed.svg)](https://obsidian.md)
[![Works with Claude · Codex · Gemini · OpenCode](https://img.shields.io/badge/works%20with-Claude%20·%20Codex%20·%20Gemini%20·%20OpenCode-2563eb.svg)](#supported-agents)

> **Give your AI coding agents long-term memory.** Agent Brain Runtime is an
> open-source, shell-native knowledge base that lets Claude Code, Codex, Gemini CLI,
> OpenCode, Cursor Agent, and any agentic CLI **read project context before work and
> save what they learn after** — using a portable, Obsidian-compatible Markdown vault.

**Agent Brain Runtime** is a lightweight persistent-memory layer for AI coding agents.
Instead of starting every session from zero, your agents load a shared **Obsidian vault**
(plain Markdown + `[[wikilinks]]`) as long-term memory, then distill reusable knowledge
back into it after meaningful work. No database, no cloud service, no lock-in — just
portable files and shell scripts.

It pairs especially well with [RTK](https://github.com/rtk-ai/rtk): RTK compresses
command output to save tokens in the short term; Agent Brain Runtime preserves
project knowledge across sessions for the long term.

## Contents

- [Why persistent memory for AI agents?](#why)
- [Supported agents](#supported-agents)
- [Create your Obsidian vault](#first-create-your-obsidian-vault)
- [Install](#install)
- [Quick start](#quick-start)
- [How it works](#how-it-works)
- [FAQ](#faq)

## Supported Agents

Agent Brain Runtime is **agent-agnostic**. It works with any AI coding CLI that can read
instructions or inherit environment variables, including:

- **Claude Code** (Anthropic)
- **Codex** (OpenAI)
- **Gemini CLI** (Google)
- **OpenCode**
- **Cursor Agent**
- any other agentic CLI or AI coding assistant on your machine

## First: Create Your Obsidian Vault

Agent Brain Runtime needs a vault first. The vault is the brain: a folder of Markdown
files that Obsidian can open as a graph and that AI agents can read/write as long-term
memory.

You have two options.

### Option A — Let the Installer Create One

By default, the installer creates:

```text
~/AI-Brain/vault
```

Open Obsidian, choose **Open folder as vault**, and select:

```text
~/AI-Brain/vault
```

This gives you a ready-to-use starter vault with:

- `index.md` — catalog of knowledge pages.
- `hot.md` — recent activity snapshot.
- `log.md` — append-only operation log.
- `_meta/workflow.md` — the read-before/write-after protocol.
- `_meta/validate.py` — quality gate for links and frontmatter.
- `_meta/dedup.py` — deterministic near-duplicate detector.
- folders like `concepts/`, `references/`, `projects/`, `synthesis/`, `entities/`.

### Option B — Use an Existing Vault

If you already have an Obsidian vault, point the installer to it:

```bash
BRAIN_HOME="$HOME/My-Brain" BRAIN_VAULT="$HOME/My-Brain/vault" ./install.sh
```

Your vault should contain at least:

```text
vault/
  AGENTS.md
  index.md
  hot.md
  log.md
  _meta/
    workflow.md
    taxonomy.md
    validate.py
    dedup.py
```

The important rule is simple: **the vault is the source of truth**. Agents should read
it before acting and distill reusable knowledge back into it after meaningful work.

## Why

Most AI coding sessions start from zero. The agent re-reads files, rediscovers
patterns, forgets decisions, and loses useful lessons when the thread ends.

Agent Brain Runtime makes the loop explicit:

```text
read vault -> work with context -> distill lessons -> grow the graph
```

Your Obsidian vault becomes the long-term memory. Agent CLIs remain temporary workers.

## Install

```bash
git clone https://github.com/AJSubrizi/agent-brain-runtime.git
cd agent-brain-runtime
./install.sh
```

Then open a new terminal and verify:

```bash
brain doctor
brain env
```

## Quick Start

```bash
# Start an agent through the brain shim
brain codex
brain opencode

# If shell integration is enabled, these pass through the brain automatically
codex
opencode
```

The installer creates:

- `~/.local/bin/brain` — wrapper for agentic CLIs.
- `~/AGENTS.md` — global bootstrap for agents that read AGENTS.md.
- `~/CLAUDE.md` and `~/GEMINI.md` — global bridges for those tools.
- `~/AI-Brain/vault` — default Obsidian-compatible vault.
- optional shell aliases/wrappers for known agent CLIs.

To install real command wrappers for GUI/PATH coverage:

```bash
INSTALL_AGENT_WRAPPERS=1 ./install.sh
```

Or wrap one command manually:

```bash
scripts/install-agent-wrapper.sh codex /path/to/real/codex
scripts/install-agent-wrapper.sh opencode /opt/homebrew/bin/opencode
```

## How It Works

```text
Without Agent Brain Runtime:

  Agent -> project files -> answer

With Agent Brain Runtime:

  Agent -> AGENTS.md -> vault/index.md + relevant notes -> project files -> answer
                                                        |
                                                        v
                                           distilled notes after work
```

The wrapper exports:

- `BRAIN_ROOT`
- `BRAIN_VAULT`
- `BRAIN_BOOT`
- `BRAIN_WORKFLOW`
- `OBSIDIAN_VAULT_PATH`
- `OBSIDIAN_WIKI_REPO`
- `OBSIDIAN_LINK_FORMAT`

It does not intercept normal developer commands like `git`, `npm`, or `python`.
Only agentic CLIs should run through the brain.

## Recommended With RTK

Use RTK for compact shell output:

Follow the install instructions at the [RTK repository](https://github.com/rtk-ai/rtk).

Recommended agent instruction:

```text
Use rtk before shell commands when possible.
Use the brain before planning, editing, or creating project output.
```

RTK saves tokens in the short-term context. Agent Brain Runtime preserves knowledge
across sessions.

## Commands

```bash
brain doctor       # verify files and vault
brain env          # print brain environment
brain codex        # run Codex with brain env
brain opencode     # run OpenCode with brain env
```

## Vault Structure

```text
vault/
  AGENTS.md
  index.md
  hot.md
  log.md
  _meta/
    workflow.md
    taxonomy.md
    validate.py
    dedup.py
  concepts/
  references/
  synthesis/
  skills/
  projects/
  entities/
  journal/
```

## Daily Workflow

1. Start your agent from a project folder.
2. The agent reads global/project `AGENTS.md`.
3. It checks `vault/index.md`, then opens the relevant notes.
4. It works normally.
5. At the end, it distills reusable knowledge into atomic notes.
6. It runs `python3 "$BRAIN_VAULT/_meta/validate.py"`.
7. Periodically, it runs `python3 "$BRAIN_VAULT/_meta/dedup.py"` to surface
   near-duplicate notes, then merges or cross-links the flagged pairs.

## GUI Coverage

Terminal aliases cover interactive shells. Wrapper binaries in `~/.local/bin` can
also cover GUIs that resolve commands from `PATH`.

GUIs that launch absolute embedded binary paths may bypass the shim. In that case,
configure the GUI command path to point to `~/.local/bin/<tool>` or use `brain <tool>`.

## Uninstall

```bash
./uninstall.sh
```

The uninstaller removes the shim and global boot files. It does not delete your vault
unless you pass `--delete-vault`.

## FAQ

### What is Agent Brain Runtime?

Agent Brain Runtime is an open-source persistent-memory layer for AI coding agents. It
gives CLIs like Claude Code, Codex, Gemini, and OpenCode a shared, Obsidian-compatible
Markdown knowledge base (a "vault") that they read before working and write to afterward,
so context and lessons survive across sessions.

### How do I give an AI coding agent long-term memory?

Point the agent at a persistent knowledge base it reads before acting and updates after.
Agent Brain Runtime does this with a portable shell shim (`brain`) plus an Obsidian vault:
run `./install.sh`, then launch your agent through the brain (`brain codex`, `brain claude`).

### Does it work with Claude Code, Codex, Gemini, and OpenCode?

Yes. It is agent-agnostic and works with any agentic CLI that can read instructions or
inherit environment variables. See [Supported agents](#supported-agents).

### Do I need Obsidian or a database?

No database and no cloud service are required. The vault is just Markdown files; Obsidian
is optional and only used to browse the knowledge graph visually.

### Is it free and open source?

Yes — MIT licensed. See the [LICENSE](LICENSE).

### How is this different from RAG or a vector database?

Agent Brain Runtime is intentionally simple: human-readable Markdown notes linked with
`[[wikilinks]]`, validated by a quality gate, with no embeddings or external services.
It complements heavier retrieval setups rather than replacing them.

## Status

This is a lightweight, shell-native starter kit for **AI agent memory**. It is
intentionally simple: Markdown, Obsidian links, portable shell scripts, and clear agent
instructions — easy to read, audit, and extend.

## Keywords

Persistent memory for AI coding agents · AI agent long-term memory · Claude Code memory ·
Codex / Gemini / OpenCode knowledge base · Obsidian vault for AI agents · agentic CLI
context · shared knowledge base for LLM agents.
