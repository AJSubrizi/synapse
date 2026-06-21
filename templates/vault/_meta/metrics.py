#!/usr/bin/env python3
"""Loop metrics — is the wiki actually compounding, or quietly stalling?

The value of an LLM Wiki is behavioral: does the agent keep distilling into it over time?
Code can't make that happen, but it can *measure* it. This reports knowledge size, growth,
loop activity (from log.md), and retrieval coverage — plus a blunt signal when distillation
has gone quiet. Stdlib only, offline, read-only.

  python3 _meta/metrics.py [--stale-days N] [--json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import sys

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META = os.path.join(VAULT, "_meta")

try:  # single source of truth for categories, with a test-time fallback
    from vault_config import CATEGORIES as CONTENT_DIRS
except Exception:
    CONTENT_DIRS = ("concepts", "techniques", "projects", "skills",
                    "sources", "analysis", "people", "organizations", "journal")


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.lstrip().startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fm: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


def parse_date(raw: str | None) -> dt.date | None:
    if not raw:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw.strip().strip("'\""))
    if not m:
        return None
    try:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def collect() -> dict:
    today = dt.date.today()
    by_cat: dict[str, int] = {}
    created: list[dt.date] = []
    for path in glob.glob(os.path.join(VAULT, "**", "*.md"), recursive=True):
        if "/_meta/" in path or "/raw/" in path:
            continue
        rel = os.path.relpath(path, VAULT)
        cat = rel.split(os.sep)[0]
        if cat not in CONTENT_DIRS:
            continue
        by_cat[cat] = by_cat.get(cat, 0) + 1
        d = parse_date(parse_frontmatter(open(path, encoding="utf-8").read()).get("created"))
        if d:
            created.append(d)

    raw_count = 0
    raw_dir = os.path.join(VAULT, "raw")
    if os.path.isdir(raw_dir):
        raw_count = sum(1 for _ in glob.glob(os.path.join(raw_dir, "**", "*"), recursive=True)
                        if os.path.isfile(_) and not _.endswith("README.md"))

    # Loop activity from the append-only log.
    ops = {"INGEST": 0, "FILE": 0, "INIT": 0, "other": 0}
    last_log: dt.date | None = None
    log_path = os.path.join(VAULT, "log.md")
    if os.path.isfile(log_path):
        for line in open(log_path, encoding="utf-8"):
            m = re.match(r"\s*-\s*\[([0-9T:\-Z]+)\]\s+(\w+)", line)
            if not m:
                continue
            verb = m.group(2).upper()
            ops[verb if verb in ops else "other"] += 1
            d = parse_date(m.group(1))
            if d and (last_log is None or d > last_log):
                last_log = d

    # Retrieval index coverage.
    index = {"built": False, "backend": None, "docs": 0}
    idx_path = os.path.join(META, "retrieval.json")
    if os.path.isfile(idx_path):
        try:
            data = json.load(open(idx_path, encoding="utf-8"))
            index["built"] = True
            index["backend"] = data.get("backend")
            docs = data.get("docs") or data.get("documents") or data.get("postings") or []
            index["docs"] = len(docs) if hasattr(docs, "__len__") else 0
        except Exception:
            index["built"] = True

    total = sum(by_cat.values())
    def added_within(days: int) -> int:
        return sum(1 for d in created if (today - d).days <= days)

    last_activity = max([d for d in [last_log] + ([max(created)] if created else []) if d],
                        default=None)

    return {
        "vault": VAULT,
        "pages_total": total,
        "by_category": dict(sorted(by_cat.items(), key=lambda kv: (-kv[1], kv[0]))),
        "raw_sources": raw_count,
        "added_7d": added_within(7),
        "added_30d": added_within(30),
        "first_page": min(created).isoformat() if created else None,
        "newest_page": max(created).isoformat() if created else None,
        "ops": ops,
        "last_activity": last_activity.isoformat() if last_activity else None,
        "days_since_activity": (today - last_activity).days if last_activity else None,
        "index": index,
    }


def render(m: dict, stale_days: int) -> str:
    L = []
    L.append("Synapse — loop metrics")
    L.append(f"Vault: {m['vault']}\n")

    L.append("Knowledge")
    L.append(f"  pages: {m['pages_total']} total   ·   raw sources: {m['raw_sources']}")
    if m["by_category"]:
        cats = " · ".join(f"{k} {v}" for k, v in m["by_category"].items())
        L.append(f"  by category: {cats}")

    L.append("\nGrowth (by created date)")
    L.append(f"  last 7d: +{m['added_7d']}   ·   last 30d: +{m['added_30d']}")
    if m["first_page"]:
        L.append(f"  span: {m['first_page']} → {m['newest_page']}")

    o = m["ops"]
    L.append("\nLoop activity (log.md)")
    L.append(f"  ingest: {o['INGEST']} · file: {o['FILE']} · other: {o['other']}")

    idx = m["index"]
    L.append("\nRetrieval")
    if idx["built"]:
        cov = f" · {idx['docs']} docs" if idx["docs"] else ""
        L.append(f"  index: {idx['backend'] or 'built'}{cov}")
    else:
        L.append("  index: not built (lexical fallback) — `synapse index` to build BM25")

    L.append("\nLoop signal")
    d = m["days_since_activity"]
    if d is None:
        L.append("  · no activity recorded yet — ingest or distill to start the loop")
    elif d <= stale_days:
        L.append(f"  ✓ distilled within the last {d} day(s) — the loop is live")
    else:
        L.append(f"  ⚠ no distillation in {d} days — the loop may be stalling")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Loop metrics for the wiki.")
    ap.add_argument("--stale-days", type=int, default=14,
                    help="flag the loop as stalling after N days without activity")
    ap.add_argument("--json", action="store_true", help="emit raw JSON instead of a report")
    args = ap.parse_args()
    m = collect()
    print(json.dumps(m, indent=2) if args.json else render(m, args.stale_days))
    return 0


if __name__ == "__main__":
    sys.exit(main())
