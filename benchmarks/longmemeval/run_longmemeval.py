#!/usr/bin/env python3
"""LongMemEval retrieval benchmark for Synapse (offline, zero API cost).

A second dataset to test whether Synapse's retriever generalises beyond LoCoMo.
LongMemEval (https://github.com/xiaowu0162/LongMemEval) embeds each question in a large
"haystack" of chat sessions; only some sessions contain the evidence. We measure whether
the retriever ranks the gold evidence in the top-k — retrieval only, no LLM.

Each entry provides:
    haystack_sessions     list of sessions; each session is a list of {role, content,
                          optional has_answer:true} turns
    haystack_session_ids  parallel list of session ids
    answer_session_ids    the session id(s) that contain the answer evidence

Gold by granularity:
    session  gold = answer_session_ids                       (default; matches Synapse notes)
    turn     gold = turns flagged has_answer (fallback: all turns in answer sessions)

Abstention questions (no evidence in the haystack) are skipped, as there is no gold to rank.

Backends, metrics and statistics are shared with LoCoMo via ../retrieval_eval.py.

Dataset: download longmemeval_s.json (or _m / _oracle) from the LongMemEval release
(HuggingFace: xiaowu0162/longmemeval) and pass it with --data.

Usage:
    python3 run_longmemeval.py --data longmemeval_s.json
    python3 run_longmemeval.py --data longmemeval_s.json --granularity turn
    python3 run_longmemeval.py --data longmemeval_s.json --backends bm25 embeddings hybrid --results results.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import retrieval_eval as re_eval  # noqa: E402


def _session_ids(entry, n):
    ids = entry.get("haystack_session_ids") or entry.get("session_ids")
    if ids and len(ids) == n:
        return [str(s) for s in ids]
    return [f"sess{i}" for i in range(n)]


def _turn_text(turn):
    if isinstance(turn, dict):
        return f"{turn.get('role','')}: {turn.get('content') or turn.get('text') or ''}".strip()
    return str(turn)


def units_of(entry, granularity):
    sessions = entry.get("haystack_sessions") or entry.get("sessions") or []
    sids = _session_ids(entry, len(sessions))
    units = []
    if granularity == "turn":
        for sid, sess in zip(sids, sessions):
            for ti, turn in enumerate(sess or []):
                uid = f"{sid}#{ti}"
                units.append((uid, _turn_text(turn), frozenset({uid})))
    else:  # session
        for sid, sess in zip(sids, sessions):
            text = "\n".join(_turn_text(t) for t in (sess or []))
            units.append((sid, text, frozenset({sid})))
    return units, sids, sessions


def gold_of(entry, granularity, sids, sessions):
    answer_sids = {str(s) for s in (entry.get("answer_session_ids") or [])}
    if granularity == "session":
        return frozenset(answer_sids)
    # turn granularity: prefer has_answer flags
    gold = set()
    for sid, sess in zip(sids, sessions):
        for ti, turn in enumerate(sess or []):
            if isinstance(turn, dict) and turn.get("has_answer"):
                gold.add(f"{sid}#{ti}")
    if not gold and answer_sids:                 # fallback: whole answer session(s)
        for sid, sess in zip(sids, sessions):
            if sid in answer_sids:
                for ti in range(len(sess or [])):
                    gold.add(f"{sid}#{ti}")
    return frozenset(gold)


def prepare(entry, granularity):
    qid = str(entry.get("question_id", ""))
    units, sids, sessions = units_of(entry, granularity)
    gold = gold_of(entry, granularity, sids, sessions)
    if qid.endswith("_abs") or not gold:
        return units, []                         # abstention / no gold -> no question
    qa = [{"question": entry.get("question", ""), "evidence": gold,
           "category": entry.get("question_type", "unknown")}]
    return units, qa


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True, help="path to longmemeval_*.json")
    ap.add_argument("--backends", nargs="+", default=["lexical", "tfidf", "bm25"],
                    choices=list(re_eval.BACKENDS))
    ap.add_argument("--granularity", default="session", choices=["turn", "session"])
    ap.add_argument("--embed-model", default="all-MiniLM-L6-v2")
    ap.add_argument("--limit", type=int, default=0,
                    help="only evaluate the first N entries (quick smoke run)")
    ap.add_argument("--results", default="")
    args = ap.parse_args()

    if not os.path.isfile(args.data):
        print(f"dataset not found: {args.data}\n"
              "Download longmemeval_s.json from the LongMemEval release "
              "(HuggingFace: xiaowu0162/longmemeval).", file=sys.stderr)
        return 2

    data = json.load(open(args.data, encoding="utf-8"))
    entries = data if isinstance(data, list) else [data]
    if args.limit:
        entries = entries[:args.limit]
    print(f"loaded {len(entries)} question entries from {args.data}", file=sys.stderr)
    prepared = [prepare(e, args.granularity) for e in entries]

    rec, gids, cats, total_q, backends = re_eval.evaluate(
        prepared, list(args.backends), args.embed_model, args.granularity)
    if total_q == 0:
        print("no answerable questions found — check the dataset schema.", file=sys.stderr)
        return 1
    re_eval.report(rec, gids, cats, total_q, backends, args.granularity, "LongMemEval")
    if args.results:
        res = re_eval.build_results(rec, gids, total_q, backends, args.granularity,
                                    "LongMemEval", args.data)
        json.dump(res, open(args.results, "w", encoding="utf-8"), indent=2)
        print(f"\nwrote {args.results}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
