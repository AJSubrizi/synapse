---
title: api-token-expiry
category: concepts
tags: [backend, security]
sources: [auth-bug-session]
summary: Auth tokens expire after 15 minutes; cache them at most 14 min and plan a refresh-on-401 retry.
created: 2026-06-18T00:00:00Z
updated: 2026-06-18T00:00:00Z
---

# api-token-expiry

Tokens are valid for 15 minutes. Caching them for an hour caused silent request failures.
Cache TTL is now 14 minutes to leave a safety margin.

Open follow-up: add a refresh-on-`401` retry so an expired token self-heals instead of
failing the call. Related: [[api-auth-bearer-header]].
