#!/usr/bin/env python3
"""Shared, dataset-agnostic retrieval evaluation engine for Synapse benchmarks.

A dataset runner (e.g. run_locomo.py, run_longmemeval.py) turns its data into a list of
"prepared" samples, each a pair:

    units: list[(unit_id, text, covered_ids)]   # retrievable units; covered_ids = frozenset
    qas:   list[{question, evidence(frozenset), category}]

and calls `evaluate(...)` then `report(...)` / `build_results(...)`. This module owns the
retrieval backends, the metrics, and the statistics so every dataset is scored identically.

Backends (offline unless noted):
    lexical     count-based term matching (mirrors `synapse search` body scan)
    tfidf       TF-IDF cosine (same formulation as `synapse index`)
    bm25        Okapi BM25 — standard strong lexical IR baseline
    embeddings  sentence-transformers cosine (opt-in; degrades cleanly if missing)

Metrics: Success@k, Recall@k (multi-evidence), nDCG@k, MRR. Headline nDCG@10 carries a
95% cluster-bootstrap CI resampled over samples (conversations/questions).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import math
import os
import platform
import random
import re
import subprocess
import sys
from collections import Counter, defaultdict

KS = (1, 3, 5, 10)
BOOTSTRAP = 1000
SEED = 13

# --- tokenizer: import the canonical one from the shipped retriever so the benchmark
# scores exactly what `synapse index/query` runs. Falls back to an inline copy if the
# template tree isn't reachable (e.g. the harness is vendored elsewhere). -------------
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "templates", "vault", "_meta"))
    from search import STOPWORDS, tokenize  # type: ignore  # noqa: E402,F401
except Exception:
    STOPWORDS = {
        "the", "a", "an", "and", "or", "but", "if", "then", "else", "for", "of", "to",
        "in", "on", "at", "by", "with", "as", "is", "are", "be", "was", "were", "this",
        "that", "these", "those", "it", "its", "into", "from", "when", "use", "used",
    }

    def tokenize(text: str) -> list[str]:
        words = re.findall(r"[a-z0-9]+", (text or "").lower())
        return [w for w in words if len(w) >= 3 and w not in STOPWORDS]


# --- retrieval backends: each returns a ranked list of unit indices ------------------

def rank_lexical(query, units):
    terms = tokenize(query) or [query.lower()]
    scored = []
    for i, (_, text, _) in enumerate(units):
        low = text.lower()
        s = sum(min(low.count(t), 5) for t in terms)
        if s:
            scored.append((s, i))
    scored.sort(key=lambda r: (-r[0], r[1]))
    return [i for _, i in scored]


def build_tfidf(units):
    docs = [Counter(tokenize(t)) for _, t, _ in units]
    df = Counter()
    for tf in docs:
        df.update(tf.keys())
    n = max(len(docs), 1)
    idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}
    vecs = []
    for tf in docs:
        v = {t: f * idf[t] for t, f in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append({k: x / norm for k, x in v.items()})
    return idf, vecs


def rank_tfidf(query, model):
    idf, vecs = model
    tf = Counter(tokenize(query))
    q = {t: f * idf.get(t, 1.0) for t, f in tf.items()}
    norm = math.sqrt(sum(x * x for x in q.values())) or 1.0
    q = {k: x / norm for k, x in q.items()}
    scored = [(sum(qi * dv.get(k, 0.0) for k, qi in q.items()), i) for i, dv in enumerate(vecs)]
    scored.sort(key=lambda r: (-r[0], r[1]))
    return [i for s, i in scored if s > 0]


def build_bm25(units, k1=1.5, b=0.75):
    docs = [tokenize(t) for _, t, _ in units]
    tfs = [Counter(d) for d in docs]
    lens = [len(d) for d in docs]
    n = max(len(docs), 1)
    avgdl = (sum(lens) / n) if n else 0.0
    df = Counter()
    for tf in tfs:
        df.update(tf.keys())
    idf = {t: math.log((n - c + 0.5) / (c + 0.5) + 1.0) for t, c in df.items()}
    return tfs, lens, avgdl, idf, k1, b


def rank_bm25(query, model):
    tfs, lens, avgdl, idf, k1, b = model
    qterms = set(tokenize(query))
    scored = []
    for i, tf in enumerate(tfs):
        dl = lens[i] or 1
        s = 0.0
        for t in qterms:
            f = tf.get(t)
            if not f:
                continue
            s += idf.get(t, 0.0) * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / (avgdl or 1)))
        if s > 0:
            scored.append((s, i))
    scored.sort(key=lambda r: (-r[0], r[1]))
    return [i for _, i in scored]


def build_embeddings(units, model_name):
    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        print("  (embeddings backend skipped: sentence-transformers not installed)",
              file=sys.stderr)
        return None
    model = SentenceTransformer(model_name)
    embs = model.encode([t for _, t, _ in units], normalize_embeddings=True,
                        show_progress_bar=False)
    return model, embs


def rank_embeddings(query, model):
    m, embs = model
    q = m.encode(query, normalize_embeddings=True)
    scored = sorted(((float((q * e).sum()), i) for i, e in enumerate(embs)), reverse=True)
    return [i for _, i in scored]


def rank_hybrid(query, model):
    """Reciprocal rank fusion of BM25 and embeddings (RRF, k=60)."""
    bm25_model, emb_model = model
    fused = defaultdict(float)
    for ranker, m in ((rank_bm25, bm25_model), (rank_embeddings, emb_model)):
        for rank, idx in enumerate(ranker(query, m)):
            fused[idx] += 1.0 / (60 + rank + 1)
    return [i for i, _ in sorted(fused.items(), key=lambda r: -r[1])]


def build_hybrid(units, model_name):
    emb = build_embeddings(units, model_name)
    if emb is None:
        return None
    return build_bm25(units), emb


# builder, ranker, needs_model_name
BACKENDS = {
    "lexical": (None, rank_lexical, False),
    "tfidf": (build_tfidf, rank_tfidf, False),
    "bm25": (build_bm25, rank_bm25, False),
    "embeddings": (build_embeddings, rank_embeddings, True),
    "hybrid": (build_hybrid, rank_hybrid, True),
}


# --- metrics -------------------------------------------------------------------------

def dcg(rels):
    return sum(r / math.log2(i + 2) for i, r in enumerate(rels))


def score_question(ranked, units, gold):
    covered = [units[i][2] for i in ranked]
    rels = [1 if (c & gold) else 0 for c in covered]
    out = {"success": {}, "recall": {}, "ndcg": {}}
    n_gold = len(gold)
    n_rel = sum(1 for c in covered if c & gold)
    first = next((r + 1 for r, x in enumerate(rels) if x), None)
    out["rr"] = 1.0 / first if first else 0.0
    for k in KS:
        topk = covered[:k]
        found = set().union(*topk) & gold if topk else set()
        out["success"][k] = 1.0 if found else 0.0
        out["recall"][k] = len(found) / n_gold if n_gold else 0.0
        ideal = dcg([1] * min(n_rel, k)) or 1.0
        out["ndcg"][k] = dcg(rels[:k]) / ideal
    return out


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def cluster_bootstrap_ci(values, group_ids, iters=BOOTSTRAP, seed=SEED):
    by_group = defaultdict(list)
    for v, g in zip(values, group_ids):
        by_group[g].append(v)
    groups = list(by_group)
    if len(groups) < 2:
        return (mean(values), mean(values))
    rng = random.Random(seed)
    means = []
    for _ in range(iters):
        pool = []
        for _ in range(len(groups)):
            pool.extend(by_group[rng.choice(groups)])
        means.append(mean(pool))
    means.sort()
    return (means[int(0.025 * iters)], means[int(0.975 * iters)])


# --- evaluation ----------------------------------------------------------------------

def evaluate(prepared, backends, embed_model, granularity_label=""):
    """prepared: iterable of (units, qas). Returns (rec, group_ids, cats, total_q, backends)."""
    backends = [b for b in backends if b in BACKENDS]
    rec = {b: {"success": defaultdict(list), "recall": defaultdict(list),
               "ndcg": defaultdict(list), "rr": []} for b in backends}
    group_ids, cats = [], []
    total_q = 0
    prepared = list(prepared)

    for gi, (units, qas) in enumerate(prepared):
        if not units or not qas:
            continue
        # Encode embeddings at most once per sample, even if both 'embeddings' and
        # 'hybrid' are requested (encoding is the expensive part).
        shared_emb = None
        if any(b in ("embeddings", "hybrid") for b in backends):
            shared_emb = build_embeddings(units, embed_model)
            if shared_emb is None:               # library/model unavailable
                for b in ("embeddings", "hybrid"):
                    if b in backends:
                        backends.remove(b); rec.pop(b, None)
        built = {}
        for b in backends:
            if b == "lexical":
                built[b] = units
            elif b == "tfidf":
                built[b] = build_tfidf(units)
            elif b == "bm25":
                built[b] = build_bm25(units)
            elif b == "embeddings":
                built[b] = shared_emb
            elif b == "hybrid":
                built[b] = (build_bm25(units), shared_emb)
        for qa in qas:
            total_q += 1
            group_ids.append(gi)
            cats.append(qa.get("category", 0))
            for b in backends:
                _, ranker, _ = BACKENDS[b]
                s = score_question(ranker(qa["question"], built[b]), units, qa["evidence"])
                for k in KS:
                    rec[b]["success"][k].append(s["success"][k])
                    rec[b]["recall"][k].append(s["recall"][k])
                    rec[b]["ndcg"][k].append(s["ndcg"][k])
                rec[b]["rr"].append(s["rr"])
        print(f"  sample {gi + 1}/{len(prepared)}: {len(units)} units"
              f"{(' ' + granularity_label) if granularity_label else ''}, "
              f"{len(qas)} answerable question(s)", file=sys.stderr)
    return rec, group_ids, cats, total_q, backends


def report(rec, group_ids, cats, total_q, backends, granularity, dataset):
    print(f"\n{dataset} retrieval benchmark — {total_q} answerable questions, "
          f"granularity={granularity}")
    print("(does the gold evidence appear in the top-k retrieved units?)\n")
    cols = ["S@1", "S@5", "S@10", "R@5", "R@10", "nDCG@10", "MRR"]
    print(f"{'backend':<11}" + "".join(f"{c:>9}" for c in cols))
    print("-" * (11 + 9 * len(cols)))
    for b in backends:
        r = rec[b]
        vals = [mean(r["success"][1]), mean(r["success"][5]), mean(r["success"][10]),
                mean(r["recall"][5]), mean(r["recall"][10]), mean(r["ndcg"][10])]
        print(f"{b:<11}" + "".join(f"{v*100:8.1f}%" for v in vals) + f"{mean(r['rr']):9.3f}")

    print("\nnDCG@10 with 95% cluster-bootstrap CI:")
    for b in backends:
        m = mean(rec[b]["ndcg"][10])
        lo, hi = cluster_bootstrap_ci(rec[b]["ndcg"][10], group_ids)
        print(f"  {b:<11} {m*100:5.1f}%   [{lo*100:.1f}%, {hi*100:.1f}%]")

    cat_set = sorted(set(cats), key=str)
    print("\nRecall@5 by category:")
    print(f"{'backend':<11}" + "".join(f"  {str(c)[:8]:<8}" for c in cat_set))
    for b in backends:
        by = defaultdict(list)
        for v, c in zip(rec[b]["recall"][5], cats):
            by[c].append(v)
        print(f"{b:<11}" + "".join(f"  {mean(by[c])*100:4.0f}%   " for c in cat_set))


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_results(rec, group_ids, total_q, backends, granularity, dataset, data_path):
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                cwd=os.path.dirname(os.path.abspath(data_path)) or ".",
                                capture_output=True, text=True).stdout.strip() or None
    except Exception:
        commit = None
    out = {
        "meta": {
            "dataset": dataset,
            "data_file": os.path.basename(data_path),
            "data_sha256": _sha256(data_path),
            "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "n_samples": len(set(group_ids)),
            "n_questions": total_q,
            "granularity": granularity,
            "backends": backends,
            "bootstrap_iters": BOOTSTRAP,
            "seed": SEED,
            "python": platform.python_version(),
            "harness_commit": commit,
            "track": "retrieval-only (no LLM answer generation)",
        },
        "results": {},
    }
    for b in backends:
        r = rec[b]
        lo, hi = cluster_bootstrap_ci(r["ndcg"][10], group_ids)
        out["results"][b] = {
            "success_at": {k: mean(r["success"][k]) for k in KS},
            "recall_at": {k: mean(r["recall"][k]) for k in KS},
            "ndcg_at": {k: mean(r["ndcg"][k]) for k in KS},
            "mrr": mean(r["rr"]),
            "ndcg10_ci95": [lo, hi],
        }
    return out
