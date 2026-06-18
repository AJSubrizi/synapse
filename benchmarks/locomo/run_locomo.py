#!/usr/bin/env python3
"""LoCoMo retrieval benchmark for Synapse (offline, zero API cost).

Measures retrieval only: given a long multi-session conversation as the "memory", does
the retriever surface the gold evidence turn(s) for each question in the top-k? It does
NOT generate answers with an LLM (that track needs a model + judge).

The retrieval backends, metrics, and statistics live in ../retrieval_eval.py and are
shared with the LongMemEval harness so both datasets are scored identically.

Dataset: snap-research/locomo, file data/locomo10.json — https://github.com/snap-research/locomo

Usage:
    python3 run_locomo.py --download
    python3 run_locomo.py --backends lexical tfidf bm25 --results results.json
    python3 run_locomo.py --granularity session
    python3 run_locomo.py --backends bm25 embeddings hybrid
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import retrieval_eval as re_eval  # noqa: E402

DATA_URL = "https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json"
DEFAULT_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locomo10.json")


def _session_order(key: str):
    m = re.search(r"(\d+)", key)
    return (0, int(m.group(1))) if m else (1, key)


def units_of(sample, granularity):
    conv = sample.get("conversation", sample)
    units = []
    for key in sorted(conv.keys(), key=_session_order):
        val = conv[key]
        if not isinstance(val, list):
            continue
        turns = [t for t in val if isinstance(t, dict) and (t.get("dia_id") or t.get("id"))]
        if not turns:
            continue
        if granularity == "session":
            dias, parts = [], []
            for t in turns:
                dias.append(t.get("dia_id") or t.get("id"))
                parts.append(f"{t.get('speaker','')}: {t.get('text') or ''} "
                             f"{t.get('blip_caption') or ''}".strip())
            units.append((key, "\n".join(parts), frozenset(dias)))
        else:
            for t in turns:
                dia = t.get("dia_id") or t.get("id")
                units.append((dia, f"{t.get('speaker','')}: {t.get('text') or ''} "
                                   f"{t.get('blip_caption') or ''}".strip(), frozenset({dia})))
    return units


def qa_of(sample):
    out = []
    for qa in sample.get("qa", []):
        ev = qa.get("evidence") or []
        if not ev:
            continue
        out.append({"question": qa.get("question", ""),
                    "evidence": frozenset(str(e) for e in ev),
                    "category": qa.get("category", 0)})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=DEFAULT_DATA)
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--backends", nargs="+", default=["lexical", "tfidf", "bm25"],
                    choices=list(re_eval.BACKENDS))
    ap.add_argument("--granularity", default="turn", choices=["turn", "session"])
    ap.add_argument("--embed-model", default="all-MiniLM-L6-v2")
    ap.add_argument("--limit", type=int, default=0,
                    help="only evaluate the first N conversations (quick smoke run)")
    ap.add_argument("--results", default="")
    args = ap.parse_args()

    if not os.path.isfile(args.data):
        if args.download:
            print(f"downloading {DATA_URL}", file=sys.stderr)
            urllib.request.urlretrieve(DATA_URL, args.data)  # noqa: S310
        else:
            print(f"dataset not found: {args.data}\nrun with --download, or fetch:\n"
                  f"  {DATA_URL}", file=sys.stderr)
            return 2

    data = json.load(open(args.data, encoding="utf-8"))
    samples = data if isinstance(data, list) else [data]
    if args.limit:
        samples = samples[:args.limit]
    print(f"loaded {len(samples)} conversation(s) from {args.data}", file=sys.stderr)
    prepared = [(units_of(s, args.granularity), qa_of(s)) for s in samples]

    rec, gids, cats, total_q, backends = re_eval.evaluate(
        prepared, list(args.backends), args.embed_model, args.granularity)
    if total_q == 0:
        print("no answerable questions found.", file=sys.stderr)
        return 1
    re_eval.report(rec, gids, cats, total_q, backends, args.granularity, "LoCoMo")
    if args.results:
        res = re_eval.build_results(rec, gids, total_q, backends, args.granularity,
                                    "LoCoMo", args.data)
        json.dump(res, open(args.results, "w", encoding="utf-8"), indent=2)
        print(f"\nwrote {args.results}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
