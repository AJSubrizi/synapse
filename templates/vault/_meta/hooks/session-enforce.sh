#!/usr/bin/env bash
# Claude Code SessionStart / SubagentStart — inject Synapse bootstrap context.
input="$(cat)"
event="$(printf '%s' "$input" | jq -r '.hook_event_name // "SessionStart"' 2>/dev/null)"
[ -z "$event" ] && event="SessionStart"

vault="${BRAIN_VAULT:-${SYNAPSE_HOME:-$HOME/Synapse}/vault}"

ctx="[Synapse — enforced]
Operational manual: ${vault}/AGENTS.md
Workflow: ${vault}/_meta/workflow.md

Before planning, coding, or deciding:
1. Phase 0 (default) or Phase 0-short for trivial tasks.
2. hot.md + index.md (if index >80 entries, synthesis hub + grep only).
3. Run Phase 0 before any skill from the skills catalog.
4. Subagents: pass vault path, relevant pages, meaningful-work rule.
5. Distill only for meaningful work; if vault/ changed, run synapse check before close."

jq -n --arg e "$event" --arg c "$ctx" \
  '{hookSpecificOutput:{hookEventName:$e, additionalContext:$c}}'
