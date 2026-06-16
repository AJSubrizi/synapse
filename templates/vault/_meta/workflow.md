# Workflow

Read the vault before work. Distill into the vault after **meaningful work**.

## Phase 0 — Before work (required)

Choose **Phase 0** (default) or **Phase 0-short** for trivial tasks.

### Phase 0 (full)

1. `synapse status` (or `brain status`) — expect `ACTIVE`; if not, load vault paths manually.
2. Open `AGENTS.md`, `hot.md`, and `index.md`. If **index has >80 entries**, read only the
   relevant `synthesis/` hub plus targeted `grep`, not the full index.
3. Load pertinent notes (`summary:` first, body only if needed).
4. Check whether the topic already exists; reuse instead of reinventing.

### Phase 0-short (trivial tasks only)

For typos, formatting, or purely executional work with complete user instructions:

1. `synapse status` (or load paths manually if `NOT active`).
2. Read `hot.md` + targeted `grep` in the vault.
3. Skip hubs/MOC and full `index.md`.

## Phase 1 — During work

1. Apply loaded notes; cite pages as `[[page-name]]`.
2. If `synapse status` shows **STALE** hash, re-read `hot.md` and domain notes.
3. After applying a skill: `synapse skill use <name>` (+ `rate` if you can judge quality).
4. Capture non-obvious discoveries.

### Subagents

Every subagent prompt must include: vault path, 1–3 relevant pages/hubs, and the
meaningful-work distillation rule from this file.

## Meaningful work — when to distill

**Distill** if at least one applies: new pattern/architectural decision; non-obvious
problem solved; knowledge not already in the vault; project/infra setup; skill outcome
worth remembering.

**Skip** for: typos/formatting; answer already in vault; purely executional tasks.

## Phase 2 — Distillation

1. Split knowledge into atomic notes; classify; cross-link.
2. Update `index.md`, `hot.md`, and `log.md`.
3. Run `synapse check` (or `python3 _meta/validate.py`) — **0 errors**; review dedup candidates.

## Session close

If you **modified files under the vault** this session, run `synapse check` before finishing.
