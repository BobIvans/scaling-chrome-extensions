# Состояния и восстановление

CodeAttempt: DRAFT → INPUT_PINNED → PATCH_READY → REVIEWED → FINAL_TREE_VERIFIED → MERGE_PENDING → MERGE_VERIFIED. Любой drift переводит affected evidence в STALE, ошибка в FAILED, неоднозначный внешний результат в UNKNOWN_EFFECT. User assertion хранится рядом, но не заменяет переход.

UpdateAttempt: RELEASE_BOUND → ACQUIRED → STAGED → REHEARSAL_PASSED → QUIESCENCE_PENDING → ACTIVATING → INSTALLED_OBSERVED → CANARY_RUNNING → QUALIFIED. Состояния ROLLBACK_PENDING/ROLLBACK_VERIFIED/RECOVERY_REQUIRED сохраняют old/new digests и data plan. QUALIFIED относится к заданному device/build/profile; usable — вычисляемое отдельное свойство.

NodeAttempt: WAITING → READY → RESERVED → RUNNING → CHECKPOINTED → VERIFIED. Также BLOCKED_BUDGET, BLOCKED_RESOURCE, BLOCKED_POLICY, STALE_INPUT, UNKNOWN_EFFECT, CANCELLED, FAILED, DEFERRED. Лишь VERIFIED с актуальными bindings может быть reused. CANCELLED terminal для intent revision; новое явное intent получает новую revision, не стирает старое.

Каждый transition содержит event_id, campaign/node/attempt/intent revision, previous/new state, expected record revision, lease epoch, input/policy/contract hashes, evidence refs, reason, UTC observation time и clock context. Durable storage commit предшествует подтверждению UI. Replay projections не создаёт effects.

## Crash boundaries

1. До reservation: ничего не удержано; retry допускается после fresh eligibility.
2. После reservation до dispatch: recovery определяет, был ли dispatch durable; наличие lease не proof отсутствия эффекта.
3. После отправки до receipt: UNKNOWN_EFFECT. Reconcile idempotency key/status/pinned target; без внешнего proof не повторять write.
4. Во время merge: read remote PR/ref/diff, сверить revision. Не создавать второй merge при pending response.
5. Во время download: сверить части/hashes/staging; не затрагивать active installation.
6. Во время migration: production DB неизменна; снять incomplete rehearsal и сохранить capsule.
7. После переключения pointer до installed receipt: наблюдать actual active build/process/data, затем записать receipt конкретной попытки.
8. После canary fail: rollback только по proved data compatibility; иначе recovery required, dependent workflows blocked.
9. После STOP: отмена намерения durable, текущий owner прекращает/сверяет effects; новые jobs не возобновляют отменённую revision.

Local transactional fencing предотвращает запись устаревшего worker в store. Для внешних эффектов fence реализуется владельцем операции/remote precondition; если remote не поддерживает fence, dispatch owner serializes и reconciliation обязателен. Не обещать exactly-once вне этого протокола.

BudgetReservation: RESERVED → SETTLED/RELEASED, либо UNKNOWN_COST. Upper bound non-negative; actual provider usage отдельно. Lease expiry не освобождает неопределённый cost. UI subscription quota и API деньги разные budget accounts.
