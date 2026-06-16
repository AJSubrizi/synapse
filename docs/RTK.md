# Using Synapse With RTK

RTK and Synapse solve different parts of the same problem.

- RTK compresses shell output (short-term context).
- Synapse preserves long-term knowledge across sessions (vault).

Recommended:

```text
Use rtk before shell commands when possible.
Use synapse before planning, editing, or creating project output.
```
