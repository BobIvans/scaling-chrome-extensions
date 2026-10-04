# Статусы без ложного DONE

## Ingestion
DISCOVERED → RAW_STORED → PARSED → INDEXED → REVIEWED. Ошибки/исключения имеют отдельные записи; RAW_STORED не равно searchable. Resume cursor относится к snapshot и версии parser/schema.

## Evidence
ASSERTED / OBSERVED / INFERRED / VERIFIED_BY_BOUND_RECEIPT / DISPUTED / UNKNOWN. Это не одна линейная шкала уверенности: подтверждённый факт устаревает и не становится правом на действие. Source authority и truth status независимы.

## Execution
PROPOSED → CONTEXT_BOUND → PREPARED → VERIFIED_CANDIDATE → COMMIT_AUTHORIZED → DISPATCHED → OBSERVED_SUCCESS.
DISPATCHED → UNKNOWN при потере ответа. UNKNOWN → RECONCILED_SUCCESS либо PROVEN_NOT_APPLIED либо MANUAL_REVIEW. Только PROVEN_NOT_APPLIED или согласованный receiver idempotency contract позволяют повтор.

CANCEL_REQUESTED не равно CANCEL_CONFIRMED. Отмена после effect не отменяет effect. FAILED_TEST не означает FAILED_MARKET; code status не означает installed qualification.

## Update
DOWNLOADED → ORIGIN_VERIFIED → PERMISSIONS_DIFFED → TESTED → STAGED → HEALTHCHECKED → ACTIVATED. Новые permissions и необратимая DB migration требуют отдельного решения. Подпись подтверждает происхождение, не безопасность.

## Single-writer scope
Локальная SQLite транзакция может атомарно записать свой эффект и квитанцию. Между SQLite, GitHub, браузером и сетью нет общей транзакции. Внешний executor требует idempotency/reconciliation; универсальное exactly-once не заявляется.
