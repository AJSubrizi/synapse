# Using Agent Brain Runtime With RTK

RTK and Agent Brain Runtime solve different parts of the same problem.

- RTK reduces short-term token waste from shell output.
- Agent Brain Runtime preserves long-term knowledge across sessions.

Recommended instruction for agents:

```text
Use rtk before shell commands when possible.
Use the brain before planning, editing, or creating project output.
After meaningful work, distill reusable knowledge into the vault.
```

Example:

```bash
rtk git status
rtk rg "TODO"
rtk pytest -q
brain codex
```

RTK project: https://github.com/rtk-ai/rtk

