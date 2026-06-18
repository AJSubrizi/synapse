# LoCoMo retrieval benchmark

A reproducible, **fully offline, zero-API-cost** benchmark of Synapse's retriever on the
[LoCoMo](https://github.com/snap-research/locomo) long-conversation memory dataset.

## What this measures (and what it doesn't)

LoCoMo has two things you could score:

1. **Answer accuracy** — generate an answer per question and judge it. This needs an LLM
   and a judge model, i.e. API cost and a model dependency. Numbers like Memanto's
   "87.1% on LoCoMo" are this track.
2. **Retrieval** — does the system surface the *gold evidence turn(s)* for each question?
   This needs no model and no network. It's the honest claim Synapse can make today:
   _"X% recall@k, entirely on your machine, at zero cost."_

**This harness measures (2).** For each backend it reports, overall and per LoCoMo
category:

- **Success@k** — any gold evidence unit in the top-k (hit rate)
- **Recall@k** — fraction of gold units retrieved in top-k (matters for multi-evidence)
- **nDCG@k** — position-aware, graded by how many gold hits
- **MRR** — reciprocal rank of the first gold unit

The headline metric (**nDCG@10**) comes with a **95% cluster-bootstrap confidence
interval** resampled over conversations (N=10 is small, so the CI matters). Each run can
emit a `results.json` with full metadata (dataset SHA-256, granularity, seed, backends,
Python version, harness commit) for reproducibility.

### Backends

| backend | deps | notes |
| --- | --- | --- |
| `lexical` | none | count-based matching, mirrors `synapse search` body scan |
| `tfidf` | none | TF-IDF cosine, same formulation as `synapse index` |
| `bm25` | none | Okapi BM25 — the standard strong lexical IR baseline |
| `embeddings` | `sentence-transformers` | opt-in; skipped cleanly if not installed |

### Granularity

`--granularity turn` (default) treats each dialogue turn as a retrieval unit;
`--granularity session` treats each session as a unit. Session granularity is closer to
how Synapse actually stores memory (distilled notes, not raw turns) and scores much higher.

## Run it

```bash
cd benchmarks/locomo

# fetches locomo10.json from snap-research/locomo
python3 run_locomo.py --download

# default backends: lexical + tfidf + bm25 (no dependencies), with a results file
python3 run_locomo.py --data locomo10.json --results results.json

# session granularity (closer to Synapse's note-level memory)
python3 run_locomo.py --granularity session

# add the optional embeddings backend (needs: pip install sentence-transformers)
python3 run_locomo.py --backends bm25 embeddings
```

## Results (turn-level, 1982 answerable questions, 10 conversations)

| backend | S@1 | S@5 | S@10 | R@5 | R@10 | nDCG@10 (95% CI) | MRR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| lexical | 19.0% | 38.7% | 48.7% | 35.4% | 44.3% | 30.8% [28.3, 32.7] | 0.289 |
| tfidf | 22.7% | 45.8% | 55.0% | 42.1% | 50.7% | 35.8% [33.4, 37.7] | 0.335 |
| **bm25** | **27.2%** | **50.6%** | **58.3%** | **46.6%** | **53.8%** | **39.8% [37.6, 41.7]** | **0.378** |

Session-level (BM25): **S@5 88.5%, R@5 83.6%, nDCG@10 77.1% [74.8, 79.7]** — granularity
matters more than the backend.

Numbers are retrieval-only and not comparable to QA-accuracy figures from papers. Embeddings
and hybrid (BM25 + embeddings) backends are expected to lift the turn-level numbers further;
run them locally to extend the table.

Quick smoke test without the real dataset:

```bash
python3 run_locomo.py --data fixture.json
```

## Output

```
LoCoMo retrieval benchmark — N answerable questions
backend       R@1      R@3      R@5      R@10     MRR
--------------------------------------------------------
lexical        ..%      ..%      ..%      ..%    .....
tfidf          ..%      ..%      ..%      ..%    .....
embeddings     ..%      ..%      ..%      ..%    .....

Recall@5 by LoCoMo category:
...
```

Questions whose `evidence` list is empty (LoCoMo's adversarial / unanswerable items) are
excluded, since there is no gold turn to retrieve.

## Notes & honesty caveats

- **Turn-level granularity.** Evidence is matched by `dia_id` (e.g. `D1:3`). We retrieve
  over individual dialogue turns. Chunking strategy affects the numbers; this one keeps
  one turn = one retrievable unit so results are directly comparable to the gold labels.
- **Not the answer-accuracy track.** Don't compare these numbers head-to-head with
  papers reporting QA accuracy — different task.
- **Keep the tokenizer in sync** with `templates/vault/_meta/search.py`; if you change one,
  change both (there's a comment marking the shared block).
- The dataset is © its authors; see the snap-research/locomo repo for terms. This harness
  downloads it on demand and does not vendor it.
