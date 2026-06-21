# Contributing

Contributions should keep the project simple:

- plain Markdown;
- portable shell;
- no required cloud service;
- no interception of normal developer commands;
- clear compatibility with RTK.

Before submitting changes:

```bash
# Run all Python tests (as CI does)
for t in tests/test_*.py; do python3 "$t" || exit 1; done

# Run shellcheck (if available)
shellcheck install.sh uninstall.sh scripts/*.sh bin/synapse templates/vault/_meta/hooks/*.sh

# Validate the vault template
python3 templates/vault/_meta/validate.py
```

## Process

Keep the history trustworthy — this project asks people to store their memory in it.

- **Branch from `main`**; never commit straight to `main`.
- **One PR per coherent change.** Don't merge a PR until the work is actually complete and
  CI is green — merging early (then pushing more to the same branch) leaves `main` behind.
- **Tag releases** (`vMAJOR.MINOR.PATCH`) on `main` after merge; update `CHANGELOG.md`.
- **Avoid force-pushing shared history** (`main`, merged branches). If a rewrite is truly
  needed, keep a backup ref and say so in the PR.
