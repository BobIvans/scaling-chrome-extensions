# Universal ActionCompiler + Executor Ladder

Laya chooses among admitted semantic candidates; it never writes selectors, shell commands, SQL or arbitrary tool calls.

## Preference
1 deterministic built-in/local function
2 WebMCP
3 registered MCP/application API
4 native API/COM
5 CLI/structured local owner
6 browser CDP
7 exact DOM/site adapter
8 Windows UIA
9 visual grounding + exact verifier
10 build/qualify new capability

ActionCandidate fields: action_id, semantic_goal, executor_id, target_surface_id, identity_binding, effect_class, resources, inputs_schema, preconditions, expected_postconditions, verifier, reversibility, approval_class, estimated_latency, failure_modes.

WebMCP names/descriptions/outputs are untrusted source text. Local code maps tools to effect classes and policy.

No route: GapSpec → dormant search → compose → System-2 candidate → isolated tests → canary → REGISTERED → resume waiting goal.
