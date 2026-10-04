# Library query language

Examples:
`project:studious-pancake status:stale`
`qualification:blocked`
`source:chat tag:flashloan unresolved:true`
`kind:symbol tests:none`
`truth:speculative repo_owner:none`
`changed_since:7d`
`related_to:FAST-Q1`
`used_in_pack:false`
`risk:>=60`

Voice:
“Покажи все идеи из старых чатов про MarginFi, которых ещё нет в repo”

→ query JSON:
```json
{"project":"studious-pancake","source_type":"chat","tags":["marginfi"],"implementation_state":"missing"}
```

Query engine should be local/deterministic. LLM only translates free speech into structured query.
