#!/usr/bin/env python3
from __future__ import annotations

import glob
import os
import re
import sys

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIRS = ("concepts", "references", "synthesis", "skills", "projects", "journal", "entities")
REQUIRED = ("title", "category", "tags", "sources", "summary", "created", "updated")
SPECIAL = {"index", "log", "hot", "AGENTS"}


def parse_frontmatter(text: str) -> dict[str, str] | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    frontmatter: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" in line and not line.startswith(" "):
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

    for path in files:
        rel = os.path.relpath(path, VAULT)
        stem = os.path.splitext(os.path.basename(path))[0]
        text = open(path, encoding="utf-8").read()

        for link in re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", strip_code(text)):
            target = link.split("/")[-1].strip()
            if target not in stems:
                errors.append(f"{rel}: broken wikilink [[{link}]]")

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

