# Labeling: не один мешок тегов, а несколько независимых осей

## Обязательные оси
Источник (system/file/message/URL), exact span, raw content hash, project/entity, speaker role, content role, source authority, epistemic state, valid/observed/ingested time, privacy/allowed recipients, parser/model/schema version, provenance lineage, current repo binding.

## Дополнительные оси для автоматизации
Actionability (informational/proposal/registered action), effect class, resource read/write sets, failure domain, applicability conditions, skill qualification expiry, task relevance, evidence cost, contradiction/supersedes, cache dependencies, unknown/unresolved reason.

**Не смешивать:** topic confidence с truth confidence; вероятность маршрутизатора с execution authority; «похожий документ» с одинаковым источником; repo code present с installed/device verified; historical market observation с fresh state.

## Три параллельных маршрута разметки
Правила дают источник/роль/commit/path. GLiNER [S08] выделяет entity spans по заданным labels. Laya [S06] предлагает typed категории на небольшом релевантном тексте. Reconciler сохраняет различия, а не делает majority vote истинностью.

Например, фраза assistant «PR полностью внедрён» получает `speaker=assistant`, `role=result`, `state=ASSERTED`, `authority=DATA_ONLY`. Проверенный GitHub merge receipt подтверждает состояние PR, но ещё не доказывает Windows execution или корректность каждого requirement.

Alias map: studious-pancake, Studio Spancake, flashloan bot → candidate project identity. При нескольких репозиториях с одинаковым alias требуется resolve by configured repo identity; не подменять операторский filesystem root данными из документа.

## Контекстный пакет
Task and acceptance → required evidence slots → parallel exact/semantic/temporal/source search → source integrity check → version closure → relevance ranking → contradiction ledger → selected sources + omissions → WHY_THIS_PACKET.

Неполноту показывать явно. Нельзя «подтянуть ещё всё» без ограничения рабочей памяти и API budget; можно догружать по continuation cursor сколько потребуется, сохраняя полную библиотеку.

## Быстрая библиотека
Raw intake и enrichment разделены. Inverted exact search/символы — первый маршрут. Embeddings, temporal graph и learned ranking добавляются по доказанной пользе. Хеши input/transform version обеспечивают incremental cache invalidation. Новая версия summary не стирает старую decision history.

## Пример короткого заголовка handoff
Зачем: локализовать failure, а не переписать весь repo.
Что дано: exact error, affected symbols/tests, source/decision refs.
Что неизвестно: актуальный installed device receipt.
Что требуется: минимальный patch proposal и независимые проверки.
Что запрещено: отключение тестов, live/sender, автоматическое расширение прав.
