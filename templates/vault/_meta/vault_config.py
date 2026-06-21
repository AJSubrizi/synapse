#!/usr/bin/env python3
"""Single source of truth for wiki categories — configurable, no database.

Karpathy's taxonomy is a *suggestion*; a coding vault doesn't need all of it. So the
categories are split into a small CORE (used constantly) and OPTIONAL ones (supported,
created on demand), and the whole set can be overridden per-vault by editing the plain
`_meta/categories` file (one category per line; `#` comments allowed).

Every engine (validate / dedup / search / wiki) imports CATEGORIES from here so the vault
has one consistent notion of what a valid category is.
"""
from __future__ import annotations

import os

META = os.path.dirname(os.path.abspath(__file__))

# What a coding vault reaches for on every session.
CORE = ("concepts", "techniques", "projects", "skills")
# Supported but not scaffolded by default; created on demand when you first file into them.
OPTIONAL = ("sources", "analysis", "people", "organizations", "journal")


def load_categories() -> tuple[str, ...]:
    """CATEGORIES = the `_meta/categories` override if present, else CORE + OPTIONAL."""
    path = os.path.join(META, "categories")
    if os.path.isfile(path):
        cats = []
        for line in open(path, encoding="utf-8"):
            line = line.split("#", 1)[0].strip()
            if line:
                cats.append(line)
        if cats:
            return tuple(cats)
    return CORE + OPTIONAL


CATEGORIES = load_categories()

# Fallback the engines use if they can't import this module (e.g. imported as a package
# member in tests rather than run as a script). Kept in sync with CORE + OPTIONAL.
DEFAULT = CORE + OPTIONAL
