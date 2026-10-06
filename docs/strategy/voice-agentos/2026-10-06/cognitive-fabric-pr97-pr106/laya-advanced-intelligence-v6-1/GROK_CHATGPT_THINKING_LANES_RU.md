# Persistent Grok / ChatGPT Thinking Lanes

External AI sessions are asynchronous cognitive workers. They never own the canonical Goal.

## Grok Build
Prefer CLI/headless/ACP for coding/workspace work.
Store exact workspace, session id, role, ContextPack digest, pending question, returned artifacts and status.

## Grok/ChatGPT browser sessions
Bind exact account/conversation.

Flow:
1. select session;
2. send bounded ContextPack delta;
3. continue safe local work while provider reasons;
4. capture returned turn;
5. archive raw response;
6. convert to CognitiveProposal;
7. verify and compile the next local action.

## ChatGPT plan lane
Use the current official Sign in with ChatGPT open-source/local flow when eligible and explicitly authorized.

Important:
- it does not expose ChatGPT conversations;
- Local Library supplies context;
- runtime obeys current plan/request restrictions;
- ordinary OpenAI API remains a separate fallback.

External chat history is not mission state. Local Goal + verified state is canonical.
