# RND-44 — Capture portfolio by information gaps
**Статус:** new; proposed R&D, не установленная интеграция.

## Зачем
Постоянная запись всех экранов не равна лучшему контексту.

## Устройство
Сначала дешёвые process/file/UIA/DOM metadata; audio/screenshot только разрешённо и по необходимости; отдельный coverage planner.

## Эксперимент
Сравнить always-on every-sensor и task-conditioned sensor portfolio на одинаковых задачах.

## Acceptance
Меньше peak RAM/CPU и privacy exposure при не худшем task-evidence recall.

## Функции
- `identify_capture_information_gap()`
- `select_observation_portfolio()`
- `measure_sensor_marginal_coverage()`
- `retire_redundant_capture_channel()`

Requirements: REQ-033 REQ-036. Sources: S24 S25.
