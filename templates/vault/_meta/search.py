#!/usr/bin/env python3
"""Optional retrieval layer for the vault — file-based, no database.

The vault works without this: agents walk `index.md` + `[[wikilinks]]`. When a vault
grows past what fits comfortably in context, this gives the agent a fast way to *find*
the few relevant notes instead of reading everything.

Three levels, smallest dependency first:

  search   lexical search over frontmatter (title/tags/summary, weighted) + body,
           with optional --tag/--title/--exact filters.
           Uses ripgrep if present, else a pure-stdlib scan. Zero new deps.
  digest   regenerate `_meta/digest.md`: one compact line per note
           (stem · category · tags · summary) — a map the agent reads in Phase 0.
  index    build an optional retrieval index for a pluggable backend
           (default: local BM25 in `_meta/retrieval.json` — the strongest lexical
           ranker, matching the published benchmark). TF-IDF stays available via
           `--backend tfidf`; embeddings are opt-in via $SYNAPSE_RETRIEVAL_BACKEND
           and degrade cleanly to BM25 if the model isn't installed.

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
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict

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

def cmd_search(query: str, limit: int, include_body: bool,
               tag: str = "", title: str = "", exact: bool = False) -> int:
    # --exact treats the query as a literal substring; otherwise tokenize.
    if exact:
        terms = [query.lower().strip()] if query.strip() else []
    else:
        terms = tokenize(query) if query.strip() else []
    tag_f = tag.lower().strip()
    title_f = title.lower().strip()
    results = []
    for path, rel in iter_notes():
        text = open(path, encoding="utf-8").read()
        fm, body = split_frontmatter(text)
        stem = os.path.splitext(os.path.basename(path))[0]
        title_l = (fm.get("title") or stem).lower()
        tags_l = fm.get("tags", "").lower()
        summary_l = fm.get("summary", "").lower()
        # Frontmatter filters narrow the candidate set before scoring.
        if tag_f and tag_f not in tags_l:
            continue
        if title_f and title_f not in title_l:
            continue
        body_l = strip_markup(body).lower() if include_body else ""
        if not terms:
            score = 1.0  # filter-only search (e.g. --tag security): list matches
        else:
            score = 0.0
            for t in terms:
                # Weighted: title hits dominate, then tags/summary, then body.
                score += 6 * title_l.count(t)
                score += 3 * tags_l.count(t)
                score += 2 * summary_l.count(t)
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
    return os.environ.get("SYNAPSE_RETRIEVAL_BACKEND", "bm25").strip().lower()


def weighted_tokens(fm: dict, body: str, stem: str) -> list[str]:
    """Tokens for indexing, weighting frontmatter over body (title/tags/summary
    repeated). Shared by the BM25 and TF-IDF index builders so they rank alike."""
    weighted = " ".join([
        (fm.get("title") or stem) + " ",
        (fm.get("tags", "") + " ") * 3,
        (fm.get("summary", "") + " ") * 2,
        strip_markup(body),
    ])
    return tokenize(weighted)


def build_bm25_index(k1: float = 1.5, b: float = 0.75) -> dict:
    """Local, dependency-free Okapi BM25 index — the default and strongest lexical
    backend. Mirrors benchmarks/retrieval_eval.py so what ships == what's measured."""
    docs = []  # (rel, token list)
    for path, rel in iter_notes():
        fm, body = split_frontmatter(open(path, encoding="utf-8").read())
        stem = os.path.splitext(os.path.basename(path))[0]
        docs.append((rel, weighted_tokens(fm, body, stem)))
    tfs = [Counter(toks) for _, toks in docs]
    lens = [len(toks) for _, toks in docs]
    n = max(len(docs), 1)
    avgdl = (sum(lens) / n) if n else 0.0
    df: Counter = Counter()
    for tf in tfs:
        df.update(tf.keys())
    idf = {t: math.log((n - c + 0.5) / (c + 0.5) + 1.0) for t, c in df.items()}
    index = {"backend": "bm25", "n": n, "avgdl": avgdl, "k1": k1, "b": b,
             "idf": idf, "docs": []}
    for (rel, _), tf, dl in zip(docs, tfs, lens):
        index["docs"].append({"rel": rel, "tf": dict(tf), "len": dl})
    return index


def build_tfidf_index() -> dict:
    """Local, dependency-free 'semantic-ish' index: TF-IDF over note tokens.
    Good enough to rank by meaning-overlap without a model or a database."""
    docs = []
    for path, rel in iter_notes():
        fm, body = split_frontmatter(open(path, encoding="utf-8").read())
        stem = os.path.splitext(os.path.basename(path))[0]
        docs.append((rel, Counter(weighted_tokens(fm, body, stem))))
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


def _load_st_model(model_name: str):
    """Load a sentence-transformers model, or return None (clean degrade) if the
    optional dependency / model isn't available."""
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except Exception:
        return None
    try:
        return SentenceTransformer(model_name)
    except Exception:
        return None


def note_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def chunk_note(fm: dict, body: str, stem: str,
               max_words: int = 160, overlap: int = 20) -> list[str]:
    """Split a note into overlapping windows for embedding. Each chunk is prefixed
    with the note's title+summary so it carries context even in isolation. Embedding
    chunks (not the whole note) stops long notes from diluting into one vague vector."""
    header = " ".join(x for x in [(fm.get("title") or stem), fm.get("summary", "")] if x).strip()
    words = strip_markup(body).split()
    if not words:
        return [header or (fm.get("title") or stem)]
    step = max(max_words - overlap, 1)
    chunks = []
    for i in range(0, len(words), step):
        window = " ".join(words[i:i + max_words])
        chunks.append(f"{header}\n{window}" if header else window)
        if i + max_words >= len(words):
            break
    return chunks or [header]


def _prev_embeddings_map(model_name: str) -> dict:
    """Map rel -> previously embedded doc (with hash + chunks) from the existing
    index, so unchanged notes can be reused instead of re-encoded. Works whether the
    prior index was 'embeddings' or 'hybrid'; empty if model changed or none exists."""
    if not os.path.isfile(INDEX):
        return {}
    try:
        prev = json.load(open(INDEX, encoding="utf-8"))
    except Exception:
        return {}
    if prev.get("backend") == "embeddings":
        sub = prev
    elif prev.get("backend") == "hybrid":
        sub = prev.get("embeddings", {})
    else:
        return {}
    if sub.get("model") != model_name:
        return {}
    return {d["rel"]: d for d in sub.get("docs", [])}


def build_embeddings_index() -> dict | None:
    """Opt-in embeddings backend, chunked + incremental. Returns None (clean degrade)
    if 'sentence-transformers'/the model isn't installed — caller falls back to bm25."""
    model_name = os.environ.get("SYNAPSE_EMBED_MODEL", "all-MiniLM-L6-v2")
    model = _load_st_model(model_name)
    if model is None:
        print("search: embeddings backend requested but 'sentence-transformers'/the model "
              "is not available; falling back to the local bm25 backend.", file=sys.stderr)
        return None
    prev = _prev_embeddings_map(model_name)
    index = {"backend": "embeddings", "model": model_name, "docs": []}
    reused = encoded = 0
    for path, rel in iter_notes():
        raw = open(path, encoding="utf-8").read()
        h = note_hash(raw)
        cached = prev.get(rel)
        if cached and cached.get("hash") == h and cached.get("chunks"):
            index["docs"].append({"rel": rel, "hash": h, "chunks": cached["chunks"]})
            reused += 1
            continue
        fm, body = split_frontmatter(raw)
        stem = os.path.splitext(os.path.basename(path))[0]
        embs = model.encode(chunk_note(fm, body, stem), normalize_embeddings=True)
        index["docs"].append({"rel": rel, "hash": h, "chunks": [e.tolist() for e in embs]})
        encoded += 1
    index["_stats"] = {"reused": reused, "encoded": encoded}
    return index


def build_hybrid_index() -> dict | None:
    """Hybrid backend: BM25 + embeddings, fused at query time with reciprocal rank
    fusion. Needs embeddings; returns None (caller degrades to bm25) if unavailable."""
    emb = build_embeddings_index()
    if emb is None:
        return None
    return {"backend": "hybrid", "model": emb["model"],
            "bm25": build_bm25_index(), "embeddings": emb}


def _doc_count(index: dict) -> int:
    if "docs" in index:
        return len(index["docs"])
    if index.get("backend") == "hybrid":
        return len(index["bm25"]["docs"])
    return 0


def cmd_index(backend: str) -> int:
    backend = backend or backend_name()
    index = None
    if backend == "embeddings":
        index = build_embeddings_index()  # None -> clean fallback to bm25 below
    elif backend == "hybrid":
        index = build_hybrid_index()
    if index is None:
        index = build_tfidf_index() if backend == "tfidf" else build_bm25_index()
    json.dump(index, open(INDEX, "w", encoding="utf-8"))
    stats = index.get("_stats") or index.get("embeddings", {}).get("_stats")
    extra = f", reused {stats['reused']} / encoded {stats['encoded']}" if stats else ""
    print(f"wrote {os.path.relpath(INDEX, VAULT)} "
          f"(backend={index['backend']}, {_doc_count(index)} notes{extra})")
    return 0


def cosine(a: dict, b: dict) -> float:
    return sum(v * b.get(k, 0.0) for k, v in a.items())


def _bm25_scored(index: dict, query: str) -> list[tuple[float, str]]:
    idf = index["idf"]
    avgdl = index.get("avgdl") or 1.0
    k1, b = index.get("k1", 1.5), index.get("b", 0.75)
    qterms = set(tokenize(query))
    scored = []
    for d in index["docs"]:
        tf, dl = d["tf"], (d.get("len") or 1)
        s = 0.0
        for t in qterms:
            f = tf.get(t)
            if not f:
                continue
            s += idf.get(t, 0.0) * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / avgdl))
        if s > 0:
            scored.append((s, d["rel"]))
    scored.sort(key=lambda r: (-r[0], r[1]))
    return scored


def _tfidf_scored(index: dict, query: str) -> list[tuple[float, str]]:
    idf = index["idf"]
    tf = Counter(tokenize(query))
    qvec = {t: f * idf.get(t, 1.0) for t, f in tf.items()}
    qnorm = math.sqrt(sum(v * v for v in qvec.values())) or 1.0
    qvec = {k: v / qnorm for k, v in qvec.items()}
    scored = [(cosine(qvec, d["vec"]), d["rel"]) for d in index["docs"]]
    scored = [(s, r) for s, r in scored if s > 0]
    scored.sort(key=lambda r: (-r[0], r[1]))
    return scored


def _embeddings_scored(index: dict, query: str) -> list[tuple[float, str]] | None:
    """Score notes by their best-matching chunk. None if the model is unavailable."""
    model = _load_st_model(index.get("model", "all-MiniLM-L6-v2"))
    if model is None:
        return None
    q = model.encode(query, normalize_embeddings=True)
    scored = []
    for d in index["docs"]:
        chunks = d.get("chunks")
        if chunks is None and "emb" in d:        # backward-compat: single-vector notes
            chunks = [d["emb"]]
        best = max((sum(qi * ci for qi, ci in zip(q, emb)) for emb in (chunks or [])),
                   default=0.0)
        if best > 0:
            scored.append((float(best), d["rel"]))
    scored.sort(key=lambda r: (-r[0], r[1]))
    return scored


def _rrf(rank_lists: list[list[str]], k: int = 60) -> list[tuple[float, str]]:
    """Reciprocal rank fusion: combine several ranked rel-lists into one ordering."""
    fused: dict[str, float] = defaultdict(float)
    for ranked in rank_lists:
        for pos, rel in enumerate(ranked):
            fused[rel] += 1.0 / (k + pos + 1)
    return sorted(((s, rel) for rel, s in fused.items()), key=lambda r: (-r[0], r[1]))


def _hybrid_scored(index: dict, query: str) -> list[tuple[float, str]]:
    bm = _bm25_scored(index["bm25"], query)
    em = _embeddings_scored(index["embeddings"], query)
    if em is None:                               # model vanished since indexing
        return bm
    return _rrf([[rel for _, rel in bm], [rel for _, rel in em]])


def cmd_query(query: str, limit: int) -> int:
    if not os.path.isfile(INDEX):
        print("search: no index yet — run `synapse index` first "
              "(falling back to lexical search).", file=sys.stderr)
        return cmd_search(query, limit, include_body=True)
    index = json.load(open(INDEX, encoding="utf-8"))
    backend = index.get("backend")
    if backend == "embeddings":
        scored = _embeddings_scored(index, query)
        if scored is None:
            print("search: embeddings model unavailable; rebuild with bm25.", file=sys.stderr)
            return cmd_search(query, limit, include_body=True)
    elif backend == "hybrid":
        scored = _hybrid_scored(index, query)
    elif backend == "bm25":
        scored = _bm25_scored(index, query)
    else:  # tfidf
        scored = _tfidf_scored(index, query)
    hits = scored[:limit]
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
    p.add_argument("query", nargs="*")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--body", action="store_true", help="also scan note bodies")
    p.add_argument("--rg", action="store_true", help="force ripgrep file listing")
    p.add_argument("--tag", default="", help="only notes whose tags contain this")
    p.add_argument("--title", default="", help="only notes whose title contains this")
    p.add_argument("--exact", action="store_true", help="literal substring (no tokenizing)")

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
        if not q and not args.tag and not args.title:
            print("usage: search <query> [--tag T] [--title T] [--exact] [--body]",
                  file=sys.stderr)
            return 2
        if args.rg and q and not args.tag and not args.title and ripgrep_available():
            return cmd_search_rg(q, args.limit)
        return cmd_search(q, args.limit, include_body=args.body,
                          tag=args.tag, title=args.title, exact=args.exact)
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
