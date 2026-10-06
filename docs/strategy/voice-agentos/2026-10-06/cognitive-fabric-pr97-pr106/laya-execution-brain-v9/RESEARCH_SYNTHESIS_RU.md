# Research synthesis for Execution Brain V9

- **CASTER** proposes context-aware dynamic routing rather than using strong models uniformly; its paper reports major cost savings while matching strong-model success in evaluated domains. citeturn499491academia12
- **Agent-as-a-Router** frames routing as Context→Action→Feedback→Context, learning from execution-grounded outcomes rather than one-off classification. citeturn499491academia15
- **MAGE** treats memory as execution-state management so failed branches do not pollute the active state; **Agent-BRACE** motivates explicit uncertainty/belief state. citeturn499491search2turn499491search3
- **MESA** reports benefits from task-adaptive memory-structure selection, while **ACON** learns from compression failures. citeturn499491search10turn499491search0
- Recent horizon-length work finds that reducing effective horizon improves stability in long action sequences. citeturn499491search5
- Microsoft’s **Universal Verifier** emphasizes specific non-overlapping rubrics and separating process from outcome; its reported false-positive rates are far lower than simpler verifier baselines. citeturn561429view0
- Chrome warns that excessive WebMCP tools consume context and increase latency/confusion, supporting dynamic minimal tool sets. citeturn856007search11
- Stagehand’s current architecture explicitly uses AI for unfamiliar workflows and caches/self-heals repeat actions so later runs can avoid LLM inference. citeturn856007search2
- Grok Build supports parallel/background workflows/subagents, fitting the role of an asynchronous strategic lane. citeturn856007search5turn856007search6
