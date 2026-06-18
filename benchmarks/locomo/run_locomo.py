#!/usr/bin/env python3
"""LoCoMo retrieval benchmark for Synapse.

Measures the part of Synapse that can be evaluated *fully offline, at zero API cost*:
retrieval. It does NOT generate answers with an LLM (LoCoMo's answer-accuracy track needs
a model + judge). It asks a narrower, honest question:

    Given a long multi-session conversation as the "memory", does the retriever surface
    the gold evidence turn(s) for each question in the top-k?

Backends (all offline unless noted):
    lexical     count-based term matching (mirrors `synapse search` body scan)
    tfidf       TF-IDF cosine (same formulation as `synapse index`)
    bm25        Okapi BM25 — the standard strong lexical IR baseline
    embeddings  sentence-transformers cosine (opt-in; needs the library; degrades cleanly)

Metrics (overall + per LoCoMo category):
    Success@k   any gold evidence unit in the top-k          (a.k.a. hit rate)
    Recall@k    fraction of gold units retrieved in top-k    (matters for multi-evidence)
    nDCG@k      position-aware, graded by how many gold hits
    MRR         reciprocal rank of the first gold unit
Headline metric (nDCG@10) is reported with a 95% cluster-bootstrap CI over conversations.

Dataset: snap-research/locomo, file `data/locomo10.json`.
    https://github.com/snap-research/locomo

Usage:
    python3 run_locomo.py --download
    python3 run_locomo.py --data locomo10.json --backends lexical tfidf bm25
    python3 run_locomo.py --granularity session
    python3 run_locomo.py --backends bm25 embeddings --embed-model all-MiniLM-L6-v2
    python3 run_locomo.py --results results.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import platform
import random
import re
import statistics
import subprocess
import sys
import urllib.request
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_URL = "https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json"
DEFAULT_DATA = os.path.join(HERE, "locomo10.json")
KS = (1, 3, 5, 10)
BOOTSTRAP = 1000
SEED = 13

# --- tokenizer: identical to templates/vault/_meta/search.py (keep in sync) ----------
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "else", "for", "of", "to",
    "in", "on", "at", "by", "with", "as", "is", "are", "be", "was", "were", "this",
    "that", "these", "those", "it", "its", "into", "from", "when", "use", "used",
}


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [w for w in words if len(w) >= 3 and w not in STOPWORDS]


# --- dataset loading -----------------------------------------------------------------

def download(path: str) -> None:
    print(f"downloading {DATA_URL} -> {path}", file=sys.stderr)
    urllib.request.urlretrieve(DATA_URL, path)  # noqa: S310 (trusted dataset URL)


def load(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


def _session_order(key: str):
    m = re.search(r"(\d+)", key)
    return (0, int(m.group(1))) if m else (1, key)


def units_of(sample: dict, granularity: str) -> list[tuple[str, str, frozenset]]:
    """Return retrieval units as (unit_id, text, covered_dia_ids).

    granularity="turn":    one unit per dialogue turn (covers its own dia_id)
    granularity="session": one unit per session (covers every dia_id in the session)
    """
    conv = sample.get("conversation", sample)
    units: list[tuple[str, str, frozenset]] = []
    for key in sorted(conv.keys(), key=_session_order):
        val = conv[key]
        if not isinstance(val, list):
            continue
        turns = [t for t in val if isinstance(t, dict) and (t.get("dia_id") or t.get("id"))]
        if not turns:
            continue
        if granularity == "session":
            dia_ids, parts = [], []
            for t in turns:
                dia = t.get("dia_id") or t.get("id")
                dia_ids.append(dia)
                parts.append(f"{t.get('speaker','')}: {t.get('text') or ''} "
                             f"{t.get('blip_caption') or ''}".strip())
            units.append((key, "\n".join(parts), frozenset(dia_ids)))
        else:
            for t in turns:
                dia = t.get("dia_id") or t.get("id")
                text = f"{t.get('speaker','')}: {t.get('text') or ''} " \
                       f"{t.get('blip_caption') or ''}".strip()
                units.append((dia, text, frozenset({dia})))
    return units


def qa_of(sample: dict) -> list[dict]:
    items = []
    for qa in sample.get("qa", []):
        ev = qa.get("evidence") or []
        if not ev:
            continue                       # adversarial / unanswerable: no gold unit
        items.append({"question": qa.get("question", ""),
                      "evidence": frozenset(str(e) for e in ev),
                      "category": qa.get("category", 0)})
    return items


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


BACKENDS = {
    "lexical": (None, rank_lexical),
    "tfidf": (build_tfidf, rank_tfidf),
    "bm25": (build_bm25, rank_bm25),
    "embeddings": (build_embeddings, rank_embeddings),
}


# --- metrics -------------------------------------------------------------------------

def dcg(rels):
    return sum(r / math.log2(i + 2) for i, r in enumerate(rels))


def score_question(ranked, units, gold):
    """Return per-k dicts of success/recall/ndcg plus reciprocal rank."""
    covered = [units[i][2] for i in ranked]                 # covered dia_ids per ranked unit
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


def cluster_bootstrap_ci(values, conv_ids, iters=BOOTSTRAP, seed=SEED):
    """95% CI for the mean of `values`, resampling whole conversations (clusters)."""
    by_conv = defaultdict(list)
    for v, c in zip(values, conv_ids):
        by_conv[c].append(v)
    convs = list(by_conv)
    if len(convs) < 2:
        return (mean(values), mean(values))
    rng = random.Random(seed)
    means = []
    for _ in range(iters):
        pool = []
        for _ in range(len(convs)):
            pool.extend(by_conv[rng.choice(convs)])
        means.append(mean(pool))
    means.sort()
    lo = means[int(0.025 * iters)]
    hi = means[int(0.975 * iters)]
    return (lo, hi)


# --- evaluation ----------------------------------------------------------------------

def evaluate(samples, backends, granularity, embed_model):
    backends = [b for b in backends if b in BACKENDS]
    # per backend: metric name -> list over questions; plus shared conv_ids / categories
    rec = {b: {"success": defaultdict(list), "recall": defaultdict(list),
               "ndcg": defaultdict(list), "rr": []} for b in backends}
    conv_ids, cats = [], []
    total_q = 0

    for ci, sample in enumerate(samples):
        units = units_of(sample, granularity)
        qas = qa_of(sample)
        if not units or not qas:
            continue
        built = {}
        for b in list(backends):
            builder, _ = BACKENDS[b]
            if builder is None:                 # lexical ranks straight over the units
                built[b] = units
                continue
            model = builder(units, embed_model) if b == "embeddings" else builder(units)
            if b == "embeddings" and model is None:
                backends.remove(b); rec.pop(b, None)
            else:
                built[b] = model

        for qa in qas:
            total_q += 1
            conv_ids.append(ci)
            cats.append(qa["category"])
            for b in backends:
                _, ranker = BACKENDS[b]
                ranked = ranker(qa["question"], built[b])
                s = score_question(ranked, units, qa["evidence"])
                for k in KS:
                    rec[b]["success"][k].append(s["success"][k])
                    rec[b]["recall"][k].append(s["recall"][k])
                    rec[b]["ndcg"][k].append(s["ndcg"][k])
                rec[b]["rr"].append(s["rr"])
        print(f"  conv {ci + 1}/{len(samples)}: {len(units)} units ({granularity}), "
              f"{len(qas)} answerable questions", file=sys.stderr)

    return rec, conv_ids, cats, total_q, backends


def report(rec, conv_ids, cats, total_q, backends, granularity):
    print(f"\nLoCoMo retrieval benchmark — {total_q} answerable questions, "
          f"granularity={granularity}")
    print("(does the gold evidence appear in the top-k retrieved units?)\n")
    cols = ["S@1", "S@5", "S@10", "R@5", "R@10", "nDCG@10", "MRR"]
    print(f"{'backend':<11}" + "".join(f"{c:>9}" for c in cols))
    print("-" * (11 + 9 * len(cols)))
    for b in backends:
        r = rec[b]
        vals = [mean(r["success"][1]), mean(r["success"][5]), mean(r["success"][10]),
                mean(r["recall"][5]), mean(r["recall"][10]), mean(r["ndcg"][10])]
        row = f"{b:<11}" + "".join(f"{v*100:8.1f}%" for v in vals)
        row += f"{mean(r['rr']):9.3f}"
        print(row)

    print("\nnDCG@10 with 95% cluster-bootstrap CI (resampled over conversations):")
    for b in backends:
        m = mean(rec[b]["ndcg"][10])
        lo, hi = cluster_bootstrap_ci(rec[b]["ndcg"][10], conv_ids)
        print(f"  {b:<11} {m*100:5.1f}%   [{lo*100:.1f}%, {hi*100:.1f}%]")

    cat_set = sorted(set(cats))
    print("\nRecall@5 by LoCoMo category:")
    print(f"{'backend':<11}" + "".join(f"  cat{c:<4}" for c in cat_set))
    for b in backends:
        by = defaultdict(list)
        for v, c in zip(rec[b]["recall"][5], cats):
            by[c].append(v)
        row = f"{b:<11}" + "".join(f"  {mean(by[c])*100:4.0f}%" for c in cat_set)
        print(row)


def build_results(rec, conv_ids, cats, total_q, backends, granularity, data_path):
    def sha256(p):
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=HERE,
                                capture_output=True, text=True).stdout.strip() or None
    except Exception:
        commit = None

    out = {
        "meta": {
            "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "dataset": os.path.basename(data_path),
            "dataset_sha256": sha256(data_path),
            "n_conversations": len(set(conv_ids)),
            "n_questions": total_q,
            "granularity": granularity,
            "backends": backends,
            "metric_definitions": {
                "success@k": "any gold evidence unit in top-k",
                "recall@k": "fraction of gold units retrieved in top-k",
                "ndcg@k": "position-aware, binary relevance per unit",
                "mrr": "reciprocal rank of first gold unit",
            },
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
        lo, hi = cluster_bootstrap_ci(r["ndcg"][10], conv_ids)
        out["results"][b] = {
            "success_at": {k: mean(r["success"][k]) for k in KS},
            "recall_at": {k: mean(r["recall"][k]) for k in KS},
            "ndcg_at": {k: mean(r["ndcg"][k]) for k in KS},
            "mrr": mean(r["rr"]),
            "ndcg10_ci95": [lo, hi],
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=DEFAULT_DATA)
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--backends", nargs="+", default=["lexical", "tfidf", "bm25"],
                    choices=list(BACKENDS))
    ap.add_argument("--granularity", default="turn", choices=["turn", "session"])
    ap.add_argument("--embed-model", default="all-MiniLM-L6-v2")
    ap.add_argument("--results", default="", help="write a results.json with metadata")
    args = ap.parse_args()

    if not os.path.isfile(args.data):
        if args.download:
            download(args.data)
        else:
            print(f"dataset not found: {args.data}\nrun with --download, or fetch:\n"
                  f"  {DATA_URL}", file=sys.stderr)
            return 2

    samples = load(args.data)
    print(f"loaded {len(samples)} conversation(s) from {args.data}", file=sys.stderr)
    rec, conv_ids, cats, total_q, backends = evaluate(
        samples, list(args.backends), args.granularity, args.embed_model)
    if total_q == 0:
        print("no answerable questions found — check the dataset schema.", file=sys.stderr)
        return 1
    report(rec, conv_ids, cats, total_q, backends, args.granularity)
    if args.results:
        res = build_results(rec, conv_ids, cats, total_q, backends, args.granularity, args.data)
        json.dump(res, open(args.results, "w", encoding="utf-8"), indent=2)
        print(f"\nwrote {args.results}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
