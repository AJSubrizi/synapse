---
title: Workflow
category: concepts
tags: [knowledge, workflow, memory]
sources: [synapse]
summary: The default agent loop: read the vault before work, then distill reusable knowledge after work.
created: 2026-01-01T00:00:00Z
updated: 2026-01-01T00:00:00Z
---

# Workflow

The brain is a persistent knowledge base. Agents are temporary workers.

This is the *concept* note for the loop. The step-by-step operating protocol lives in
`_meta/workflow.md` (kept out of the wiki graph, since `_meta/` holds machinery, not
knowledge).

## Loop

1. Read `index.md`.
2. Load relevant notes.
3. Work with context.
4. Distill reusable lessons into atomic pages.
5. Validate the vault.

## Related

- New atomic notes should link back here with `[[workflow]]` when they describe part
  of this loop. (This starter vault ships with one page; cross-links grow as you distill.)

