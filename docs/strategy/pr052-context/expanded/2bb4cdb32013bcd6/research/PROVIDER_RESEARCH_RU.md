# Provider notes · 2026-10-04

Официальные ссылки и ограниченные observations сохранены в PRIMARY_SOURCE_NOTES.json. Сетевые API calls не выполнялись; account rate plan не проверен. Исторические endpoint names/«60 RPM» из памяти не являются runtime config.

Jupiter: rate-limit policy действует на organisation/main bucket; concurrent strategy workers должны брать разрешение у общего broker. API limits и headers могут меняться, при actual acquisition сохранить documentation/policy version и наблюдаемые ответы. [Источник](https://developers.jup.ag/docs/portal/rate-limits).

Solana: base/priority и failure costs учитывать отдельно, pinned transaction format определяет формулу. [Источник](https://solana.com/docs/core/fees/fee-structure).

Marginfi/P0: fee documentation различает program и frontend costs; per-program identity и exact on-chain state проверять перед economic verdict. [Источник](https://docs.marginfi.com/protocol-overview/fees). Original program-source URL перенаправился на [0dotxyz/marginfi-v2](https://github.com/0dotxyz/marginfi-v2); это observation redirect, не claim об audited compatibility.

[Kamino SDK](https://github.com/Kamino-Finance/klend-sdk) — primary code source для future exact-version audit. Из чтения repository landing page не следует поддержка flashloan handler в Studious.

Funding/cross-chain/intent settlement providers не выбраны заранее: исследовательский contract сначала offline, protocol-specific real-data/settlement adapter требует own source/version/evidence. New official sources входят в atlas с date, claims и missing requirements.
