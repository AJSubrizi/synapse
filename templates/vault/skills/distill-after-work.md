---
title: distill-after-work
category: skills
tags: [skills, workflow]
sources: [synapse]
summary: After meaningful work, turn what was learned into atomic vault notes, cross-link them, update the catalog, and validate.
created: 2026-01-01T00:00:00Z
updated: 2026-06-18T00:00:00Z
version: 2
requires: [[file-into-vault]]
uses: 0
score: 0.0
votes: 0
last_used: '-'
---

# distill-after-work

A reusable procedure (skill) for the distillation phase of the loop. The block of
`uses` / `score` / `votes` / `last_used` keys above is the **scorecard**: it turns this
vault into a rated *skills library*, not just memory.

## When to run

After any *meaningful* unit of work — a bug understood, a convention decided, an API
learned, a dead end ruled out. Skip trivial edits. If you wouldn't want a future agent
to re-derive it, distill it.

## Steps

1. **Decide create vs update.** Search first: `synapse search "<topic>"`. If a note
   already covers the idea, update it (and bump `updated`) instead of adding a near-duplicate.
2. **Split into atomic notes** — one idea per page. A note is atomic when its title is a
   single claim or concept and you can't split it without one half becoming a stub.
3. **Write frontmatter** (all required keys): `title, category, tags, sources, summary,
   created, updated`. `category` must equal the folder. Pick `tags` from
   `_meta/taxonomy.md` — don't invent new ones without adding them there.
4. **Write a one-line `summary`** — the gist a future agent reads before opening the note.
   Keep it under ~240 chars; the body holds the detail.
5. **Cross-link**: at least one `[[wikilink]]` in or out. New notes must not be orphans.
6. **Update the catalog**: add the note to `index.md`; surface hot items in `hot.md`;
   append a one-line entry to `log.md`.
7. **Refresh the map** (optional, for large vaults): `synapse digest`.
8. **Validate and self-correct**: run `synapse check --strict`, then fix every warning it
   prints and re-run until clean. This is the loop — don't stop at the first pass.

## What "good" looks like

**Good (atomic, linked, tight summary):**

```markdown
---
title: tailwind-shadcn-styling
category: concepts
tags: [frontend, styling]
sources: [project-x]
summary: Use shadcn/ui primitives; restyle via Tailwind utility classes, never by editing component internals.
created: 2026-06-18T00:00:00Z
updated: 2026-06-18T00:00:00Z
---
# tailwind-shadcn-styling
Restyle shadcn components with utility classes on the wrapper; see [[frontend-stack]].
```

**Bad (and why):**

- Title `notes` or `misc` — not a claim; not atomic. Split into named concepts.
- `summary` is three sentences of the body. Compress to one line.
- No wikilinks. Orphan; cross-link to a hub note.
- `tags: [frontend, ui, css, styles, design]` none in taxonomy. Reuse canonical tags.
- Two notes, `api-auth` and `auth-api`, ~80% overlap. `synapse check` flags the pair; merge.

## Scorecard

- The agent runs `synapse skill use distill-after-work` after applying it.
- Anyone can run `synapse skill rate distill-after-work <1-5> [note]` to vote on quality.
- `synapse skill list` ranks the whole library by score, then by uses.

## Related

- [[workflow]] — the loop this skill belongs to
- [[file-into-vault]] — filing a draft or external source into the right folder
