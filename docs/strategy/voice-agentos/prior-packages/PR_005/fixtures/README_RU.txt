64 synthetic expected entries, не output работающего приложения.
44 ordinary inputs + 20 boundary cases. 56 INDEXED, 6 EXCLUDED, 2 ERROR.
Из 56 raw-captured: 49 text-eligible, 3 binary/non-UTF8, 4 LFS candidates.
15 gaps (64-49) в EXPECTED_GAPS. Categories overlap; не суммировать raw+text.

input_bytes/ содержит синтетические входы для tests, в том числе безопасные
dummy protected-name/heuristic specimens. Их наличие в test fixture не
разрешает app выводить реальные protected bytes. Metadata-only submodule,
unsupported path, oversize и unavailable blob задаются fault recipes; fixture
не обещает portable materialization таких путей на Windows.

Missing local LFS payload не заявлен: payload availability NOT_CHECKED,
external_payloads_complete=null. Pointer Git bytes проверяются отдельно.
raw_integrity NOT_RUN во всех DTO; file hashes fixtures — ожидаемые данные,
а не receipt проверки app. New Native PAGE показывает все entries до EOF.
Для app tests ожидаемый ledger сверяют с фактическим output adapter.
