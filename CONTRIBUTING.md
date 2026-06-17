# Contributing

Contributions should keep the project simple:

- plain Markdown;
- portable shell;
- no required cloud service;
- no interception of normal developer commands;
- clear compatibility with RTK.

Before submitting changes:

```bash
# Run Python tests
python3 tests/test_validate.py
python3 tests/test_dedup.py
python3 tests/test_skill.py

# Run shellcheck (if available)
shellcheck install.sh uninstall.sh scripts/install-agent-wrapper.sh bin/synapse 2>/dev/null || true

# Validate the vault template
python3 templates/vault/_meta/validate.py
```
