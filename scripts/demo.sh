#!/usr/bin/env bash
# Reproducible Synapse demo: learn -> write -> recall, in a throwaway vault.
# Self-contained — does not touch your real ~/Synapse or shell config.
# Record it with asciinema / vhs to produce the README demo GIF.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYN="$ROOT/bin/synapse"
DEMO="$(mktemp -d)"
trap 'rm -rf "$DEMO"' EXIT

VAULT="$DEMO/vault"
cp -R "$ROOT/templates/vault" "$VAULT"

export BRAIN_VAULT="$VAULT"
export SYNAPSE_TEMPLATES="$ROOT/templates"
export BRAIN_QUIET=1

step() { printf '\n\033[1;36m== %s ==\033[0m\n' "$1"; }

step "1. A fresh vault — Obsidian-compatible Markdown, no database"
"$SYN" status | sed -n '2,3p' || true

step "2. The agent learns something and writes an atomic note"
cat > "$VAULT/concepts/rate-limit-fastapi.md" <<'MD'
---
title: Rate-limit FastAPI endpoints
category: concepts
tags: [backend, security]
sources: [demo]
summary: Per-route rate limiting with slowapi + Redis, returning 429 + Retry-After.
created: 2026-06-19T00:00:00Z
updated: 2026-06-19T00:00:00Z
---
Use `slowapi` with a Redis backend. Decorate routes with `@limiter.limit("5/minute")`.
Return 429 with a `Retry-After` header. See [[workflow]] for the distillation loop.
MD
printf 'wrote concepts/rate-limit-fastapi.md\n'

step "3. Quality gate keeps the vault healthy"
"$SYN" check || true

step "4. Build the offline BM25 retrieval index"
"$SYN" index

step "5. Recall it later — by meaning, not exact words"
"$SYN" query "throttle API requests with redis"

step "Done — your memory is just Markdown you own: $VAULT"
