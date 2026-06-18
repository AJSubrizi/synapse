# Distillation example — before / after

A concrete look at the distillation phase: messy session output on the left, the atomic,
linked, validated vault notes it should become on the right.

- [`before-raw-session.md`](before-raw-session.md) — what an agent "knows" at the end of a
  task: a wall of mixed findings, decisions, and dead ends.
- [`after/`](after/) — the same knowledge distilled into atomic notes with frontmatter,
  canonical tags, `[[wikilinks]]`, and one-line summaries. This is what passes
  `synapse check --strict`.

## The moves that turn one into the other

1. **Search before writing** — `synapse search "auth token"` to avoid duplicating a note.
2. **Split by idea** — one claim per note; the raw session became three notes.
3. **Tight summary** — a one-line gist per note (the body holds the detail).
4. **Cross-link** — every note links to at least one other; no orphans.
5. **Catalog + validate** — add to `index.md`, then `synapse check --strict` until clean.

See the [`distill-after-work`](../../templates/vault/skills/distill-after-work.md) skill for
the full procedure.
