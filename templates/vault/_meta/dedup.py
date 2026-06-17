#!/usr/bin/env python3
"""Deterministic near-duplicate detector for the vault.

This finds *candidate* duplicate notes; it never merges anything. Detection is
cheap and repeatable (stdlib only, no embeddings, no network); deciding whether a
pair is truly redundant — and merging without losing nuance — is left to a human
or an AI agent reviewing only the flagged pairs.

Usage:
  python3 _meta/dedup.py                 # report pairs scoring >= 0.5
  python3 _meta/dedup.py --threshold 0.7 # stricter
  python3 _meta/dedup.py --strict        # exit 1 if any candidate (for CI)
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from difflib import SequenceMatcher
from itertools import combinations

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIRS = ("concepts", "references", "synthesis", "skills", "projects", "journal", "entities")
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "else", "for", "of", "to",
    "in", "on", "at", "by", "with", "as", "is", "are", "be", "was", "were", "this",
    "that", "these", "those", "it", "its", "into", "from", "when", "use", "used",
}


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip()
    return fm, text[end + 4:]


def parse_tags(raw: str) -> set[str]:
    return {t.strip().lower() for t in raw.strip("[] ").split(",") if t.strip()}


def tokenize(body: str) -> set[str]:
    body = re.sub(r"```.*?```", " ", body, flags=re.DOTALL)
    body = re.sub(r"`[^`]*`", " ", body)
    body = re.sub(r"\[\[[^\]]*\]\]", " ", body)
    words = re.findall(r"[a-z0-9]+", body.lower())
    return {w for w in words if len(w) >= 3 and w not in STOPWORDS}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--strict", action="store_true", help="exit 1 if any candidate found")
    ap.add_argument("--optimize", action="store_true", help="use inverted index for faster dedup (default: auto)")
    args = ap.parse_args()

    notes = []
    for path in glob.glob(os.path.join(VAULT, "**", "*.md"), recursive=True):
        rel = os.path.relpath(path, VAULT)
        # Skip files in _meta/ directory (exact match to avoid false positives)
        if "/_meta/" in rel or rel.startswith("_meta/"):
            continue
        if not rel.startswith(CONTENT_DIRS):
            continue
        fm, body = split_frontmatter(open(path, encoding="utf-8").read())
        stem = os.path.splitext(os.path.basename(path))[0]
        meta = f"{fm.get('title', stem)} {fm.get('summary', '')}".lower()
        notes.append((rel, meta, parse_tags(fm.get("tags", "")), tokenize(body)))

    # Use inverted index optimization if enabled or if notes > 50
    use_inverted_index = args.optimize or len(notes) > 50
    if use_inverted_index:
        # Build inverted index: token -> list of note indices
        token_to_notes = {}
        for idx, (rel, meta, tags, body_tokens) in enumerate(notes):
            all_tokens = body_tokens | tags
            for token in all_tokens:
                if token not in token_to_notes:
                    token_to_notes[token] = []
                token_to_notes[token].append(idx)

        # Only compare notes that share at least one token
        compared_pairs = set()
        candidates = []
        for token, note_indices in token_to_notes.items():
            for i in range(len(note_indices)):
                for j in range(i + 1, len(note_indices)):
                    idx_a = note_indices[i]
                    idx_b = note_indices[j]
                    if (idx_a, idx_b) in compared_pairs:
                        continue
                    compared_pairs.add((idx_a, idx_b))
                    rel_a, meta_a, tags_a, body_a = notes[idx_a]
                    rel_b, meta_b, tags_b, body_b = notes[idx_b]
                    meta_sim = SequenceMatcher(None, meta_a, meta_b).ratio()
                    body_sim = jaccard(body_a, body_b)
                    tag_sim = jaccard(tags_a, tags_b)
                    score = 0.5 * meta_sim + 0.4 * body_sim + 0.1 * tag_sim
                    if score >= args.threshold:
                        candidates.append((score, rel_a, rel_b, meta_sim, body_sim, tag_sim))
    else:
        # Original O(n^2) approach for small vaults
        candidates = []
        for (rel_a, meta_a, tags_a, body_a), (rel_b, meta_b, tags_b, body_b) in combinations(notes, 2):
            meta_sim = SequenceMatcher(None, meta_a, meta_b).ratio()
            body_sim = jaccard(body_a, body_b)
            tag_sim = jaccard(tags_a, tags_b)
            score = 0.5 * meta_sim + 0.4 * body_sim + 0.1 * tag_sim
            if score >= args.threshold:
                candidates.append((score, rel_a, rel_b, meta_sim, body_sim, tag_sim))

    candidates.sort(reverse=True)
    print(f"Notes analyzed: {len(notes)}")
    print(f"Candidate duplicate pairs (threshold {args.threshold}): {len(candidates)}")
    for score, rel_a, rel_b, meta_sim, body_sim, tag_sim in candidates:
        print(f"  ~ {score:.2f}  {rel_a}  <->  {rel_b}")
        print(f"       title/summary={meta_sim:.2f} body={body_sim:.2f} tags={tag_sim:.2f}")
    if not candidates:
        print("  ok")
    return 1 if (candidates and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
