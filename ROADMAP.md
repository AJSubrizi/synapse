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
| 1 | Demo GIF/asciinema from `demo.sh` | Adoption: felt memory in <2 min | Low |
| 2 | Codex / OpenCode / Gemini hook parity | Loop reliability beyond Claude+Cursor rules | Med (blocked on each CLI's hook surface) |
| 3 | Shared `_meta/synapse_lib.py` | One frontmatter/parser; cut 6× drift | Med |
| 4 | Generated catalog section (keep human `index.md` hubs) | Catalog integrity at scale | Med |
| 5 | Eval gates in CI (nDCG / answer floors) | Retrieval regressions become measurable | Med |
| 6 | Memory packs (`synapse ingest --pack`) | Shareable file-based knowledge modules | High |
| 7 | Multi-vault `query --all` (RRF) | Work/personal vaults without monorepo | Med |

## Do not do

- Required database or hosted proprietary store
- Auto-merge of dedup candidates
- Mandatory embeddings on the base path
- Silent rewrite of user notes / full `index.md`
