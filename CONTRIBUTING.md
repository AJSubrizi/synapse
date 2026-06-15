# Contributing

Contributions should keep the project simple:

- plain Markdown;
- portable shell;
- no required cloud service;
- no interception of normal developer commands;
- clear compatibility with RTK.

Before submitting changes:

```bash
python3 templates/vault/_meta/validate.py
shellcheck install.sh uninstall.sh scripts/install-agent-wrapper.sh 2>/dev/null || true
```
