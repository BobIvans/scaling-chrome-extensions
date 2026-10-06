# Grok / ChatGPT Multimodal Relay

Grok can be a deep-thinking lane for protocol docs, screenshots, CSV/XLSX, code/log bundles and web3 observations. Current xAI APIs support files and mixed text/file/image inputs; Grok web supports broad file uploads.

For code/repo work prefer Grok Build headless/ACP. For human-visible continuity, use the exact Grok web conversation.

AgentOS:
1. binds exact session;
2. builds a bounded TaskPacket;
3. attaches allowed files/images;
4. sends one bounded question;
5. keeps safe local lanes running;
6. captures raw response/artifacts;
7. stores them in Library;
8. converts them to CognitiveProposal;
9. compiles/validates the next local action.

ChatGPT uses the same TaskPacket abstraction. ProviderGraph discovers modality support at runtime. Local Library remains canonical memory.
