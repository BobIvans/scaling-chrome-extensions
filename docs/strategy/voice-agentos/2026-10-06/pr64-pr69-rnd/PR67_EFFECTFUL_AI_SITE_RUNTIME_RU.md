# PR67 — Qualified Effectful AI-Site Runtime

## Thesis

Довести существующий `site_adapter.py` from substrate to qualified runtime for effectful AI sites. Не делать generic blind click/send. Каждое отправление привязывается к exact site identity, exact composer, durable EffectIntent и reconciliation.

## Existing implementation to preserve

`SiteAdapterRegistry/Runtime` уже имеет profile/contract digest, qualification object, bind, prepare, outbox, `send_once`, Core effect transitions, UNKNOWN reconciliation и read. PR67 расширяет и квалифицирует этот owner.

## Required contracts

### Exact identity
Binding должен различать как минимум:
- origin/provider;
- account identity evidence;
- workspace/org/project;
- conversation/thread;
- branch/session where applicable;
- tab/document token;
- adapter version/code digest/contract digest.

Нельзя send, если required identity field UNKNOWN/AMBIGUOUS или drifted после prepare.

### Composer binding
- exact element/fingerprint;
- visibility/enabled state;
- focus/selection semantics;
- human activity lease;
- pre-draft empty/current value observation;
- max text bytes;
- attachment state if provider supports attachments.

### Draft prepare + independent readback
`prepare()` обязан после mutation прочитать composer заново и доказать exact draft digest. Если readback differs — no send.

### Send once
- durable outbox bytes/hash;
- EffectIntent before dispatch;
- exact send control fingerprint;
- one dispatch attempt per effect revision;
- post-send observation tied to outgoing draft digest/message identity;
- exception/timeout → reconcile, not blind repeat.

### UNKNOWN reconciliation
- observe conversation/outgoing message history;
- if exact outgoing evidence exists → OBSERVED;
- if independent evidence proves not applied → NOT_APPLIED may permit a later re-dispatch;
- ambiguous remains UNKNOWN and blocks same composer/conversation WRITE resource.

### Response stream reader
- response message identity/branch;
- streaming vs final state;
- chunk/result digest;
- attachments/artifacts inventory;
- completion/cancel/error reason;
- preserve raw archive in Library when useful.

## Qualification corpus

Frozen fixtures + device canary must include:
- wrong account;
- wrong workspace;
- wrong conversation;
- composer replaced between bind and send;
- selector drift;
- page navigation/document token drift;
- duplicate/outgoing already present;
- send timeout after actual dispatch;
- human takeover during prepare;
- response branch change;
- virtualized message list;
- restart in DISPATCHING/UNKNOWN.

## Integration with PR66

Qualified AI site becomes a `browser_site` System-2 provider. Provider request uses PR66 contract; actual message dispatch uses PR67 exact effect contract. Provider registry does not bypass site qualification.

## Parallel semantics

- two different qualified conversations may run concurrently if resources disjoint;
- same composer/conversation WRITE resource serializes;
- read-only observation may continue while another site is sending;
- human foreground lease wins.

## Acceptance

- no send on unqualified profile/code/contract drift;
- exact draft readback before send;
- duplicate prevention survives restart;
- timeout never automatically resends;
- wrong-target fixture always blocks;
- account/conversation drift invalidates binding;
- response capture returns typed COMPLETE/STREAMING/FAILED state;
- all effect receipts are Core-bound and inspectable;
- live provider/device qualification remains explicit per provider/account profile.
