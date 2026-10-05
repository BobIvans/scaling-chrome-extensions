# Universal Workspace V3 — Notion-like Library + Repos + AI Targets + Missions

Date: 2026-10-05

This document extends the Universal Long-Horizon Laya Agent V2 into an operator-facing workspace. It does not create a second application or second store. It reuses the existing `one-click-context/library.html`, `workspace.mjs`, `agent.mjs`, `campaign-ui.mjs`, Desktop shell, Context Library, repo capture/groups and durable action runtime.

## Product thesis

The app should feel like a personal Notion/IDE/agent workspace rather than a single-purpose Grok automation window.

Everything the user has collected or observed becomes a first-class Library record with provenance. Repositories have their own workspace. Conversations have their own workspace. Missions combine chosen context with a chosen target and an action goal. Automations persist long-running recipes. Skills expose qualified capabilities. Evidence shows what actually happened.

Core navigation:

1. **Home / Inbox**
2. **Library**
3. **Conversations**
4. **Repositories**
5. **Context Cart**
6. **AI Targets**
7. **Missions / Actions**
8. **Automations / Campaigns**
9. **Skills / Tools**
10. **Evidence / Receipts**
11. **Work Sessions**
12. **Settings / Policies**

## 1. Home / Inbox

Purpose: zero-friction capture and continuation.

Show:
- recent imported files/chats/repos/results;
- active missions;
- waiting/blocking missions;
- latest AI replies;
- unclassified sources;
- stale context;
- capability gaps;
- due automations;
- "continue last work session".

Quick actions:
- Add files
- Add local repo
- Clone GitHub repo
- Capture current Chrome tab
- Capture selected tabs
- New mission
- Resume mission
- Voice command
- Search everything

## 2. Library

Universal source database.

Record types:
- note
- document
- chat/conversation
- browser turn
- attachment
- web page
- repo snapshot
- repo logical group
- code symbol
- test/CI result
- terminal output
- AI result
- task/mission result
- image/media
- imported ZIP/archive
- Git/GitHub receipt
- skill/tool artifact

The Library must support:
- full-text search;
- project/session/source/type/status filters;
- user tags;
- auto-suggested labels;
- manual correction;
- pin/favorite;
- collections;
- backlinks/related items;
- versions/history;
- valid-from/valid-until;
- conflict groups;
- source authority;
- freshness/staleness;
- exact provenance;
- hidden/tombstoned records;
- "add to Context Cart";
- "start mission from this";
- "ask selected AI about this";
- "show dependent packets/missions".

The existing project/session facets remain supported; V3 expands them instead of replacing them.

## 3. Conversations

A dedicated view for Grok, ChatGPT, Codex/Work exports, Telegram, other chat sources.

Each conversation page:
- provider/account/workspace/conversation identity;
- captured turns;
- branches;
- attachments;
- links;
- code blocks;
- coverage/gaps;
- tags/projects;
- open loops / unresolved questions;
- related missions;
- related repo commits/PRs;
- "Observe live";
- "Add selected turns to Context Cart";
- "Continue in selected target";
- "Extract tasks";
- "Extract decisions";
- "Extract sources";
- "Extract capability gaps".

This implements the earlier `chat_history_to_open_loops` concept.

## 4. Repositories

Repository Workbench.

Actions:
- Open local repository
- Clone GitHub repository
- Fetch/update
- Pin branch/ref/commit
- Whole repo initial scan
- Resume/pause scan
- Build logical groups
- Whole Repo Indexed pack
- Interconnected Files pack
- Tech Debt pack
- Error/Broken Paths pack
- High Value Files pack
- Test Impact pack
- Runtime Path pack
- Delta pack
- Custom goal-driven pack

Each repo gets:
- snapshot history;
- HEAD/tree;
- file/symbol/test/dependency indexes;
- logical groups;
- open findings;
- missions;
- PRs/commits;
- recent failures;
- skill/capability references;
- stale packets after HEAD drift.

## 5. Context Cart

The user can combine arbitrary records from Library/Conversations/Repos.

Cart shows:
- selected records and exact revisions;
- token/byte budget;
- logical grouping;
- duplicate detection;
- conflicts;
- missing dependencies;
- source coverage;
- why-selected reason;
- receiver profile (Grok/Codex/ChatGPT/etc.).

Actions:
- Build packet
- Split into logical parts
- Export TXT/MD/JSON
- Send to selected AI Target
- Save as reusable Context Set
- Attach to Mission

This restores the earlier `Library Navigator + Chunk Workspace + Context Cart` concept.

## 6. AI Targets

Visible target list:
- Chrome tabs;
- Grok/Grok Build web sessions;
- headless Grok Build;
- ACP sessions;
- optional APIs/CLI providers.

UI separates:
- Source target: observe/read.
- Action target: allowed to fill/send.
- Result target: where response is expected.

Exact TargetBinding is always shown. Title/URL/provider guess is not authority.

## 7. Missions / Actions

Mission form:
- goal;
- expected outcome;
- acceptance clauses;
- constraints;
- prohibitions;
- selected context/cart;
- repo/snapshot;
- AI target;
- effect scope;
- time/budget;
- parallelism;
- stop policy;
- automation mode.

Modes:
- OBSERVE
- PREVIEW
- RUN_REGISTERED
- LONG_HORIZON
- WAIT_AND_RESUME

Mission page:
- H2 strategy;
- H1 frontier;
- H0 next step;
- Laya decision;
- current leases/resources;
- progress delta;
- evidence;
- blockers;
- receipts;
- STOP / Pause / Resume / Human takeover.

## 8. Automations / Campaigns

Saved long-running recipes:
- watch selected tab/chat;
- watch repo/PR/CI;
- periodic repo qualification;
- ingest new attachments;
- process Inbox;
- continue unresolved mission;
- scheduled research;
- wait for event/quota;
- create a report;
- background context prefetch.

Each automation stores:
trigger, goal revision, source scope, target bindings, recipe version, budgets, freshness, missed-run policy, no-progress threshold, stop conditions, next due time.

## 9. Skills / Tools

Capability registry:
- name/version;
- inputs/outputs;
- aliases;
- effect class;
- executor;
- verifier;
- required permissions;
- supported resources/providers;
- qualification state;
- dependency hashes;
- source/license;
- failures/counterexamples;
- rollback version;
- usage history.

Unknown capability → GapSpec → candidate → STAGING → CANARY → REGISTERED.

## 10. Evidence / Receipts

Timeline of truth:
- source capture receipts;
- target bindings;
- EffectIntent;
- browser send/readback;
- downloads;
- tests;
- Git commits;
- PR/CI/merge;
- build/install/device;
- verifier results;
- UNKNOWN/BLOCKED/STALE.

A model saying "done" is never evidence by itself.

## 11. Work Sessions

A session bundles:
- selected tabs/windows/repos;
- voice/text events;
- current mission(s);
- snapshots;
- outputs;
- open loops;
- last checkpoint.

"Continue last work session" rebuilds the frontier from current evidence rather than replaying old clicks.

## 12. Settings / Policies

- data roots;
- projects/tags taxonomy;
- provider adapters;
- browser profiles;
- Laya checkpoint/runtime;
- models/providers;
- effect grants;
- allowed roots/origins;
- budgets;
- schedules;
- privacy/redaction;
- default verifier policies;
- device qualification status.

## UX rule

Every object in the UI should support:
**Open → Label → Relate → Add to Context → Start Mission → Inspect Evidence**.

That common interaction makes arbitrary sources composable without building a custom screen for every scenario.
