#!/usr/bin/env python3
"""LoCoMo retrieval benchmark for Synapse.

This measures the part of Synapse that can be evaluated *fully offline, with zero API
cost*: retrieval. It does NOT generate answers with an LLM (LoCoMo's answer-accuracy
track needs a model + judge). It asks a narrower, honest question:

    Given a long multi-session conversation as the "memory", does Synapse's retriever
    surface the gold evidence turn(s) for each question in the top-k?

We report recall@k and MRR, overall and per LoCoMo question category. The retriever
under test is the same lexical + TF-IDF approach used by `synapse search` / `synapse
index` (same tokenizer, same TF-IDF cosine). An optional embeddings backend is included
for comparison and degrades cleanly if sentence-transformers is not installed.

Dataset: snap-research/locomo, file `data/locomo10.json`.
    https://github.com/snap-research/locomo

Usage:
    python3 run_locomo.py --download                 # fetch locomo10.json next to this file
    python3 run_locomo.py --data locomo10.json
    python3 run_locomo.py --backends lexical tfidf
    python3 run_locomo.py --backends embeddings --embed-model all-MiniLM-L6-v2
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import urllib.request
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_URL = "https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json"
DEFAULT_DATA = os.path.join(HERE, "locomo10.json")
KS = (1, 3, 5, 10)

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
    print(f"downloading {DATA_URL} -> {path}")
    urllib.request.urlretrieve(DATA_URL, path)  # noqa: S310 (trusted dataset URL)


def load(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = [data]
    return data


def turns_of(sample: dict) -> list[tuple[str, str]]:
    """Return [(dia_id, text), ...] across all sessions of one conversation.
    LoCoMo stores sessions under conversation['session_N'] as lists of turn dicts,
    each with a 'dia_id' (e.g. 'D1:3'), a 'speaker', and 'text'."""
    conv = sample.get("conversation", sample)
    out: list[tuple[str, str]] = []
    for key in sorted(conv.keys(), key=_session_order):
        val = conv[key]
        if not isinstance(val, list):
            continue
        for turn in val:
            if not isinstance(turn, dict):
                continue
            dia = turn.get("dia_id") or turn.get("id")
            if not dia:
                continue
            text = turn.get("text") or turn.get("clean_text") or ""
            cap = turn.get("blip_caption") or turn.get("caption") or ""
            speaker = turn.get("speaker", "")
            out.append((dia, f"{speaker}: {text} {cap}".strip()))
    return out


def _session_order(key: str):
    m = re.search(r"(\d+)", key)
    return (0, int(m.group(1))) if m else (1, key)


def qa_of(sample: dict) -> list[dict]:
    items = []
    for qa in sample.get("qa", []):
        ev = qa.get("evidence") or []
        if not ev:                       # skip adversarial / unanswerable (no gold turn)
            continue
        items.append({
            "question": qa.get("question", ""),
            "evidence": [str(e) for e in ev],
            "category": qa.get("category", 0),
        })
    return items


# --- retrieval backends --------------------------------------------------------------

def rank_lexical(query: str, corpus: list[tuple[str, str]]) -> list[str]:
    """Count-based weighting, mirroring `synapse search` body scan (no frontmatter here)."""
    terms = tokenize(query) or [query.lower()]
    scored = []
    for dia, text in corpus:
        low = text.lower()
        score = sum(min(low.count(t), 5) for t in terms)
        if score:
            scored.append((score, dia))
    scored.sort(key=lambda r: (-r[0], r[1]))
    return [dia for _, dia in scored]


def build_tfidf(corpus: list[tuple[str, str]]):
    docs = [(dia, Counter(tokenize(text))) for dia, text in corpus]
    df: Counter = Counter()
    for _, tf in docs:
        df.update(tf.keys())
    n = max(len(docs), 1)
    idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}
    vecs = []
    for dia, tf in docs:
        v = {t: f * idf[t] for t, f in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append((dia, {k: x / norm for k, x in v.items()}))
    return idf, vecs


def rank_tfidf(query: str, idf, vecs) -> list[str]:
    tf = Counter(tokenize(query))
    q = {t: f * idf.get(t, 1.0) for t, f in tf.items()}
    norm = math.sqrt(sum(x * x for x in q.values())) or 1.0
    q = {k: x / norm for k, x in q.items()}
    scored = [(sum(qi * dv.get(k, 0.0) for k, qi in q.items()), dia) for dia, dv in vecs]
    scored.sort(key=lambda r: (-r[0], r[1]))
    return [dia for s, dia in scored if s > 0]


def build_embeddings(corpus, model_name):
    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        print("  (embeddings backend skipped: sentence-transformers not installed)",
              file=sys.stderr)
        return None
    model = SentenceTransformer(model_name)
    dias = [d for d, _ in corpus]
    embs = model.encode([t for _, t in corpus], normalize_embeddings=True,
                        show_progress_bar=False)
    return model, dias, embs


def rank_embeddings(query, bundle) -> list[str]:
    model, dias, embs = bundle
    q = model.encode(query, normalize_embeddings=True)
    scored = sorted(((float((q * e).sum()), d) for e, d in zip(embs, dias)), reverse=True)
    return [d for _, d in scored]


# --- metrics -------------------------------------------------------------------------

def evaluate(samples, backends, model_name):
    # acc[backend][k] = list of per-question recall@k (1.0 if any gold in top-k)
    recall = {b: {k: [] for k in KS} for b in backends}
    rr = {b: [] for b in backends}                       # reciprocal rank of first gold
    by_cat = {b: defaultdict(lambda: [[], []]) for b in backends}  # cat -> [recall@5, rr]
    total_q = 0

    for si, sample in enumerate(samples):
        corpus = turns_of(sample)
        qas = qa_of(sample)
        if not corpus or not qas:
            continue
        prebuilt = {}
        if "tfidf" in backends:
            prebuilt["tfidf"] = build_tfidf(corpus)
        if "embeddings" in backends:
            eb = build_embeddings(corpus, model_name)
            if eb is None:
                backends = [b for b in backends if b != "embeddings"]
                recall.pop("embeddings", None); rr.pop("embeddings", None)
                by_cat.pop("embeddings", None)
            else:
                prebuilt["embeddings"] = eb

        for qa in qas:
            total_q += 1
            gold = set(qa["evidence"])
            for b in backends:
                if b == "lexical":
                    ranked = rank_lexical(qa["question"], corpus)
                elif b == "tfidf":
                    ranked = rank_tfidf(qa["question"], *prebuilt["tfidf"])
                else:
                    ranked = rank_embeddings(qa["question"], prebuilt["embeddings"])
                # first-gold rank for MRR
                first = next((i + 1 for i, d in enumerate(ranked) if d in gold), None)
                rr_val = 1.0 / first if first else 0.0
                rr[b].append(rr_val)
                by_cat[b][qa["category"]][1].append(rr_val)
                for k in KS:
                    hit = 1.0 if any(d in gold for d in ranked[:k]) else 0.0
                    recall[b][k].append(hit)
                    if k == 5:
                        by_cat[b][qa["category"]][0].append(hit)
        print(f"  conv {si + 1}/{len(samples)}: {len(corpus)} turns, "
              f"{len(qas)} answerable questions", file=sys.stderr)

    return recall, rr, by_cat, total_q


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def report(recall, rr, by_cat, total_q):
    print(f"\nLoCoMo retrieval benchmark — {total_q} answerable questions")
    print("(metric = does the gold evidence turn appear in the top-k retrieved turns)\n")
    header = f"{'backend':<12}" + "".join(f"  R@{k:<5}" for k in KS) + f"  {'MRR':<6}"
    print(header)
    print("-" * len(header))
    for b in recall:
        row = f"{b:<12}"
        for k in KS:
            row += f"  {mean(recall[b][k]) * 100:5.1f}%"
        row += f"  {mean(rr[b]):.3f}"
        print(row)
    # per-category recall@5 for the strongest signal
    cats = sorted({c for b in by_cat for c in by_cat[b]})
    if cats:
        print("\nRecall@5 by LoCoMo category:")
        print(f"{'backend':<12}" + "".join(f"  cat{c:<4}" for c in cats))
        for b in by_cat:
            row = f"{b:<12}"
            for c in cats:
                row += f"  {mean(by_cat[b][c][0]) * 100:4.0f}%"
            print(row)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=DEFAULT_DATA, help="path to locomo10.json")
    ap.add_argument("--download", action="store_true", help="download the dataset if missing")
    ap.add_argument("--backends", nargs="+", default=["lexical", "tfidf"],
                    choices=["lexical", "tfidf", "embeddings"])
    ap.add_argument("--embed-model", default="all-MiniLM-L6-v2")
    args = ap.parse_args()

    if not os.path.isfile(args.data):
        if args.download:
            download(args.data)
        else:
            print(f"dataset not found: {args.data}\n"
                  f"run with --download, or fetch it from:\n  {DATA_URL}", file=sys.stderr)
            return 2

    samples = load(args.data)
    print(f"loaded {len(samples)} conversation(s) from {args.data}", file=sys.stderr)
    recall, rr, by_cat, total_q = evaluate(samples, list(args.backends), args.embed_model)
    if total_q == 0:
        print("no answerable questions found — check the dataset schema.", file=sys.stderr)
        return 1
    report(recall, rr, by_cat, total_q)
    return 0


if __name__ == "__main__":
    sys.exit(main())
