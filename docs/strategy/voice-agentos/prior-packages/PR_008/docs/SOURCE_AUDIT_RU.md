# Что действительно прочитано

№5 locally saved package, №6/7 materialized ZIPs and source references from
master were read. Source commit da6abf4; current main/build/merge not observed.
User reports previous being developed; no live status in another chat implied.

| Source | Observed basis | №8 consequence |
| --- | --- | --- |
| native_adapter.main | Bare stdin JSON until EOF; ok/result/error wrapper | direct stdio, no Chrome binary framing |
| native_adapter.operator_profile | Trusted store/policy/namespaces/templates/repositories | Reuse scope validation and same loaded profile |
| native_adapter.dispatch | Shared Core/content/review/repo domain routes | one implementation, early info path and readonly mode guard |
| automation_core.search/context_pack | FTS/current heads; ranked bounded search and selected-ID context | GUI labels bounded scope; preserve owner digest |
| agent-bridge/durable.mjs | shell=False, sanitized env, combined stdout/stderr limit, timeout | reuse qualification constraints, not unrestricted RPC |
| agent-bridge/Install.ps1 | Chrome extension ID, Node/Codex/C# host dependencies | separate direct-Python shell launcher |
| context_studio_v2/app.py | Tk widgets/worker queue with its own pipeline/snapshot backend | widget reference only, no forked backend |

Existing scope constraints remain explicit: Native input/output/timeout, selected
IDs<=10/context bytes<=48,000/search top matches<=20, profile repo aliases<=20.
They differ from total repository file count. This desktop slice does not remove
the broader processing limits or long job gaps. Dynamic page APIs must be used
to EOF; missing continuation cannot be fabricated. Scope-specific errors remain
visible. Full future work retained in source registries/followups.

Additional archived content-lab modules were extracted using capture manifest
Git OIDs/byte hashes. They are historical source evidence, not a runnable current
Windows installation. Native/runtime source is not executed by package QA.
