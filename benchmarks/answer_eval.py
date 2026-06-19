#!/usr/bin/env python3
"""Answer-accuracy track for Synapse benchmarks: retrieval -> LLM answer -> judge.

The retrieval benchmarks (retrieval_eval.py) measure whether the gold evidence is
ranked highly. This module closes the loop the README promises: feed the retrieved
units to an LLM, have it answer, and grade the answer. It turns a *retrieval* number
into a *memory* number.

Everything here is optional and degrades cleanly:
  - answerer = "claude"  -> calls the Claude API (default model claude-opus-4-8)
  - answerer = "echo"    -> returns the top retrieved unit verbatim (offline)
  - judge    = "claude"  -> LLM-as-judge (default model claude-opus-4-8)
  - judge    = "exact"   -> normalized substring match (offline, deterministic)

The offline echo/exact path lets CI exercise the full plumbing without an API key.
Ranking reuses retrieval_eval's backends, so the same retriever scores both tracks.
"""
from __future__ import annotations

import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import retrieval_eval as re_eval  # noqa: E402

DEFAULT_MODEL = "claude-opus-4-8"

ANSWER_SYSTEM = (
    "You answer questions strictly from the provided context passages. "
    "If the answer is not in the context, say you don't know. Answer concisely — "
    "a phrase or one sentence, no preamble."
)
JUDGE_SYSTEM = (
    "You are a strict grader. Decide whether a candidate answer matches the reference "
    "answer in meaning. Minor wording differences are fine. Reply with exactly one word: "
    "CORRECT or INCORRECT."
)


def build_answer_prompt(question: str, contexts: list[str]) -> str:
    ctx = "\n\n".join(f"[{i + 1}] {t}" for i, t in enumerate(contexts)) or "(no context)"
    return f"Context:\n{ctx}\n\nQuestion: {question}\n\nAnswer:"


def build_judge_prompt(question: str, gold: str, pred: str) -> str:
    return (f"Question: {question}\nReference answer: {gold}\n"
            f"Candidate answer: {pred}\n\nIs the candidate correct? Reply CORRECT or INCORRECT.")


# --- Claude client + answerer/judge factories -----------------------------------------

def make_client():
    """An Anthropic client, or None if the SDK/key is unavailable (clean degrade)."""
    try:
        import anthropic  # type: ignore
    except Exception:
        return None
    try:
        return anthropic.Anthropic()
    except Exception:
        return None


def _text(resp) -> str:
    if getattr(resp, "stop_reason", None) == "refusal":
        return ""
    for block in resp.content:
        if block.type == "text":
            return block.text
    return ""


def claude_answerer(client, model: str = DEFAULT_MODEL):
    def answer(question: str, contexts: list[str]) -> str:
        resp = client.messages.create(
            model=model, max_tokens=512, system=ANSWER_SYSTEM,
            messages=[{"role": "user", "content": build_answer_prompt(question, contexts)}])
        return _text(resp).strip()
    return answer


def echo_answerer():
    """Offline answerer: return the top retrieved passage verbatim."""
    def answer(question: str, contexts: list[str]) -> str:
        return contexts[0] if contexts else ""
    return answer


def claude_judge(client, model: str = DEFAULT_MODEL):
    def judge(question: str, gold: str, pred: str) -> bool:
        if not gold.strip():
            return False
        resp = client.messages.create(
            model=model, max_tokens=8, system=JUDGE_SYSTEM,
            messages=[{"role": "user", "content": build_judge_prompt(question, gold, pred)}])
        return _text(resp).strip().upper().startswith("CORRECT")
    return judge


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())).strip()


def exact_judge():
    """Offline judge: normalized substring match in either direction."""
    def judge(question: str, gold: str, pred: str) -> bool:
        g, p = _norm(gold), _norm(pred)
        return bool(g) and (g in p or p in g)
    return judge


# --- ranking (reuse retrieval_eval backends) ------------------------------------------

def _build(backend: str, units, embed_model: str):
    if backend == "lexical":
        return units
    if backend == "tfidf":
        return re_eval.build_tfidf(units)
    if backend == "bm25":
        return re_eval.build_bm25(units)
    if backend in ("embeddings", "hybrid"):
        emb = re_eval.build_embeddings(units, embed_model)
        if emb is None:
            return None
        return emb if backend == "embeddings" else (re_eval.build_bm25(units), emb)
    raise ValueError(f"unknown backend: {backend}")


# --- evaluation -----------------------------------------------------------------------

def evaluate_answers(prepared, backend, k, answerer, judge,
                     embed_model="all-MiniLM-L6-v2"):
    """prepared: iterable of (units, qas) where each qa has 'question' and 'answer'.
    Returns list of (category, correct) or None if the backend's model is unavailable."""
    if backend not in re_eval.BACKENDS:
        raise ValueError(f"unknown backend: {backend}")
    _, ranker, _ = re_eval.BACKENDS[backend]
    rows = []
    prepared = list(prepared)
    for gi, (units, qas) in enumerate(prepared):
        if not units or not qas:
            continue
        model_obj = _build(backend, units, embed_model)
        if model_obj is None:
            print("answer_eval: embeddings backend unavailable — install "
                  "sentence-transformers or use --answer-backend bm25.", file=sys.stderr)
            return None
        for qa in qas:
            ranked = ranker(qa["question"], model_obj)
            contexts = [units[i][1] for i in ranked[:k]]
            pred = answerer(qa["question"], contexts)
            ok = bool(judge(qa["question"], qa.get("answer", ""), pred))
            rows.append((qa.get("category", "unknown"), ok))
        print(f"  sample {gi + 1}/{len(prepared)}: {len(qas)} answered", file=sys.stderr)
    return rows


def report_answers(rows, backend, k, dataset, answerer_name, judge_name):
    total = len(rows)
    correct = sum(1 for _, ok in rows if ok)
    acc = (correct / total) if total else 0.0
    print(f"\n{dataset} answer-accuracy — {total} questions, backend={backend}, "
          f"top-k={k}, answerer={answerer_name}, judge={judge_name}")
    print(f"accuracy: {acc * 100:.1f}%  ({correct}/{total})\n")
    by = defaultdict(lambda: [0, 0])
    for cat, ok in rows:
        by[cat][1] += 1
        by[cat][0] += 1 if ok else 0
    print(f"{'category':<26}{'acc':>8}{'n':>6}")
    print("-" * 40)
    for cat in sorted(by, key=str):
        c, n = by[cat]
        print(f"{str(cat)[:26]:<26}{(c / n * 100 if n else 0):7.1f}%{n:6d}")
    return acc
