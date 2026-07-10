# synapse

<!-- ohcanvas-flow-memory:start -->
## OhCanvas Flow Memory

Before exploring this repository, read `.ohcanvas/flow/active-context.md`.
It is the shared working memory for agents on this canvas (goal, decisions, tasks, touched files).
Do not re-scan the whole repo. Prefer suggested/touched files from that pack.
After important decisions, update it with:
OHCANVAS {"action":"flow_memory_append","kind":"decision","text":"..."}
OHCANVAS {"action":"flow_memory_update_task","text":"...","status":"done"}
OHCANVAS {"action":"flow_memory_touch","paths":["src/foo.ts"]}
<!-- ohcanvas-flow-memory:end -->
