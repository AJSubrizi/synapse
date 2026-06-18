---
title: api-auth-bearer-header
category: concepts
tags: [backend, security]
sources: [auth-bug-session]
summary: The API authenticates via a bearer token in the Authorization header; query-param and cookie auth both fail (gateway strips cookies).
created: 2026-06-18T00:00:00Z
updated: 2026-06-18T00:00:00Z
---

# api-auth-bearer-header

Send credentials as `Authorization: Bearer <token>`. The old docs showing `?token=` are
wrong and cause `401`s. Cookie-based auth cannot work either: the gateway strips cookies
before the request reaches the service.

See [[api-token-expiry]] for the token lifetime, and [[http-session-reuse]] for the
connection-reuse win found in the same session.
