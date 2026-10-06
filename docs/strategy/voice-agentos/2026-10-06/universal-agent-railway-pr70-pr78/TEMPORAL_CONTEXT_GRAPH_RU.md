# Temporal ContextGraph + ContextPack Compiler

Lifetime context stays local; models receive only a bounded evidence subgraph.

Nodes: Source, Artifact, Conversation, Message, Person/Agent, Account, Workspace, Site, Repo, File, Document, Goal, Decision, Action, Effect, Receipt, Skill, Surface, Event, Claim, AcceptanceCriterion.

Edges: DERIVED_FROM, VERSION_OF, PART_OF, MENTIONS, SUPPORTS, CONTRADICTS, SUPERSEDES, PRODUCED_BY, EXECUTED_ON, OBSERVED_AT, RELATED_TO, BELONGS_TO_PROJECT, REQUIRES, BLOCKS, SATISFIES, SAME_IDENTITY_AS.

Every edge is temporal/provenanced: valid_from, valid_until, observed_at, exact source refs.

ContextPack input: GoalState + SurfaceGraph + acceptance.
Output: exact evidence refs, relevant environment conventions, prior successful trajectories, contradictions, coverage gaps, candidate skills/providers.

Retrieval: identifiers/labels → FTS → graph neighborhood → optional embeddings → temporal/freshness ranking. Embeddings help discovery but never replace exact refs.
