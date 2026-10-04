# Предлагаемый протокол готовности и доказательств

Это design extension V5. Названия полей ниже не являются уже поддерживаемыми
API-командами SCE. Перед реализацией согласовать их с действующими DTO и owners;
сохранённые интерфейсы V4 имеют собственную schema.

## Разделение состояния

| Объект | Значимое состояние | Что ещё нельзя вывести |
| --- | --- | --- |
| Definition | PROPOSED → EXPERIMENTED → DECIDED | Решение не означает наличие handler |
| Code | PLANNED / UNVERIFIED / PARTIAL / IMPLEMENTED_SCOPED | Local test не означает installed release |
| Evidence | PASS / FAIL / UNKNOWN / STALE / NOT_RUN | PASS относится только к frozen criterion/scope |
| Delivery | PREPARED / DRAFT_OBSERVED / SEND_INTENT / SENT_OBSERVED / UNKNOWN_EFFECT | Отправлено не означает прочитано или использовано |
| Release | CANDIDATE → STAGED → INSTALLED → CANARY_PASSED | Merge/download не означает установку |
| Capability | DECLARED / DEPENDENCY_MISSING / UNQUALIFIED / QUALIFIED / STALE / QUARANTINED | Объявление не разрешает автономное выполнение |
| Aim | OPEN / BLOCKED / VERIFIED_SCOPED / USABLE_SCOPED / DEFERRED | Узкая проверка не закрывает широкую feature card |

При изменении source/HEAD/profile/adapter/build изменяются только зависимые
проекции. Старые receipts остаются в истории; новый статус сообщает причину
stale. Никакой переход не основывается исключительно на imported model claim.

## Минимальные evidence envelopes

Общие поля proposal: schema/version, receipt_id, criterion_id/criterion_revision,
attempt_id, subject identity, exact source/build/config hashes, observer/test
identity/version, observed_at и clock uncertainty, scope, outcome,
artifact_refs с hashes, validity_inputs, limitations. Поля «подпись» не
доказывают authenticity без выбранного доверенного issuer/key contract.

**SourceCoverageReceipt:** snapshot SHA/scope, expected tree manifest hash,
entry counts by outcome, per-entry paths/object/ranges/status/reason,
part manifest hash, byte reconstruction outcome. Отдельные coverage показатели:
accounted, raw captured, extracted, packet included, delivered, acknowledged,
used. Нельзя переносить полноту первого показателя на последний.

**DeliveryObservation:** task/packet/part identity/hash, provider/account/chat,
binding revision, adapter version, observed draft/send event, remote
message/attachment identity когда доступна, uncertainty interval, retry/reconcile
history. UNKNOWN_EFFECT имеет отдельный journal entry. Факт полученного ответа
не означает, что модель использовала каждый приложенный источник.

**CriterionEvidence:** frozen input/config, registered verifier, output artifact,
outcome, execution mode и exact build. Путь local_test не запускает arbitrary
commands из импортированного result; profile lookup/registration принадлежит
операторскому существующему owner.

**InstalledVersionReceipt:** candidate/source/assets hashes, installer/updater
version, actual device/OS/build identity, schema before/after, activation,
canary observations, previous restore point и rollback outcome. Linux fixture
или CI не заполняет device field как Windows success.

**CapabilityQualification:** capability ID/version и typed args/effects,
installed build, dependency versions, resource identities, profile revision,
preconditions, verifier cases, normal/fault results, valid scope,
invalidation rules. Skills/templates ссылаются на эту revision.

**GoalGateEvaluation:** aim/criterion revision, required receipts, каждое
PASS/FAIL/UNKNOWN/STALE, evidence scope, named gaps, next request и evaluator
version. Сводное usable возможно только в обозначенной области. Частичная
готовность сохраняется; missing evidence не подменяется optimistic success.

## Надёжность и польза

Заморозить task corpus и manual baseline. Denominator — все started attempts;
отдельно показать completed, failed, unknown, cancelled и blocked. Human assisted
успех не считается unattended успехом. Retries остаются внутри attempt history;
неудачные branches и costs не удаляются из расчёта.

Измерять на каждом этапе success rate, omission/error rate, time to useful
result, вмешательства человека, latency, CPU/RAM/disk, provider usage и полную
цену попытки. Shared dataset/пересказы одного источника не являются независимыми
подтверждениями. Несколько моделей с одним input не создают независимый ground
truth. Сравнение по одинаковым inputs и заранее выбранным критериями.

Начальные correctness gates: нет silent tree omission; нет wrong-target send;
нет повторения unknown external effect до reconciliation; нет criterion closure
по stale/unknown evidence. Performance и utility thresholds предложить до
пилота, после baseline; this ZIP не заявляет измеренный universal success rate.

## Функциональное определение будущей automation

Input contract → source/target binding → typed plan → eligibility/admission →
durable checkpoint → registered effect → independent observation → goal gate.
Каждый handler объявляет cancellation point, repeatability/idempotence,
uncertainty, resource locks, retry/timeout budget и recovery output.
One-shot UI кнопка создаёт такую сохраняемую кампанию, а не бесконечный цикл.
Документы, repo text и AI output остаются контекстом; они не меняют trusted
action profile. User grant может быть долговременным в явно заданной области.
