# Workflow

Read the brain before work. Distill into the brain after work.

## Phase 0 — Before Work

1. Confirm the brain is loaded: run `brain status` (expect `ACTIVE`, not stale).
2. Open `index.md`.
3. Open the relevant synthesis or concept notes.
4. Check whether the topic already exists.

## Phase 1 — During Work

1. Apply the loaded notes.
2. Capture non-obvious discoveries.
3. Cite pages as `[[page-name]]`.

## Phase 2 — Distillation

1. Split knowledge into atomic notes.
2. Classify each note.
3. Cross-link it.
4. Update `index.md`, `hot.md`, and `log.md`.
5. Run `brain check` (validate + dedup, read-only) — or `python3 _meta/validate.py`
   directly. Resolve errors before finishing; review any duplicate candidates.

