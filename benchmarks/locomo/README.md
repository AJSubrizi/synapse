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

**This harness measures (2).** It reports `recall@{1,3,5,10}` and `MRR`, overall and per
LoCoMo question category, for each retrieval backend. It does not call any LLM.

The retriever under test is the same one shipped in `synapse search` / `synapse index`:
identical tokenizer and the same TF-IDF cosine formulation. An optional `embeddings`
backend (sentence-transformers) is included for comparison and is skipped cleanly if the
library isn't installed.

## Run it

```bash
cd benchmarks/locomo

# fetches data/locomo10.json from snap-research/locomo
python3 run_locomo.py --download

# default backends: lexical + tfidf (no dependencies)
python3 run_locomo.py --data locomo10.json

# add the optional embeddings backend (needs: pip install sentence-transformers)
python3 run_locomo.py --data locomo10.json --backends lexical tfidf embeddings
```

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
