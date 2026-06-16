# Custom Layouts

Synapse defaults to a self-contained home directory:

```text
~/Synapse/vault/          # knowledge base
~/Synapse/vault/skills/   # skill procedures (starter: distill-after-work only)
```

Use this when your skills and vault live in a **monorepo** or split directories.

## Variables

| Variable | Default install | Custom monorepo example |
|----------|-----------------|-------------------------|
| `SYNAPSE_HOME` / `BRAIN_ROOT` | `~/Synapse` | `~/Projects/MyBrain` |
| `BRAIN_VAULT` | `$BRAIN_ROOT/vault` | same |
| `BRAIN_BOOT` | `$BRAIN_VAULT/AGENTS.md` | `$BRAIN_ROOT/AGENTS.md` (index → vault manual) |
| `BRAIN_SKILLS_DIR` | `$BRAIN_VAULT/skills` | `$BRAIN_ROOT/.agents/skills` or `$BRAIN_ROOT/*/SKILL.md` |

Environment variables `BRAIN_*` are kept for compatibility; `SYNAPSE_HOME` is the
preferred name for the install root.

## Skills outside `vault/skills/`

Ship a vault-local `_meta/skill.py` that discovers:

1. `$BRAIN_ROOT/<name>/SKILL.md` (canonical layout)
2. `$BRAIN_SKILLS_DIR/<name>/SKILL.md` (agent mirror)

Exclude non-skill directories (`vault`, dot dirs, project folders).

**Do not** copy a large private skill library into the Synapse repo — keep skills in your
brain root and point `BRAIN_SKILLS_DIR` / `skill.py` at them.

## Shell bootstrap

For custom paths, edit `~/.zshrc` manually or set env vars **before** `synapse reinit`:

```bash
export SYNAPSE_HOME="$HOME/Projects/MyBrain"
export BRAIN_ROOT="$SYNAPSE_HOME"
export BRAIN_VAULT="$BRAIN_ROOT/vault"
export BRAIN_BOOT="$BRAIN_ROOT/AGENTS.md"
export BRAIN_SKILLS_DIR="$BRAIN_ROOT/.agents/skills"
```

Do not run `install.sh` reinit blindly on a custom block — it writes default paths.

## Cursor / Claude Code

- **Cursor:** `.cursor/rules/synapse.mdc` with `alwaysApply: true`, absolute vault paths.
- **Claude Code:** wire `vault/_meta/hooks/session-enforce.sh` (SessionStart/SubagentStart)
  and `stop-check.sh` (Stop) in `.claude/settings.json`.

See `templates/vault/_meta/hooks/` for starter scripts.

## Migration from Agent Brain Runtime

- Repo renamed to **Synapse**; CLI is `synapse` (`brain` symlink for compatibility).
- Default home moved from `~/AI-Brain` to `~/Synapse` (override with `SYNAPSE_HOME`).
- Shell block marker is `# >>> Synapse >>>` (legacy `Agent Brain Runtime` stripped on reinit).
