# Grok Supervisor Protocol

## Persistent session
One optional long-lived Grok session acts as strategist/critic. It stores only compact mission summaries, verified milestones, unresolved blockers and prior supervisor recommendations.

## SupervisorPacket
Send only on escalation:
- goal + active subgoal;
- remaining acceptance clauses;
- verified progress since last Grok review;
- new high-value evidence/contradictions;
- failed strategy/no-progress summary;
- active lanes;
- available capabilities;
- one exact strategic question;
- requested output schema;
- prohibited effects.

## Expected GrokSupervisorProposal
- strategic assessment;
- likely blocker;
- requested next evidence;
- proposed strategy change;
- possible code/capability gap;
- risk flags;
- what observation would falsify the recommendation.

## Asynchronous rule
While Grok thinks, safe local lanes continue. If the goal, subgoal or evidence changes materially, the eventual Grok result may be rejected as stale.

## Delta rule
Do not resend full mission history. Accumulate verified deltas and send only strategy-critical changes.
