# Главное уточнение: много наблюдателей, много изолированных исполнителей, один владелец конфликтующего эффекта

## 1. Никакого глобального запрета параллельной записи
Микрофон → один device stream → несколько потребителей ASR/VAD/архиватора. DOM, accessibility, Git и terminal collectors одновременно создают свои observations. Каждый имеет namespace/sequence/source revision. Same raw bytes могут храниться один раз, но все ссылки происхождения сохраняются.

БД физически может сериализовать короткие транзакции. Это не значит, что она сериализует весь процесс записи, ASR, поиск и запуск работы. Контент capture append-only; модель не переписывает original history. Для больших media — потоковая spool + cursor + retention, а не RAM buffer; данный lab этого не реализует.

Параллельные code writers также допустимы в разных worktrees. Общая branch/head publication контролируется отдельно. Несколько реальных действий над разными ресурсами выполняются одновременно. «Один writer» относится к конкретному неидемпотентному effect target, не к машине в целом.

## 2. Пять режимов, которые нужно выбирать явно
| Режим | Для чего | Когда завершать |
|---|---|---|
| COMPLEMENTARY_UNION | Собрать разные наблюдения одного процесса | По completion/coverage/deadline; не по первому ответу |
| REQUIRED_EVIDENCE_JOIN | Код + тесты + актуальная цель | Когда все обязательные доказательства присутствуют |
| FIRST_VERIFIED | Альтернативные способы получить одинаковый результат | Первый прошедший независимые checks, не первый fastest text |
| PARTITIONED_MAP | Части большого корпуса или разные effect targets | Все нужные partitions с coverage ledger |
| PREPARE_COMMIT | Патчи, обновления, внешний submit | Параллельная подготовка, одна scoped activation/operation |

## 3. Самый быстрый путь к пользе в нашем проекте — гипотеза
Не ждать новую большую AgentOS. Сохранить SCE content.sqlite3 / queue/review owners и добавить desktop client + event intake. Первая команда строит source-bound handoff для Studious из текущего source snapshot и known blocker. Голос и модели маршрутизации добавляются поверх того же typed request.

Проектная pipeline:
```
voice/text → IntentSpec revision
  ├─ live workspace state       ┐
  ├─ Git/symbol/test context    ├─ evidence-ready handoff v1 → chosen AI
  ├─ accepted goals/history    ┘          ↑                 ↓
  └─ allowed archive ingestion → late delta        NEED_CONTEXT / patch
                                     ↓                    ↓
                           freshness check          isolated test branch
                                     └──── verifier ──────┘
                                             ↓
                                   scoped install / receipt
```
Не нужно запускать весь набор распознавания/планирования на каждом слове. Часть read-only prefetch выполняется заранее; stable intent имеет revision. Новое «нет, не этот проект» отзывает pending effect.

## 4. ZIP и текст чата — совместимы, но не независимые голоса
ZIP — versioned procedures/contracts/backlog. Текущий текст пользователя — intent, scope и обновления требований. Repo — фактический source snapshot; execution receipts — доказательства запуска. Они обрабатываются параллельно в разных authority lanes и соединяются в один goal/evidence graph.

Если ZIP повторяет текст чата, это одна lineage, не два подтверждения истины. Если старый ZIP противоречит последней явной инструкции пользователя, instruction обновляет planned behavior, но не переписывает факты в source/test evidence.

## 5. Отсутствующие права/данные не выводятся из желания «всё автоматизировать»
Источник может быть AVAILABLE, PARTIAL, NOT_CAPTURED, UNSUPPORTED, DENIED, STALE или ERROR. Эти статусы повышают честность availability карты. Полнота относится к объявленному scope и snapshot, а не к «любой информации вообще». Нельзя наблюдением страницы гарантировать захват невидимой части истории.

## 6. Производственная граница
Reference lab — проверка алгоритмических contracts на synthetic data. Не готовый агент, не security sandbox, не streaming TB store, не real voice performance. В app существующий Core остаётся владельцем прав, очередь не дублируется. Реальный update сохраняет attestation/digest, permission diff, smoke test, one activation и ограниченный rollback.
