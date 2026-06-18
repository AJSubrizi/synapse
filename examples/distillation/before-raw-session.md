# Raw session notes (BEFORE distillation)

> This is what an agent has in its head at the end of a task. It is NOT vault-ready:
> no frontmatter, multiple ideas tangled together, no links, no summaries.

Spent the afternoon on the auth bug. Turns out the API expects the bearer token in the
`Authorization` header, not as a `?token=` query param like the old docs said — that's why
we kept getting 401s. Switched all callers to the header and the 401s went away.

Also: tokens expire after 15 min. We were caching them for an hour, so half the requests
failed silently. Fixed the cache TTL to 14 min to leave a margin. Should probably add a
refresh-on-401 retry later but didn't do it yet.

Tried using the `requests` session object to reuse connections — gave a nice ~30% latency
drop on the batch job. Keeping that.

Dead end: tried passing the token via a cookie. The gateway strips cookies, so that can
never work. Don't try it again.

Random: the staging gateway URL is gw-staging.internal, prod is gw.internal. (probably
belongs in the project note, not here)
