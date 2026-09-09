# Provider routing for OCC/Hermes

Hermes should be the stable agent API; model providers are replaceable capacity behind it.

Recommended policy:

1. Start with the cheapest/free provider that meets tool/reasoning requirements.
2. On quota/429/provider failure, fail over to the next configured provider.
3. Keep research, coding and cheap extraction routes separate when useful.
4. Allow custom OpenAI-compatible routers so OmniRoute/Birouter/OpenRouter/OpenCode-like gateways can be used without changing OCC.
5. Track provider, model, latency, failure and quota metadata per run in the control plane.
6. Never obtain or use provider credentials without the provider/user's authorization. Free/promotional quotas are opportunistic and can change at any time.
7. Do not store provider master keys inside repository snapshots, page captures or model prompts.

OCC keeps a direct universal provider adapter as a low-overhead fallback, while remote Hermes is preferred for multi-step research/delegation/memory/scheduling.
