# LongMemEval retrieval benchmark

A second dataset (besides LoCoMo) to test whether Synapse's retriever **generalises** — a
single benchmark invites overfitting. Same engine, same metrics, **fully offline, zero
API cost**.

[LongMemEval](https://github.com/xiaowu0162/LongMemEval) embeds each question in a large
"haystack" of chat sessions; only a few sessions hold the evidence. We measure whether the
retriever ranks the gold evidence in the top-k. Retrieval only — no LLM answer generation.

## Get the data

LongMemEval is distributed via its release (HuggingFace `xiaowu0162/longmemeval`). Download
one of `longmemeval_s.json` (small haystack), `longmemeval_m.json` (medium), or
`longmemeval_oracle.json` (evidence only) and drop it in this folder.

## Run it

```bash
cd benchmarks/longmemeval

# session granularity (default; closest to how Synapse stores distilled notes)
python3 run_longmemeval.py --data longmemeval_s.json --results results.json

# turn granularity (uses per-turn has_answer flags)
python3 run_longmemeval.py --data longmemeval_s.json --granularity turn

# add embeddings + hybrid (needs: pip install sentence-transformers)
python3 run_longmemeval.py --data longmemeval_s.json --backends bm25 embeddings hybrid
```

Smoke test without the real data:

```bash
python3 run_longmemeval.py --data fixture.json
```

## What's measured

Identical to the LoCoMo harness (shared `../retrieval_eval.py`):

- **Success@k**, **Recall@k** (multi-evidence), **nDCG@k**, **MRR**
- headline **nDCG@10** with a 95% cluster-bootstrap CI
- per-category breakdown (here: by LongMemEval `question_type`)
- optional `results.json` with dataset SHA-256, seed, backends, and harness commit

## Gold & granularity

- `--granularity session` (default): gold = `answer_session_ids`.
- `--granularity turn`: gold = turns flagged `has_answer` (falls back to all turns in the
  answer session(s) if no flags are present).
- Abstention questions (`*_abs`, no evidence in the haystack) are skipped — there is no
  gold unit to retrieve. (A future answer-accuracy track could score abstention directly.)

## Caveat

Retrieval-only numbers; not comparable to LongMemEval's published QA-accuracy figures,
which generate and judge answers with an LLM.
