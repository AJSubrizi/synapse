#!/usr/bin/env python3
"""Distillation-quality eval — the honest end-to-end number for Synapse.

The retrieval and answer benchmarks score raw chat sessions. But Synapse's real
artifact is *distilled atomic notes*, not raw turns. This eval runs the actual loop:

    raw sessions -> distill into notes -> index with the shipped retriever (search.py)
                 -> retrieve top-k notes -> LLM answer -> judge

So it measures whether the full learn->write->recall loop produces correct answers,
using the same BM25 retriever users get from `synapse index`.

Reuses answer_eval (answerer + judge + client) and the shipped search.py retriever.

Distiller / answerer / judge are pluggable and degrade:
  --distiller claude|echo   echo writes each session verbatim as a note (offline)
  --answerer  claude|echo   (see answer_eval)
  --judge     claude|exact  exact = offline substring match

Offline mode (echo/echo/exact) lets CI exercise the whole loop without an API key.

Data: a LongMemEval-style JSON (haystack_sessions + question + answer per entry).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "templates", "vault", "_meta"))
import answer_eval as ans_eval  # noqa: E402
import search  # noqa: E402  (the shipped retriever)

DISTILL_SYSTEM = (
    "You distill a chat session into a single atomic note for a knowledge base. "
    "Output a one-line summary, then the durable facts as terse bullet points. "
    "Keep only what would be worth recalling later. No preamble."
)


def claude_distiller(client, model: str = ans_eval.DEFAULT_MODEL):
    def distill(session_text: str) -> str:
        resp = client.messages.create(
            model=model, max_tokens=400, system=DISTILL_SYSTEM,
            messages=[{"role": "user", "content": session_text[:8000]}])
        return ans_eval._text(resp).strip()
    return distill


def echo_distiller():
    def distill(session_text: str) -> str:
        return session_text
    return distill


def _session_text(session) -> str:
    parts = []
    for turn in session or []:
        if isinstance(turn, dict):
            parts.append(f"{turn.get('role', '')}: "
                         f"{turn.get('content') or turn.get('text') or ''}".strip())
        else:
            parts.append(str(turn))
    return "\n".join(parts)


def _point_search_at(vault_dir: str):
    meta = os.path.join(vault_dir, "_meta")
    os.makedirs(os.path.join(vault_dir, "concepts"), exist_ok=True)
    os.makedirs(meta, exist_ok=True)
    search.VAULT, search.META = vault_dir, meta
    search.INDEX = os.path.join(meta, "retrieval.json")
    search.DIGEST = os.path.join(meta, "digest.md")


def run_entry(entry, distiller, answerer, judge, k):
    """Distill one entry's sessions into a temp vault, index, retrieve, answer, judge."""
    sessions = entry.get("haystack_sessions") or entry.get("sessions") or []
    question = entry.get("question", "")
    answer = entry.get("answer", "")
    with tempfile.TemporaryDirectory() as vault:
        _point_search_at(vault)
        for i, sess in enumerate(sessions):
            note = distiller(_session_text(sess))
            if note.strip():
                open(os.path.join(vault, "concepts", f"note-{i}.md"), "w",
                     encoding="utf-8").write(note + "\n")
        index = search.build_bm25_index()
        ranked = search._bm25_scored(index, question)[:k]
        contexts = []
        for _, rel in ranked:
            try:
                contexts.append(open(os.path.join(vault, rel), encoding="utf-8").read())
            except OSError:
                pass
        pred = answerer(question, contexts)
        return bool(judge(question, answer, pred))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True, help="LongMemEval-style JSON")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--distiller", default="claude", choices=["claude", "echo"])
    ap.add_argument("--answerer", default="claude", choices=["claude", "echo"])
    ap.add_argument("--judge", default="claude", choices=["claude", "exact"])
    ap.add_argument("--model", default=None, help="default: claude-opus-4-8")
    args = ap.parse_args()

    if not os.path.isfile(args.data):
        print(f"dataset not found: {args.data}", file=sys.stderr)
        return 2
    data = json.load(open(args.data, encoding="utf-8"))
    entries = data if isinstance(data, list) else [data]
    entries = [e for e in entries if not str(e.get("question_id", "")).endswith("_abs")
               and e.get("answer")]
    if args.limit:
        entries = entries[:args.limit]
    if not entries:
        print("no answerable entries with gold answers found.", file=sys.stderr)
        return 1

    client = None
    if "claude" in (args.distiller, args.answerer, args.judge):
        client = ans_eval.make_client()
        if client is None:
            print("claude distiller/answerer/judge needs the 'anthropic' SDK + "
                  "ANTHROPIC_API_KEY; use --distiller echo --answerer echo --judge exact "
                  "for the offline plumbing.", file=sys.stderr)
            return 2
    model = args.model or ans_eval.DEFAULT_MODEL
    distiller = claude_distiller(client, model) if args.distiller == "claude" else echo_distiller()
    answerer = ans_eval.claude_answerer(client, model) if args.answerer == "claude" else ans_eval.echo_answerer()
    judge = ans_eval.claude_judge(client, model) if args.judge == "claude" else ans_eval.exact_judge()

    rows = []
    for gi, entry in enumerate(entries):
        ok = run_entry(entry, distiller, answerer, judge, args.k)
        rows.append((entry.get("question_type", "unknown"), ok))
        print(f"  entry {gi + 1}/{len(entries)}: {'ok' if ok else 'miss'}", file=sys.stderr)

    total = len(rows)
    correct = sum(1 for _, ok in rows if ok)
    print(f"\nDistillation-quality eval — {total} questions, top-k={args.k}, "
          f"distiller={args.distiller}, answerer={args.answerer}, judge={args.judge}")
    print(f"end-to-end accuracy: {correct / total * 100:.1f}%  ({correct}/{total})\n")
    by = defaultdict(lambda: [0, 0])
    for cat, ok in rows:
        by[cat][1] += 1
        by[cat][0] += 1 if ok else 0
    print(f"{'category':<26}{'acc':>8}{'n':>6}")
    print("-" * 40)
    for cat in sorted(by, key=str):
        c, n = by[cat]
        print(f"{str(cat)[:26]:<26}{(c / n * 100 if n else 0):7.1f}%{n:6d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
