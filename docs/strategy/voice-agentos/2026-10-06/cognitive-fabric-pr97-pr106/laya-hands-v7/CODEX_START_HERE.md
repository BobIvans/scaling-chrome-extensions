# Codex Start Here — Laya Hands V7

Focused addendum to PR97–PR100. Do not create a separate implementation PR for V7.

Implementation:
1. finish missing foundations before PR97;
2. PR97 adds TaskPacket/session/provider modality contracts;
3. PR98 adds secure authorized transports;
4. PR99 adds PacketHand/prefetch/cost logic;
5. PR100 adds Grok/ChatGPT multimodal persistent relay and attachment transports.

Never execute provider prose directly.
Never upload arbitrary local files.
Never make web3 research mode capable of wallet signing.
Tests must cover text-only, document, image, mixed packet, attachment drift, provider failure and unknown send.
