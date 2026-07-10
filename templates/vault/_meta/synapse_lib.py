#!/usr/bin/env python3
"""Shared vault helpers — one frontmatter/parser/iterator for every engine.

Engines (validate, dedup, search, wiki, metrics, skill) should import from here
instead of re-implementing YAML-ish frontmatter splits. Stdlib only.
"""
from __future__ import annotations

import glob
import os
import re
from typing import Iterator

HERE = os.path.dirname(os.path.abspath(__file__))
VAULT = os.path.dirname(HERE)

try:
    from vault_config import CATEGORIES, DEFAULT
except Exception:
    CATEGORIES = DEFAULT = (
        "concepts", "techniques", "projects", "skills",
        "sources", "analysis", "people", "organizations", "journal",
    )

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "else", "for", "of", "to",
    "in", "on", "at", "by", "with", "as", "is", "are", "be", "was", "were", "this",
    "that", "these", "those", "it", "its", "into", "from", "when", "use", "used",
}


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return (frontmatter_dict, body). Empty dict if no frontmatter."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip()
    return fm, text[end + 4:]


def split_fm_lines(text: str) -> tuple[list[str], str]:
    """Return (frontmatter_lines, rest) — for in-place key updates (skill/wiki)."""
    if not text.startswith("---"):
        return [], text
    end = text.find("\n---", 3)
    if end == -1:
        return [], text
    return text[3:end].lstrip("\n").splitlines(), text[end + 4:]


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Like split_frontmatter but None when missing (validate-style)."""
    if not text.startswith("---"):
        return None
    fm, _ = split_frontmatter(text)
    return fm if fm else {}


def fm_get(fm_lines: list[str], key: str) -> str | None:
    for line in fm_lines:
        m = re.match(rf"{key}\s*:\s*(.*)$", line)
        if m:
            return m.group(1).strip().strip("'\"")
    return None


def parse_tags(raw: str) -> list[str]:
    return [t.strip().lower() for t in (raw or "").strip("[] ").split(",") if t.strip()]


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [w for w in words if len(w) >= 3 and w not in STOPWORDS]


def iter_notes(
    vault: str | None = None,
    categories: tuple[str, ...] | None = None,
) -> Iterator[tuple[str, str]]:
    """Yield (abs_path, rel_path) for wiki notes under category dirs."""
    root = vault or VAULT
    cats = categories or CATEGORIES
    for path in sorted(glob.glob(os.path.join(root, "**", "*.md"), recursive=True)):
        if "/_meta/" in path.replace("\\", "/"):
            continue
        rel = os.path.relpath(path, root)
        if not rel.startswith(cats):
            continue
        yield path, rel


def wikilinks(text: str) -> list[str]:
    return re.findall(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]", text or "")
