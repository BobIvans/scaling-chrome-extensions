# Каталог функций → запросы Laya

`laya_catalog.py` сохраняет входной каталог без изменений и группирует его
карточки по capability. Для каждой функции создаётся один отдельный JSON-запрос
к Laya и индекс всех её исходных CAND. Двадцать аспектов функции остаются
двадцатью проверяемыми требованиями; количество реальных PR определяется пробелами кода.

Пример из корня репозитория (Python, без сторонних пакетов):

```bash
python content-lab/laya_catalog.py --catalog /path/to/authorized-catalog.json --out /path/to/new-review-package
python -m unittest discover -s content-lab -p 'test_laya_catalog.py' -v
```

Каталог должен содержать `candidate_count`, `capability_count`,
`slices_per_capability` и массив `items`. Проверяются уникальные CAND,
непротиворечивая функция/repository внутри CAP, число и уникальность аспектов,
обязательные строки и критерии приёмки. Некорректный вход отклоняется до записи.
Существующий output не перезаписывается. Вход ограничен 16 MB / 20 000 карточками.

Выход: `SOURCE_CATALOG.json` (исходные байты), `OCC_LAYA_CATALOG_INDEX_RU.json`
и `laya_requests/CAP-*.json`. В индекс включены исходный SHA-256 и явные статусы:
`inference_performed=false`, `execution_queue_compatible=false`.
Каталог и медицинские/частные исходники остаются у оператора; в этот PR они не входят.

Запросы содержат `state`, `questions`, `model="multilingual"`, `max_len=8192`
и предназначены для `POST /v1/systemone`. В прочитанном upstream `laya/serve.py`
(Git blob `59a3075337cb83569f05c2af8139bbfdc8f14a60`) одиночный обработчик
передаёт `max_len` в модель, а batch-обработчик передаёт только state/questions/model.
Поэтому пакет не рассчитывает на поддержку override в batch. Совместимость
установленной версии, длина в реальном токенизаторе, качество и RAM требуют
отдельного локального испытания. Проверка числа символов не доказывает укладывание
в контекст. Модель и веса здесь не устанавливаются и не запускаются.

Официальные источники:
- https://github.com/NandhaKishorM/laya
- https://github.com/NandhaKishorM/laya/blob/main/laya/serve.py
- https://huggingface.co/convaiinnovations/laya-multilingual

Laya предлагает направление проверки. Её ответ не является доказательством,
разрешением на выполнение, тестом, code gap или основанием для merge.
Перед передачей в существующую `automation_core.enqueue` нужны текущий owner,
проверка пересекающихся PR, конкретный diff/профиль задания и критерии результата.
Сам компилятор не вызывает enqueue, shell, сеть, API, браузер, signer или sender.
Существующие очередь, Native Host и CI consumer сохраняют свои роли.

Связь с roadmap: CAP-046/F-23 (маршрутизация) и CAP-035/F-34 (прослеживаемость)
тематическая. Этот узкий компилятор не закрывает эти функции целиком и не
заменяет следующий F-16 — получение CI с привязкой к коммиту.
