#!/usr/bin/env python3
"""Portable memory packs — share a subtree of the wiki as a file-based bundle.

A pack is a directory (or .tar.gz) with:
  PACK.md          manifest (name, version, pages, provenance)
  <category>/*.md  wiki pages
  raw/             optional immutable sources cited by those pages

  python3 _meta/pack.py export <name> [--pages a,b,c] [--category concepts] [--out DIR]
  python3 _meta/pack.py import <pack-path> [--force]

No database. Import never overwrites existing pages unless --force.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import sys
import tarfile

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META = os.path.join(VAULT, "_meta")

try:
    from vault_config import CATEGORIES
    from synapse_lib import split_frontmatter, wikilinks
except Exception:
    CATEGORIES = (
        "concepts", "techniques", "projects", "skills",
        "sources", "analysis", "people", "organizations", "journal",
    )

    def split_frontmatter(text: str):
        if not text.startswith("---"):
            return {}, text
        end = text.find("\n---", 3)
        if end == -1:
            return {}, text
        fm = {}
        for line in text[3:end].splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip()
        return fm, text[end + 4:]

    def wikilinks(text: str):
        return re.findall(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]", text or "")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def find_page(stem: str) -> str | None:
    for cat in CATEGORIES:
        path = os.path.join(VAULT, cat, f"{stem}.md")
        if os.path.isfile(path):
            return path
    return None


def collect_pages(stems: list[str]) -> list[tuple[str, str]]:
    """Return list of (rel, abs_path). Follow one hop of wikilinks."""
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    queue = list(stems)
    while queue:
        stem = queue.pop(0)
        if stem in seen:
            continue
        path = find_page(stem)
        if not path:
            print(f"pack: missing page {stem}.md", file=sys.stderr)
            continue
        seen.add(stem)
        rel = os.path.relpath(path, VAULT)
        out.append((rel, path))
        text = open(path, encoding="utf-8").read()
        for link in wikilinks(text):
            link = link.strip()
            if link and link not in seen:
                queue.append(link)
    return out


def cmd_export(args: argparse.Namespace) -> int:
    stems: list[str] = []
    if args.pages:
        stems = [s.strip() for s in args.pages.split(",") if s.strip()]
    elif args.category:
        cat_dir = os.path.join(VAULT, args.category)
        if not os.path.isdir(cat_dir):
            print(f"pack: no category dir {args.category}", file=sys.stderr)
            return 2
        stems = [os.path.splitext(f)[0] for f in os.listdir(cat_dir) if f.endswith(".md")]
    else:
        print("pack export: pass --pages a,b or --category concepts", file=sys.stderr)
        return 2

    pages = collect_pages(stems)
    if not pages:
        print("pack: nothing to export", file=sys.stderr)
        return 1

    out_dir = args.out or os.path.join(META, "packs", args.name)
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)

    raw_copied = []
    for rel, path in pages:
        dest = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(path, dest)
        fm, _ = split_frontmatter(open(path, encoding="utf-8").read())
        srcs = fm.get("sources", "")
        for m in re.findall(r"raw/[^\s\],'\"]+", srcs):
            src_path = os.path.join(VAULT, m)
            if os.path.isfile(src_path):
                rdest = os.path.join(out_dir, m)
                os.makedirs(os.path.dirname(rdest), exist_ok=True)
                shutil.copy2(src_path, rdest)
                raw_copied.append(m)

    manifest = [
        "---",
        f"name: {args.name}",
        f"version: {args.version}",
        f"exported: {now_iso()}",
        f"pages: {len(pages)}",
        f"raw: {len(raw_copied)}",
        "---",
        "",
        f"# Pack: {args.name}",
        "",
        "File-based Synapse memory pack. Import with:",
        "",
        f"```bash",
        f"synapse pack import {args.name}.tar.gz",
        f"```",
        "",
        "## Pages",
        "",
    ]
    for rel, _ in pages:
        manifest.append(f"- `{rel}`")
    if raw_copied:
        manifest.append("")
        manifest.append("## Raw sources")
        manifest.append("")
        for r in raw_copied:
            manifest.append(f"- `{r}`")
    open(os.path.join(out_dir, "PACK.md"), "w", encoding="utf-8").write(
        "\n".join(manifest) + "\n"
    )

    archive = args.archive or f"{args.name}.tar.gz"
    if not os.path.isabs(archive):
        archive = os.path.join(os.getcwd(), archive)
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(out_dir, arcname=args.name)
    print(f"pack: exported {len(pages)} pages -> {archive}")
    print(f"      working copy: {out_dir}")
    return 0


def _extract_pack(path: str, dest: str) -> str:
    """Extract pack path (dir or tar.gz) into dest; return root dir containing PACK.md."""
    if os.path.isdir(path):
        return path
    os.makedirs(dest, exist_ok=True)
    with tarfile.open(path, "r:gz") as tar:
        tar.extractall(dest)
    # find PACK.md
    for root, _dirs, files in os.walk(dest):
        if "PACK.md" in files:
            return root
    raise FileNotFoundError("PACK.md not found in archive")


def cmd_import(args: argparse.Namespace) -> int:
    tmp = os.path.join(META, ".pack-import-tmp")
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    try:
        root = _extract_pack(args.path, tmp)
    except Exception as exc:
        print(f"pack: cannot open {args.path}: {exc}", file=sys.stderr)
        return 2

    imported = 0
    skipped = 0
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if f == "PACK.md" or not f.endswith(".md"):
                # also copy non-md raw files
                rel = os.path.relpath(os.path.join(dirpath, f), root)
                if rel.startswith("raw" + os.sep) or rel.startswith("raw/"):
                    dest = os.path.join(VAULT, rel)
                    if os.path.exists(dest) and not args.force:
                        skipped += 1
                        continue
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.copy2(os.path.join(dirpath, f), dest)
                    imported += 1
                continue
            rel = os.path.relpath(os.path.join(dirpath, f), root)
            if rel == "PACK.md":
                continue
            dest = os.path.join(VAULT, rel)
            if os.path.exists(dest) and not args.force:
                print(f"pack: skip existing {rel}")
                skipped += 1
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(os.path.join(dirpath, f), dest)
            # register in index/log when wiki.py available
            stem = os.path.splitext(os.path.basename(f))[0]
            cat = rel.split(os.sep)[0]
            try:
                sys.path.insert(0, META)
                import wiki
                fm, _ = split_frontmatter(open(dest, encoding="utf-8").read())
                summary = (fm.get("summary") or f"Imported pack page {stem}.").strip()
                tags = [t.strip() for t in fm.get("tags", "[]").strip("[] ").split(",") if t.strip()]
                wiki.register_in_index(stem, summary, tags or ["knowledge"], cat.capitalize())
                wiki.append_log("PACK", stem, cat, None)
            except Exception:
                pass
            print(f"pack: imported {rel}")
            imported += 1

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"pack: done — imported {imported}, skipped {skipped}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Synapse memory packs")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("name")
    e.add_argument("--pages", default="", help="comma-separated page stems")
    e.add_argument("--category", default="", help="export whole category (+ 1-hop links)")
    e.add_argument("--version", default="1")
    e.add_argument("--out", default="", help="working directory for the pack")
    e.add_argument("--archive", default="", help="output .tar.gz path")
    i = sub.add_parser("import")
    i.add_argument("path", help="pack directory or .tar.gz")
    i.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if args.cmd == "export":
        return cmd_export(args)
    if args.cmd == "import":
        return cmd_import(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
