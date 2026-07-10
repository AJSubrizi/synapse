#!/usr/bin/env python3
"""Deterministic wiki mutations for the LLM Wiki (Karpathy's pattern).

The agent writes prose; this writes *structure*. Creating a page by hand means getting
the frontmatter right, registering it under the correct `index.md` heading, and appending
to `log.md` — three places that drift out of sync. `wiki.py new` does all three atomically
so `ingest` and the query file-back are real operations, not just a recipe to follow.

  python3 _meta/wiki.py new --category sources --title "RFC 9110" \
      --source raw/rfc-9110.txt --summary "HTTP semantics" --tags knowledge,backend \
      --link rest-api-design --op INGEST

Prints the created page path. Idempotent on the page file (won't overwrite); the index
and log are append-only and de-duplicated by page stem.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
from difflib import SequenceMatcher

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Categories from the single source of truth (_meta/vault_config.py, configurable via
# _meta/categories). Each maps to an index.md heading. Test-time fallback if imported.
try:
    from vault_config import CATEGORIES
except Exception:
    CATEGORIES = (
        "concepts", "techniques", "projects", "skills",
        "sources", "analysis", "people", "organizations", "journal",
    )
try:
    from synapse_lib import split_fm_lines
except Exception:
    def split_fm_lines(text: str) -> tuple[list[str], str]:
        if not text.startswith("---"):
            return [], text
        end = text.find("\n---", 3)
        if end == -1:
            return [], text
        return text[3:end].lstrip("\n").splitlines(), text[end + 4:]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s or "untitled"


def heading_for(category: str) -> str:
    return category.capitalize()


def page_exists(stem: str) -> bool:
    for cat in CATEGORIES:
        if os.path.isfile(os.path.join(VAULT, cat, f"{stem}.md")):
            return True
    return False


def near_duplicates(title: str, summary: str, threshold: float = 0.72) -> list[tuple[float, str, str]]:
    """Return (score, relpath, stem) for notes with a near-matching title/stem.

    Title + stem only (not default 'Notes on …' summaries) so empty stubs do not
    false-positive. Callers refuse create unless --force.
    """
    title_l = title.lower().strip()
    stem_new = slugify(title)
    hits: list[tuple[float, str, str]] = []
    for cat in CATEGORIES:
        d = os.path.join(VAULT, cat)
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            if not name.endswith(".md"):
                continue
            path = os.path.join(d, name)
            try:
                text = open(path, encoding="utf-8").read()
            except OSError:
                continue
            fm_lines, _ = split_fm_lines(text)
            fm: dict[str, str] = {}
            for line in fm_lines:
                if ":" in line and not line.startswith(" "):
                    k, _, v = line.partition(":")
                    fm[k.strip()] = v.strip()
            stem = name[:-3]
            existing_title = (fm.get("title") or stem).lower().strip()
            title_sim = SequenceMatcher(None, title_l, existing_title).ratio() if title_l else 0.0
            stem_sim = SequenceMatcher(None, stem_new, stem).ratio()
            score = max(title_sim, stem_sim)
            # Optional: if caller passed a real summary, boost when both title and summary match
            existing_sum = (fm.get("summary") or "").lower().strip()
            if summary and len(summary) >= 20 and existing_sum and not existing_sum.startswith("notes on "):
                sum_sim = SequenceMatcher(None, summary.lower(), existing_sum).ratio()
                if title_sim >= 0.5 and sum_sim >= 0.7:
                    score = max(score, 0.55 * title_sim + 0.45 * sum_sim)
            if score >= threshold:
                hits.append((score, os.path.relpath(path, VAULT), stem))
    hits.sort(reverse=True)
    return hits[:5]


def write_page(path: str, fm: dict[str, str], link: str | None, source: str | None) -> None:
    lines = ["---"]
    for key in ("title", "category", "tags", "sources", "summary", "created", "updated"):
        lines.append(f"{key}: {fm[key]}")
    lines.append("---\n")
    lines.append(f"# {fm['title']}\n")
    if source:
        lines.append(f"> Derived from `{source}` (immutable source under `raw/`).\n")
    lines.append("## Takeaways\n")
    lines.append("_Fill in the high-signal points distilled from the source._\n")
    if link:
        lines.append("## Related\n")
        lines.append(f"- [[{link}]]\n")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def register_in_index(stem: str, summary: str, tags: list[str], heading: str) -> bool:
    """Insert a catalog bullet under `## <heading>` in index.md. No-op if already listed."""
    index = os.path.join(VAULT, "index.md")
    if not os.path.isfile(index):
        return False
    # flock against concurrent agents filing notes in the same session
    with open(index, "r+", encoding="utf-8") as fh:
        try:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_EX)
        except Exception:
            pass
        text = fh.read()
        if re.search(rf"\[\[{re.escape(stem)}\]\]", text):
            return False  # already catalogued
        tag_str = "".join(f" #{t}" for t in tags)
        bullet = f"- [[{stem}]] — {summary} ({tag_str.strip()})"
        lines = text.splitlines()
        out: list[str] = []
        inserted = False
        i = 0
        while i < len(lines):
            out.append(lines[i])
            if not inserted and lines[i].strip() == f"## {heading}":
                j = i + 1
                block: list[str] = []
                while j < len(lines) and not lines[j].startswith("## "):
                    block.append(lines[j])
                    j += 1
                while block and block[-1].strip() == "":
                    block.pop()
                if not block:
                    block.append("")
                block.append(bullet)
                block.append("")
                out.extend(block)
                i = j
                inserted = True
                continue
            i += 1
        if not inserted:
            if out and out[-1].strip() != "":
                out.append("")
            out.extend([f"## {heading}", "", bullet, ""])
        fh.seek(0)
        fh.truncate()
        fh.write("\n".join(out).rstrip() + "\n")
        try:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_UN)
        except Exception:
            pass
    return True


def append_log(op: str, stem: str, category: str, source: str | None) -> None:
    log = os.path.join(VAULT, "log.md")
    src = f' source="{source}"' if source else ""
    entry = f'- [{now_iso()}] {op} page="{category}/{stem}"{src}'
    with open(log, "a", encoding="utf-8") as fh:
        try:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_EX)
        except Exception:
            pass
        fh.write(entry + "\n")
        try:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_UN)
        except Exception:
            pass


def cmd_new(args: argparse.Namespace) -> int:
    if args.category not in CATEGORIES:
        print(f"wiki: unknown category '{args.category}' (one of: {', '.join(CATEGORIES)})",
              file=sys.stderr)
        return 2
    stem = slugify(args.title)
    if page_exists(stem):
        print(f"wiki: page already exists: {stem}.md (not overwriting)", file=sys.stderr)
        print(f"       prefer: synapse file update {stem}", file=sys.stderr)
        return 1
    tags = [t.strip().lower() for t in (args.tags or "knowledge").split(",") if t.strip()]
    summary = args.summary or f"Notes on {args.title}."
    if len(summary) < 10:
        summary = (summary + " — fill in the one-line gist.")[:240]
    # Search-before-create: refuse near-duplicates unless --force
    if not getattr(args, "force", False):
        dups = near_duplicates(args.title, summary)
        if dups:
            print("wiki: near-duplicate(s) found — refuse create (pass --force to override):",
                  file=sys.stderr)
            for score, rel, existing in dups:
                print(f"  ~ {score:.2f}  {rel}  (update: synapse file update {existing})",
                      file=sys.stderr)
            return 1
    sources = f"[{args.source}]" if args.source else "[]"
    ts = now_iso()
    fm = {
        "title": args.title,
        "category": args.category,
        "tags": "[" + ", ".join(tags) + "]",
        "sources": sources,
        "summary": summary,
        "created": ts,
        "updated": ts,
    }
    path = os.path.join(VAULT, args.category, f"{stem}.md")
    write_page(path, fm, args.link, args.source)
    register_in_index(stem, summary, tags, heading_for(args.category))
    append_log(args.op, stem, args.category, args.source)
    print(os.path.relpath(path, VAULT))
    return 0


def find_page(stem: str) -> str | None:
    for cat in CATEGORIES:
        path = os.path.join(VAULT, cat, f"{stem}.md")
        if os.path.isfile(path):
            return path
    return None


def set_fm_keys(fm: list[str], updates: dict[str, str]) -> list[str]:
    seen: set[str] = set()
    out = list(fm)
    for i, line in enumerate(out):
        m = re.match(r"(\w+)\s*:", line)
        if m and m.group(1) in updates:
            out[i] = f"{m.group(1)}: {updates[m.group(1)]}"
            seen.add(m.group(1))
    for k, v in updates.items():
        if k not in seen:
            out.append(f"{k}: {v}")
    return out


def cmd_update(args: argparse.Namespace) -> int:
    """Refresh summary/tags/links on an existing page; bump updated; log UPDATE."""
    stem = slugify(args.title) if args.title else (args.stem or "")
    if args.stem:
        stem = args.stem
    if not stem:
        print("wiki: update requires --stem or --title", file=sys.stderr)
        return 2
    path = find_page(stem)
    if not path:
        print(f"wiki: page not found: {stem}.md", file=sys.stderr)
        return 1
    text = open(path, encoding="utf-8").read()
    fm, rest = split_fm_lines(text)
    if not fm:
        print(f"wiki: no frontmatter on {stem}.md", file=sys.stderr)
        return 1
    updates: dict[str, str] = {"updated": now_iso()}
    if args.summary:
        updates["summary"] = args.summary[:240]
    if args.tags:
        tags = [t.strip().lower() for t in args.tags.split(",") if t.strip()]
        updates["tags"] = "[" + ", ".join(tags) + "]"
    fm = set_fm_keys(fm, updates)
    if args.link and f"[[{args.link}]]" not in rest:
        if "## Related" in rest:
            rest = rest.rstrip() + f"\n- [[{args.link}]]\n"
        else:
            rest = rest.rstrip() + f"\n\n## Related\n\n- [[{args.link}]]\n"
    open(path, "w", encoding="utf-8").write("---\n" + "\n".join(fm) + "\n---\n" + rest)
    cat = os.path.basename(os.path.dirname(path))
    append_log("UPDATE", stem, cat, None)
    print(os.path.relpath(path, VAULT))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministic wiki mutations.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new", help="create a wiki page + register it in index.md + log.md")
    p.add_argument("--category", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--summary", default="")
    p.add_argument("--tags", default="")
    p.add_argument("--source", default="")
    p.add_argument("--link", default="")
    p.add_argument("--op", default="FILE", help="log verb (INGEST, FILE, ...)")
    p.add_argument("--force", action="store_true",
                   help="create even when a near-duplicate title/summary exists")
    u = sub.add_parser("update", help="refresh an existing page (summary/tags/link/updated)")
    u.add_argument("--stem", default="", help="page stem (filename without .md)")
    u.add_argument("--title", default="", help="title to slugify if --stem omitted")
    u.add_argument("--summary", default="")
    u.add_argument("--tags", default="")
    u.add_argument("--link", default="")
    args = ap.parse_args()
    if args.cmd == "new":
        args.source = args.source or None
        args.link = args.link or None
        return cmd_new(args)
    if args.cmd == "update":
        args.link = args.link or None
        return cmd_update(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
