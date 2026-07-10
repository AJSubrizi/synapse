# Synapse — Roadmap

> Updated 2026-07-10 after the A→B→C upgrade pass (onboard / engine sync / compounding).
> Principle unchanged: core stays file-based, plain Markdown, no required DB.

## Shipped (was roadmap; now done)

| Theme | Status |
|---|---|
| Retrieval (search, BM25, embeddings, hybrid, digest) | Done |
| `synapse setup <agent>` + Claude hooks | Done (+ Cursor `.mdc`) |
| Distillation templates + `lint --strict` | Done (+ workflow self-correct) |
| Skills deps / suggest / version field | Done (suggest now retrieval-backed) |
| Git staleness, metrics, demo.sh, examples | Done |
| `synapse onboard` / `upgrade` / rich `doctor` | Done (v0.5.0 engine) |
| Index fingerprint / stale detection | Done |
| `wiki.py update` / `file update` | Done |

## Next (prioritized)

| # | Theme | Why | Effort |
|---|---|---|---|
| 1 | Demo GIF/asciinema from `demo.sh` | Recorder ready (`scripts/record-demo.sh`); GIF asset optional | Low |
| 2 | Codex / OpenCode / Gemini hook parity | Loop reliability beyond Claude+Cursor rules | Med (blocked on each CLI's hook surface) |
| 3 | Shared `_meta/synapse_lib.py` | **Done** (0.5.1) | — |
| 4 | Generated catalog section (keep human `index.md` hubs) | **Done** (`_meta/catalog.md`) | — |
| 5 | Eval gates in CI (nDCG / answer floors) | **Done** (fixture floors) | — |
| 6 | Memory packs (`synapse pack export|import`) | **Done** (MVP tar.gz) | — |
| 7 | Multi-vault `query --all` (RRF) | **Done** | — |

## Do not do

- Required database or hosted proprietary store
- Auto-merge of dedup candidates
- Mandatory embeddings on the base path
- Silent rewrite of user notes / full `index.md`
