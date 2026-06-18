#!/usr/bin/env python3
"""Optional retrieval layer for the vault — file-based, no database.

The vault works without this: agents walk `index.md` + `[[wikilinks]]`. When a vault
grows past what fits comfortably in context, this gives the agent a fast way to *find*
the few relevant notes instead of reading everything.

Three levels, smallest dependency first:

  search   lexical search over frontmatter (title/tags/summary, weighted) + body.
           Uses ripgrep if present, else a pure-stdlib scan. Zero new deps.
  digest   regenerate `_meta/digest.md`: one compact line per note
           (stem · category · tags · summary) — a map the agent reads in Phase 0.
  index    build an optional retrieval index for a pluggable backend
           (default: local TF-IDF in `_meta/retrieval.json`). Embeddings backends
           are opt-in via $SYNAPSE_RETRIEVAL_BACKEND and degrade cleanly if absent.

Usage:
  python3 _meta/search.py search <query> [--limit N] [--body]
  python3 _meta/search.py digest [--write]
  python3 _meta/search.py index [--backend tfidf|embeddings]
  python3 _meta/search.py query <query> [--limit N]   # uses the built index

Philosophy: every level is optional and degrades. If Python/ripgrep/a model is
missing, the layer below still answers; a vault with no index behaves exactly as before.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import shutil
import subprocess
import sys
from collections import Counter

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META = os.path.join(VAULT, "_meta")
CONTENT_DIRS = ("concepts", "references", "synthesis", "skills", "projects", "journal", "entities")
DIGEST = os.path.join(META, "digest.md")
INDEX = os.path.join(META, "retrieval.json")
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


def iter_notes():
    for path in sorted(glob.glob(os.path.join(VAULT, "**", "*.md"), recursive=True)):
        if "/_meta/" in path:
            continue
        rel = os.path.relpath(path, VAULT)
        if not rel.startswith(CONTENT_DIRS):
            continue
        yield path, rel


def strip_markup(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"\[\[[^\]]*\]\]", " ", text)
    return text


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if len(w) >= 3 and w not in STOPWORDS]


# ---------------------------------------------------------------- search (lexical)

def cmd_search(query: str, limit: int, include_body: bool) -> int:
    terms = [t for t in tokenize(query)] or [query.lower()]
    results = []
    for path, rel in iter_notes():
        text = open(path, encoding="utf-8").read()
        fm, body = split_frontmatter(text)
        stem = os.path.splitext(os.path.basename(path))[0]
        title = (fm.get("title") or stem).lower()
        tags = fm.get("tags", "").lower()
        summary = fm.get("summary", "").lower()
        body_l = strip_markup(body).lower() if include_body else ""
        score = 0.0
        for t in terms:
            # Weighted: title hits dominate, then tags/summary, then body.
            score += 6 * title.count(t)
            score += 3 * tags.count(t)
            score += 2 * summary.count(t)
            if include_body:
                score += 1 * min(body_l.count(t), 5)  # cap body spam
        if score > 0:
            results.append((score, rel, fm.get("summary", "")))
    results.sort(key=lambda r: (-r[0], r[1]))
    if not results:
        print(f"no matches for: {query}")
        return 0
    for score, rel, summary in results[:limit]:
        print(f"  {score:5.0f}  {rel}")
        if summary:
            print(f"         {summary}")
    return 0


def ripgrep_available() -> bool:
    return shutil.which("rg") is not None


def cmd_search_rg(query: str, limit: int) -> int:
    """Fast path: ripgrep over the vault, frontmatter-aware ordering left to lexical."""
    try:
        out = subprocess.run(
            ["rg", "-i", "-l", "--glob", "*.md", "--glob", "!_meta/**", query, VAULT],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        return cmd_search(query, limit, include_body=True)
    files = [f for f in out.stdout.splitlines() if f.strip()]
    if not files:
        print(f"no matches for: {query}")
        return 0
    for f in files[:limit]:
        print(f"  {os.path.relpath(f, VAULT)}")
    return 0


# ---------------------------------------------------------------- digest

def build_digest() -> str:
    lines = ["# Digest", "",
             "_Auto-generated map of the vault (one line per note). "
             "Regenerate with `synapse digest`._", ""]
    by_dir: dict[str, list[str]] = {}
    for path, rel in iter_notes():
        fm, _ = split_frontmatter(open(path, encoding="utf-8").read())
        stem = os.path.splitext(os.path.basename(path))[0]
        folder = rel.split(os.sep)[0]
        tags = fm.get("tags", "").strip("[] ")
        summary = fm.get("summary", "").strip()
        line = f"- [[{stem}]]"
        if tags:
            line += f" · _{tags}_"
        if summary:
            line += f" — {summary}"
        by_dir.setdefault(folder, []).append(line)
    for folder in sorted(by_dir):
        lines.append(f"## {folder}")
        lines.append("")
        lines.extend(sorted(by_dir[folder]))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def cmd_digest(write: bool) -> int:
    content = build_digest()
    if write:
        open(DIGEST, "w", encoding="utf-8").write(content)
        n = content.count("\n- ")
        print(f"wrote {os.path.relpath(DIGEST, VAULT)} ({n} notes)")
    else:
        sys.stdout.write(content)
    return 0


# ---------------------------------------------------------------- index (pluggable)

def backend_name() -> str:
    return os.environ.get("SYNAPSE_RETRIEVAL_BACKEND", "tfidf").strip().lower()


def build_tfidf_index() -> dict:
    """Local, dependency-free 'semantic-ish' index: TF-IDF over note tokens.
    Good enough to rank by meaning-overlap without a model or a database."""
    docs = []
    for path, rel in iter_notes():
        fm, body = split_frontmatter(open(path, encoding="utf-8").read())
        stem = os.path.splitext(os.path.basename(path))[0]
        weighted = " ".join([
            (fm.get("title") or stem) + " ",
            (fm.get("tags", "") + " ") * 3,
            (fm.get("summary", "") + " ") * 2,
            strip_markup(body),
        ])
        docs.append((rel, Counter(tokenize(weighted))))
    df: Counter = Counter()
    for _, tf in docs:
        df.update(tf.keys())
    n = max(len(docs), 1)
    idf = {term: math.log((n + 1) / (cnt + 1)) + 1 for term, cnt in df.items()}
    index = {"backend": "tfidf", "n": n, "idf": idf, "docs": []}
    for rel, tf in docs:
        vec = {term: freq * idf[term] for term, freq in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        index["docs"].append({"rel": rel, "vec": {k: v / norm for k, v in vec.items()}})
    return index


def build_embeddings_index() -> dict | None:
    """Opt-in embeddings backend. Tries a local model; returns None (clean degrade)
    if the optional dependency/model is not installed — caller falls back to tfidf."""
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except Exception:
        print("search: embeddings backend requested but 'sentence-transformers' is not "
              "installed; falling back to the local tfidf backend.", file=sys.stderr)
        return None
    model_name = os.environ.get("SYNAPSE_EMBED_MODEL", "all-MiniLM-L6-v2")
    model = SentenceTransformer(model_name)
    index = {"backend": "embeddings", "model": model_name, "docs": []}
    for path, rel in iter_notes():
        fm, body = split_frontmatter(open(path, encoding="utf-8").read())
        stem = os.path.splitext(os.path.basename(path))[0]
        text = f"{fm.get('title') or stem}\n{fm.get('summary','')}\n{strip_markup(body)}"
        emb = model.encode(text, normalize_embeddings=True).tolist()
        index["docs"].append({"rel": rel, "emb": emb})
    return index


def cmd_index(backend: str) -> int:
    backend = backend or backend_name()
    index = None
    if backend == "embeddings":
        index = build_embeddings_index()
    if index is None:
        index = build_tfidf_index()
    json.dump(index, open(INDEX, "w", encoding="utf-8"))
    print(f"wrote {os.path.relpath(INDEX, VAULT)} "
          f"(backend={index['backend']}, {len(index['docs'])} notes)")
    return 0


def cosine(a: dict, b: dict) -> float:
    return sum(v * b.get(k, 0.0) for k, v in a.items())


def cmd_query(query: str, limit: int) -> int:
    if not os.path.isfile(INDEX):
        print("search: no index yet — run `synapse index` first "
              "(falling back to lexical search).", file=sys.stderr)
        return cmd_search(query, limit, include_body=True)
    index = json.load(open(INDEX, encoding="utf-8"))
    if index.get("backend") == "embeddings":
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            model = SentenceTransformer(index.get("model", "all-MiniLM-L6-v2"))
            q = model.encode(query, normalize_embeddings=True).tolist()
            scored = [(sum(qi * di for qi, di in zip(q, d["emb"])), d["rel"])
                      for d in index["docs"]]
        except Exception:
            print("search: embeddings model unavailable; rebuild with tfidf.", file=sys.stderr)
            return cmd_search(query, limit, include_body=True)
    else:
        idf = index["idf"]
        tf = Counter(tokenize(query))
        qvec = {t: f * idf.get(t, 1.0) for t, f in tf.items()}
        qnorm = math.sqrt(sum(v * v for v in qvec.values())) or 1.0
        qvec = {k: v / qnorm for k, v in qvec.items()}
        scored = [(cosine(qvec, d["vec"]), d["rel"]) for d in index["docs"]]
    scored.sort(reverse=True)
    hits = [(s, r) for s, r in scored if s > 0][:limit]
    if not hits:
        print(f"no matches for: {query}")
        return 0
    for s, rel in hits:
        print(f"  {s:5.3f}  {rel}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="search.py", add_help=True)
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("search")
    p.add_argument("query", nargs="+")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--body", action="store_true", help="also scan note bodies")
    p.add_argument("--rg", action="store_true", help="force ripgrep file listing")

    p = sub.add_parser("digest")
    p.add_argument("--write", action="store_true")

    p = sub.add_parser("index")
    p.add_argument("--backend", default="")

    p = sub.add_parser("query")
    p.add_argument("query", nargs="+")
    p.add_argument("--limit", type=int, default=10)

    args = ap.parse_args()
    if args.cmd == "search":
        q = " ".join(args.query)
        if args.rg and ripgrep_available():
            return cmd_search_rg(q, args.limit)
        return cmd_search(q, args.limit, include_body=args.body)
    if args.cmd == "digest":
        return cmd_digest(args.write)
    if args.cmd == "index":
        return cmd_index(args.backend)
    if args.cmd == "query":
        return cmd_query(" ".join(args.query), args.limit)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
