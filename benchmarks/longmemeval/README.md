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

## Answer-accuracy track (optional, LLM)

Retrieval-only numbers don't tell you whether the retrieved context actually answers
the question. The answer track closes the loop: retrieve top-k units → an LLM answers
from them → a judge grades the answer. It needs `pip install anthropic` and
`ANTHROPIC_API_KEY` (default model `claude-opus-4-8`).

```bash
# retrieve with BM25, answer + judge with Claude
python3 run_longmemeval.py --data longmemeval_s.json --track answer

# offline plumbing check — no API key (echo answerer + substring judge)
python3 run_longmemeval.py --data fixture.json --track answer --answerer echo --judge exact
```

Flags: `--answer-backend` (default `bm25`), `--k` (passages fed to the answerer),
`--answerer claude|echo`, `--judge claude|exact`, `--answer-model` / `--judge-model`.

### Distillation-quality eval — the honest end-to-end number

Synapse's real artifact is *distilled notes*, not raw turns.
[`distillation_eval.py`](../distillation_eval.py) runs the full loop —
**distill sessions into notes → index with the shipped `search.py` (BM25) → retrieve →
answer → judge** — so it scores the learn→write→recall path on the artifact users
actually store:

```bash
python3 ../distillation_eval.py --data longmemeval_s.json          # claude distiller/answerer/judge
python3 ../distillation_eval.py --data fixture.json \
  --distiller echo --answerer echo --judge exact                   # offline plumbing
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

## Results (longmemeval_s_cleaned, session granularity, 470 answerable questions)

| backend | S@1 | S@5 | S@10 | R@5 | R@10 | nDCG@10 (95% CI) | MRR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| lexical | 73.2% | 90.4% | 95.7% | 81.4% | 90.7% | 79.8% [77.3, 82.4] | 0.808 |
| tfidf | 78.1% | 93.4% | 96.8% | 86.6% | 92.8% | 84.4% [82.0, 86.8] | 0.852 |
| **bm25** | **87.0%** | **96.8%** | **98.3%** | **91.2%** | **95.0%** | **89.8% [88.0, 91.8]** | **0.912** |

Per category (Recall@5, BM25): knowledge-update 99%, single-session-user 100%,
single-session-preference 83%, single-session-assistant 100%, multi-session 84%,
temporal-reasoning 88%.

Retrieval is much stronger here than on LoCoMo's turn-level task: LongMemEval sessions are
topically distinct, and session-level retrieval is closer to how Synapse stores distilled
notes. Numbers are retrieval-only and not comparable to LongMemEval's published
QA-accuracy figures, which generate and judge answers with an LLM. Embeddings/hybrid
backends are expected to lift the harder categories (multi-session, temporal) further.

## Caveat

Retrieval-only numbers; not comparable to LongMemEval's published QA-accuracy figures,
which generate and judge answers with an LLM.
