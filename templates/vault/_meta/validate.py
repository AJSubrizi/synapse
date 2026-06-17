#!/usr/bin/env python3
from __future__ import annotations

import glob
import os
import re
import sys

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAXONOMY = os.path.join(VAULT, "_meta", "taxonomy.md")
CONTENT_DIRS = ("concepts", "references", "synthesis", "skills", "projects", "journal", "entities")
REQUIRED = ("title", "category", "tags", "sources", "summary", "created", "updated")
SPECIAL = {"index", "log", "hot", "AGENTS"}


def load_taxonomy_tags() -> set[str]:
    """Canonical tags = every backticked token in taxonomy.md (covers aliases too)."""
    if not os.path.isfile(TAXONOMY):
        return set()
    text = open(TAXONOMY, encoding="utf-8").read()
    return {t.strip().lower() for t in re.findall(r"`([^`]+)`", text) if t.strip()}


def parse_tags(raw: str) -> list[str]:
    return [t.strip().lower() for t in raw.strip("[] ").split(",") if t.strip()]


def parse_frontmatter(text: str) -> dict[str, str] | None:
    if not text.lstrip().startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    frontmatter: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" in line and not line.lstrip().startswith("#"):  # Skip comments
            key, _, value = line.partition(":")
            frontmatter[key.strip()] = value.strip()
    return frontmatter


def strip_code(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]*`", "", text)
    return text


def main() -> int:
    files = [
        path
        for path in glob.glob(os.path.join(VAULT, "**", "*.md"), recursive=True)
        if "/_meta/" not in path
    ]
    stems = {os.path.splitext(os.path.basename(path))[0] for path in files}
    errors: list[str] = []
    warnings: list[str] = []

    # Knowledge-graph health, not just per-file integrity. These track whether the
    # vault stays *useful* over many distillation cycles (no orphans, no drift).
    outgoing: dict[str, set[str]] = {}   # note stem -> notes it links to
    incoming: dict[str, set[str]] = {}   # note stem -> notes that link to it
    index_targets: set[str] = set()      # notes catalogued in index.md
    content_notes: list[tuple[str, str, dict[str, str] | None]] = []  # (rel, stem, fm)

    for path in files:
        rel = os.path.relpath(path, VAULT)
        stem = os.path.splitext(os.path.basename(path))[0]
        text = open(path, encoding="utf-8").read()
        is_index = stem == "index" and os.sep not in rel

        for link in re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", strip_code(text)):
            target = link.split("/")[-1].strip()
            if target not in stems:
                errors.append(f"{rel}: broken wikilink [[{link}]]")
                continue
            if is_index:
                index_targets.add(target)
            if target != stem:
                outgoing.setdefault(stem, set()).add(target)
                incoming.setdefault(target, set()).add(stem)

        if stem in SPECIAL and os.sep not in rel:
            continue
        if not rel.startswith(CONTENT_DIRS):
            continue

        fm = parse_frontmatter(text)
        if fm is None:
            errors.append(f"{rel}: missing frontmatter")
            continue
        for key in REQUIRED:
            if key not in fm:
                errors.append(f"{rel}: missing frontmatter key {key}")
        content_notes.append((rel, stem, fm))

    # Warn (don't fail) on knowledge rot: the failure modes of auto-distilled vaults.
    known_tags = load_taxonomy_tags()
    for rel, stem, fm in content_notes:
        if not outgoing.get(stem) and not incoming.get(stem):
            warnings.append(f"{rel}: orphan note (no links in or out) — cross-link it")
        if stem not in index_targets:
            warnings.append(f"{rel}: not linked from index.md — add it to the catalog")
        folder = rel.split(os.sep)[0]
        category = (fm or {}).get("category")
        if category and category != folder:
            warnings.append(
                f"{rel}: category '{category}' does not match folder '{folder}'"
            )
        if known_tags:
            for tag in parse_tags((fm or {}).get("tags", "")):
                if tag not in known_tags:
                    warnings.append(
                        f"{rel}: unknown tag '{tag}' (not in _meta/taxonomy.md)"
                    )

    print(f"Pages analyzed: {len(files)}")
    print(f"Errors: {len(errors)} | Warnings: {len(warnings)}")
    for error in errors:
        print(f"  x {error}")
    for warning in warnings:
        print(f"  ! {warning}")
    if not errors and not warnings:
        print("  ok")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

