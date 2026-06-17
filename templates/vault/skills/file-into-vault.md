---
title: file-into-vault
category: skills
tags: [skills, workflow, knowledge]
sources: [synapse]
summary: Turn a draft note or an external source (URL, Git repo, document) into normalized, cross-linked vault notes with provenance, an index entry, and a passing check.
created: 2026-06-17T00:00:00Z
updated: 2026-06-17T00:00:00Z
uses: 0
score: 0.0
votes: 0
last_used: '-'
---

# file-into-vault

A reusable procedure (skill) for adding content to the vault — whether the user dropped a
rough Markdown draft or handed you an external source to ingest. It complements
[[distill-after-work]] (which distills what *you* learned); this one files *given* material.

## When to use

- The user dropped a note with just a title + body and asked you to "file it into the vault".
- The user gave you a source — a URL, a Git repo, a local document — to ingest.

## Steps

1. **Get the material.** For a draft, read the file. For a source, fetch it with your own
   tools (web fetch, `git clone`, file read) and skim for the high-signal parts.
2. **Split into atomic notes** — one idea per page. Don't dump a whole document into one note.
3. **Pick the folder**: `skills/`, `concepts/`, `references/`, `projects/`, `entities/`, or
   `synthesis/`. (Use `journal/` only for raw, dated capture.)
4. **Add frontmatter**: `title`, `category`, `tags` (1-5, from `_meta/taxonomy.md`), `sources`
   (the URL / repo / path it came from — provenance is mandatory for ingested material),
   `summary`, `created`, `updated`.
5. **Cross-link** with at least one `[[wikilink]]` to a related note.
6. **Register** the note under the right heading in `index.md`.
7. **Run `synapse check`** (validate + dedup); if dedup flags a near-duplicate, merge instead
   of adding a second copy.

## Scorecard

- Run `synapse skill use file-into-vault` after applying it.
- Rate quality with `synapse skill rate file-into-vault <1-5> [note]`.
- `synapse skill list` ranks the whole library by score, then by uses.

## Related

- [[distill-after-work]] — distill your own learnings after meaningful work
- [[workflow]] — the loop both skills belong to
