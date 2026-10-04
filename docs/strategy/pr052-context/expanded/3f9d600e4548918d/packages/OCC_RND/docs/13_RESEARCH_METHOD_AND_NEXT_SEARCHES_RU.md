# Как искать ещё более сильные подходы

## Не расширять стек без конкретного вопроса

Каждое новое repo/model оценивается по одному пробелу: нужна ли лучшая речь, маршрутизация, кодогенерация, UI grounding, extraction, retrieval, execution reliability или evidence? У кандидата фиксируются creator source, revision/date, licence, runtime, dataset, benchmark protocol и failure modes. Звёзды GitHub и demo не являются нужным benchmark.

## Приоритетные дальнейшие поиски по первичным источникам

1. **Decision models:** Laya calibration/typed schema budget, Jev harness, hierarchical routing vs flat labels, abstention under shift. Проверять не общую accuracy, а cost-weighted wrong-action rate и risk-coverage curve.
2. **Demonstration-to-skill:** OpenAdapt verified outcome, UFO tool/GUI coordination, Agent-S and UI-TARS recovery. Искать сохранение provenance, narrow locator repair, postcondition oracles, replay when software updates.
3. **Accessible voice:** ASR robustness on spontaneous RU+code, endpointing/negation, alternative input, screen-reader focus. Искомый результат — task completion и corrections, не только WER.
4. **Executable knowledge library:** original→derived→claim→test→receipt relationships; incremental snapshots; branch-aware conversations; negative memory; deterministic context compiler.
5. **Code understanding:** точный entrypoint/plugin inventory, import graph, reachability, dead/config-only code, test evidence vs function existence. AST-signal нельзя выдавать за доказанный bug.
6. **World/decision models:** point-in-time Web3 decision episodes, counterfactual labels, target leakage, allocation under account conflicts. Historical Chronos/TimesFM/TabPFN suggestions требуют новой проверки до включения.
7. **Information acquisition:** какую следующую RPC/state/test observation купить/собрать, чтобы изменить решение; distinguish cost/rights/staleness. Предпочесть полезный missing-data test новой спекулятивной стратегии.

## Единый evaluation corpus

Создать versioned набор реальных задач пользователя, обезличенный по необходимости: найти старую идею; собрать >20 docs; обнаружить незапущенный proposal; проверить installed mismatch; воспроизвести bug; открыть нужную строку; отменить неверно распознанный intent; объяснить no-edge result. Зафиксировать train/calibration/holdout заранее, разделять по источникам/времени, не обучаться на test outcomes.

Метки: correct intent/slots/effects; successful verified outcome; elapsed time; compute/API cost; corrections; unsafe actions; lost evidence; reproducibility; privacy leaks. Сравнить baseline A (deterministic), B (router), C (router+LLM), D (always-LLM). Повышение сложности оправдывается только измеримым улучшением с учётом доверительных интервалов и риска.

## Обновление каталога

Не делаем в этом чате фоновый мониторинг. Предлагаемый локальный workflow после реализации может по расписанию читать approved release feeds/commit metadata, сохранять diff и отмечать изменившиеся API/model cards. Он не должен сам обновлять production dependencies: сначала compatibility тест и review.
