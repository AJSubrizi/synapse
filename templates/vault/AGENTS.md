# AGENTS.md — Vault Operating Manual

This vault is the long-term memory for AI agents.

## Read Recipe

1. Read `index.md`.
2. Pick 1-3 relevant pages.
3. Read each page's `summary:` first.
4. Open full bodies only when needed.
5. Cite used pages as `[[page-name]]`.

## Write Recipe

1. Create atomic notes: one idea per page.
2. Use frontmatter with `title`, `category`, `tags`, `sources`, `summary`, `created`, `updated`.
3. Add at least one `[[wikilink]]` to an existing page.
4. Update `index.md`, `hot.md`, and `log.md`.
5. Run `python3 _meta/validate.py`.
6. Periodically run `python3 _meta/dedup.py` and merge or cross-link any flagged
   duplicate pairs (the detector only suggests; you decide and merge).

## Categories

- `concepts/` — mental models and principles.
- `references/` — how-to notes and source summaries.
- `synthesis/` — maps of content.
- `skills/` — skill catalogs and procedures.
- `projects/` — project-specific overview notes.
- `entities/` — people, tools, products, roles.
- `journal/` — dated observations.

