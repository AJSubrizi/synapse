# Changelog

## 0.1.1

- `validate.py` now warns on knowledge rot in addition to integrity errors:
  orphan notes (no links in or out), notes missing from `index.md`, and
  `category` frontmatter that does not match the folder. Warnings do not fail CI.
- Added `_meta/dedup.py`: a deterministic, dependency-free near-duplicate
  detector. It flags candidate duplicate notes (by title/summary/tag/body
  similarity) for a human or agent to review and merge — it never merges itself.
  Supports `--threshold` and `--strict` (exit 1 on candidates, for optional CI).

## 0.1.0

- Initial public starter kit.
- Added `brain` shim.
- Added vault skeleton.
- Added global AGENTS/CLAUDE/GEMINI templates.
- Added RTK recommendation docs.

