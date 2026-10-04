Все replies/context/paths/hashes — SYNTHETIC expected data для будущих app tests.
Это не ответы установленного backend и не Windows/device receipt.

Valid samples: hello, repo list, UTF8 search, selected context, TASK_DRAFT.txt.
Faults: invalid UTF8/duplicate JSON/NaN/trailing data, wrong protocol/operation/
profile, output/stderr overflow, timeout/nonzero/write refusal. UI fence includes
7 expected apply/discard cases. fake_adapter.py воспроизводит только fixtures;
он не читает corpus, Git, SQLite и не запускает jobs.

Byte budgets относятся к одному wire request. Fixture count не является app
limit. Actual search/context caps remain labelled bounded selection. Backend
context SHA использует default separators archived automation_core.digest;
draft file SHA рассчитывается по exact output bytes отдельно.

Чтобы tests могли запускать fake_adapter, test harness явно задаёт --scenario.
Production client argv не принимает --scenario или другие UI-supplied flags.
Actual Native result payloads и schema/version сверяются на implementation SHA.
