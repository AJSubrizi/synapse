# Changelog

## Unreleased

- **Installer fixed** — `install.sh` was stale: it created the old category dirs and never
  copied the new engine files, so topping up an existing vault left it without
  `wiki.py` / `vault_config.py` / `metrics.py` / `categories` / `prompt-retrieve.sh`. It now
  scaffolds the LLM-Wiki layout (`raw/ sources/ concepts/ techniques/ projects/ skills/`)
  and copies every current engine file. Added `templates/vault/raw/README.md`.
- **`synapse metrics`** — loop instrumentation (`_meta/metrics.py`): page count + growth,
  ingest/file activity from `log.md`, retrieval index coverage, and a blunt stall signal
  (`⚠ no distillation in N days`). Makes the wiki's compounding *measurable*, not assumed.
  Stdlib-only, offline, read-only; `--json` for scripting. New `tests/test_metrics.py`.
- **Process hygiene** (`CONTRIBUTING.md`): branch-from-`main`, one PR per coherent change,
  don't merge early, tag releases, avoid force-pushing shared history. Test command aligned
  to CI (all `tests/test_*.py`).
- **Aligned to Karpathy's LLM Wiki** — Synapse now adopts the
  [LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
  as its baseline: three layers (immutable `raw/` sources → an LLM-owned wiki → the
  `AGENTS.md` schema) and three operations (**ingest → query → lint**).
  - New `raw/` layer + **`synapse ingest <file|url>`**: copies the source into `raw/`
    (immutable, with provenance) **and** deterministically creates the derived `sources/`
    page — full frontmatter, an `index.md` catalog entry, and a `log.md` line — so ingest
    is a real wiki mutation; the agent only fills the distilled body. (Engine: `_meta/wiki.py`.)
  - New **`synapse file <category> <title>`**: files knowledge back as a wiki page
    (frontmatter + index + log) — the compounding half of `query`, now a command not a memo.
  - New **`synapse lint`** (alias of `check`).
  - New **`synapse hooks install`**: safe, idempotent JSON merge that wires the
    continuous-loop hooks (SessionStart / UserPromptSubmit / Stop) into
    `~/.claude/settings.json` — backs up to `.bak`, preserves your other settings/hooks.
    Turns Phase-0's one-shot read into per-turn retrieval (fixes read-once drift).
  - Wiki categories realigned to Karpathy's: `concepts/`, `people/`, `organizations/`,
    `techniques/`, `sources/`, `analysis/`. Synapse extensions (`skills/` rated, `projects/`,
    `journal/`) are kept on top. (Replaces the previous `references/`, `synthesis/`, `entities/`.)
  - Schema/workflow/docs (`AGENTS.md`, `_meta/workflow.md`, README, ARCHITECTURE, bootstrap
    templates) rewritten around the three layers and operations.
  - **Configurable categories** fit to the coding-agent domain: a single source of truth
    (`_meta/vault_config.py`, overridable via the plain `_meta/categories` file) replaces the
    hardcoded list across validate/dedup/search/wiki. Core (always scaffolded):
    `concepts/ techniques/ projects/ skills/`; optional (created on demand):
    `sources/ analysis/ people/ organizations/ journal/`. `synapse vault <name>` now
    scaffolds only the core set + `raw/` + `sources/`.
  - **`techniques/` vs `skills/` clarified**: a *technique* is a described pattern you
    reference; a *skill* is an executed, **rated** procedure (`synapse skill use|rate`).
  - **`raw/` is pragmatic, not mandatory**: used when ingesting an external source;
    session-distilled knowledge goes straight to the wiki. Documented in schema + README.
  - **README** rewritten model-/tool-agnostic and concise (441 → ~120 lines) with a Mermaid
    loop diagram; emphasizes it works with any LLM and any agentic CLI.
- **Continuous integration loop (Claude Code hooks)** — turn Phase 0's one-shot vault read
  into an ongoing loop:
  - `prompt-retrieve.sh` (**UserPromptSubmit**): ranks the vault against every prompt and
    injects the top matching notes (instant lexical ranking, no model) so memory resurfaces
    each turn instead of only at session start.
  - `stop-check.sh` (**Stop**, rewritten): if notes changed, runs `synapse check` and blocks
    the stop on errors; if project files changed but no notes were written, gives a one-shot
    distill reminder. Guarded against loops; silence the nudge with `SYNAPSE_DISTILL_NUDGE=0`.
- **Faster, smaller embeddings index** — vectors are now stored in a compact binary sidecar
  (`_meta/retrieval.vec`, float32) and queried with a single vectorized matrix-vector product
  instead of re-parsing JSON floats and doing cosine in Python: ~140× faster per query and
  ~5× smaller on disk at a few thousand chunks. Backward-compatible with old inline indexes.

## v0.4.0 — 2026-06-19

Smarter retrieval (BM25 default + hybrid/embeddings), end-to-end answer benchmarks,
one-line install, and git-derived staleness.

- **One-line install**: `curl -fsSL .../scripts/get.sh | bash` clones (or updates) the
  repo and runs `install.sh` — honoring the same env overrides.
- **Reproducible demo** (`scripts/demo.sh`): runs the full learn → write → recall loop in
  a throwaway vault (nothing touched outside a temp dir); the basis for the README GIF and
  a CI end-to-end smoke.
- **Git-derived staleness** (`synapse check --git-staleness`): flags stale notes from
  git commit history (ground truth) instead of the self-reported `updated:` frontmatter,
  falling back cleanly to the frontmatter date when the vault isn't a git work tree.
- **Answer-accuracy track** (`run_longmemeval.py --track answer`): closes the loop the
  README promised — retrieve top-k units, have an LLM answer from them, and grade the
  answer with an LLM judge (default model `claude-opus-4-8`). Turns a retrieval number
  into a memory number. Offline `--answerer echo --judge exact` exercises the plumbing
  with no API key (and runs in CI).
- **Distillation-quality eval** (`benchmarks/distillation_eval.py`): the honest
  end-to-end number — distill raw sessions into notes, index them with the *shipped*
  BM25 retriever, then retrieve→answer→judge. Measures Synapse's real artifact (distilled
  notes), not raw chat turns.
- **Hybrid retrieval backend** (`synapse index --backend hybrid`): fuses BM25 and
  embeddings with reciprocal rank fusion to lift the harder query types (multi-session,
  temporal). Opt-in; degrades to BM25 if embeddings aren't available.
- **Chunked, incremental embeddings**: notes are embedded per overlapping chunk (each
  carrying the title/summary as context) instead of one diluted whole-note vector, and
  `synapse index` re-encodes only notes whose content hash changed — reusing the rest, so
  re-indexing a large vault is cheap. Reports `reused / encoded` counts.
- **BM25 is now the default retrieval backend** for `synapse index` / `synapse query` —
  the strongest offline ranker (~90% nDCG@10 on LongMemEval-S, vs ~84% for TF-IDF), so
  what ships matches the published benchmark. TF-IDF stays available via
  `synapse index --backend tfidf`; embeddings degrade to BM25 if the model is absent.
- **Unified `synapse search`** on the weighted, frontmatter-aware `_meta/search.py`
  retriever (with `--tag` / `--title` / `--exact` filters), replacing the older grep-based
  shell implementation. The benchmark harness now imports the retriever's canonical
  tokenizer, so scores describe exactly what users run.
- **CI** now runs the unit suite (incl. new retriever tests) and an offline retrieval
  benchmark smoke test on the bundled fixtures, guarding against quality regressions.
- **Retrieval (optional, file-based)**: `_meta/search.py` powers `synapse search`
  (lexical, ripgrep-aware), `synapse digest` (compact `_meta/digest.md` map), and
  `synapse index` / `synapse query` (BM25 by default; opt-in embeddings backend
  via `SYNAPSE_RETRIEVAL_BACKEND`, degrades cleanly). The vault still works with
  no index at all — every layer is optional and degrades.
- **`synapse setup <target>`**: one-command wiring for claude-code / codex / cursor /
  gemini / opencode — installs the matching context file pointed at the active vault,
  idempotently. Templates are stashed under `$SYNAPSE_HOME/templates` at install time.
- **Stricter quality gate**: `synapse check --strict` flags distillation-quality issues
  (over-long/empty summaries, stale `updated` dates) as errors for CI; `check` now also
  reports the skill dependency graph.
- **Skills system**: skills can declare `requires: [[...]]` dependencies and a `version`;
  new `synapse skill suggest <context>` recommends a skill by relevance + reputation, and
  `synapse skill deps` reports/validates the dependency graph.
- **Docs**: README quickstart now leads with `synapse setup`; new worked
  `examples/distillation/` (raw session → atomic, linked, validated notes).
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
