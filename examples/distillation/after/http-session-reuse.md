---
title: http-session-reuse
category: concepts
tags: [backend, devops]
sources: [auth-bug-session]
summary: Reusing one HTTP session/connection pool across calls cut batch-job latency by ~30%.
created: 2026-06-18T00:00:00Z
updated: 2026-06-18T00:00:00Z
---

# http-session-reuse

Reuse a single HTTP session object (connection pooling) instead of opening a fresh
connection per request. On the batch job this gave roughly a 30% latency drop.

Pairs with the auth fix in [[api-auth-bearer-header]] — both came out of the same session.
