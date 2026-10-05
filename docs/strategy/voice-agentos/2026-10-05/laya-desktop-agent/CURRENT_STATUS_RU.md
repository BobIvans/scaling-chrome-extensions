# Что уже есть и что ещё нужно реализовать

## Уже присутствует в текущем main

### Локальный UI и Windows shell

Текущий `desktop/app.py` — локальный Tk UI. В нём уже есть настройки/подключение, поиск, выбранный контекст, экспорт manifest/history/delta, управление repo scan, окно «Текст / голос → действия», окно «Контекст и задания» и диагностика.

В репозитории уже есть `desktop/Launch_Windows.ps1` и `desktop/Install_Windows.ps1`. Значит, архитектурно мы не начинаем UI с нуля.

### Repo capture и логические связи

`repo_context.py` уже сохраняет Git source data в canonical store, а `repo_groups.py` строит логические группы/relations/segments с provenance. Поэтому новая функция должна расширять существующий grouping/projection слой, а не повторять scanner.

### Voice/text и typed intent

`desktop/actions_ui.py` уже имеет PTT/voice, typed fields, Target Binding ID и поле «Выбранный CDP tab ID». `action_intent.py` компилирует только зарегистрированные capabilities; неизвестная команда превращается в development request.

### Selected browser tab runtime

`action_runtime.py` уже имеет `BIND`, durable target rows, immutable packets, send attempts, reconciliation, STOP/fencing and result import. `browser_cdp.py` уже имеет `observe → canary → prepare → send → reconcile → read_result`.

Это означает: фундамент «выбрать конкретную вкладку и безопасно работать только с ней» уже существует.

## Пока не считать готовым

1. **Friendly tab picker.** Сейчас operator вводит/передаёт raw CDP handle. Нужен список вкладок с title/origin/provider и кнопка «Выбрать активную вкладку», после чего UI сам создаёт exact binding.
2. **Real Laya runtime wiring.** В `action_intent.LayaAdapter` есть интерфейс/abstention fallback, но текущий runtime сам отмечает Laya как unverified/direct UI fallback. Нужен pinned local runtime + question runner + confidence/abstention gates.
3. **Logical TXT pack UI.** Whole-repo capture/groups есть, но нет завершённого Workbench с кнопками Whole / Interconnected / Tech debt / Errors / High value / Test impact / Runtime path / Delta и verified TXT/MD/JSON exports.
4. **Mission loop.** Нужна state machine, которая после ответа AI автоматически формирует evidence/next-action state, прогоняет Laya questions, выбирает зарегистрированный workflow, исполняет его и возвращает следующий evidence doc — пока оператор не остановит процесс, критерии не выполнены или не возник UNKNOWN/BLOCKED.
5. **GitHub acquire UX.** Нужна кнопка clone/fetch/open repo, structured capability and immutable clone/update receipt. Не разрешать модели выполнять произвольную shell-строку.
6. **Grok/Grok Build device qualification.** Нужно реально квалифицировать selectors/identity/readback на текущем UI и Windows устройстве.
7. **Installed product qualification.** Текущий Python/Tk app можно запускать, но polished installed workflow, shortcut/update/readback and actual target-device receipt должны быть подтверждены на Windows.
8. **Optional Grok Build headless/ACP transport.** Это более надёжный coding route, который должен использовать те же Intent/Packet/Receipt contracts, а не отдельную автономную систему.

## Итог

После реализации backlog из этого handoff пользователь сможет говорить «проанализируй этот repo, найди tech debt, спроси выбранный Grok Build tab что делать дальше, собери недостающие данные, подготовь change task» — и система будет циклически собирать факты и выполнять **только зарегистрированные** действия. Формулировка «автоматизировать что угодно» означает «любую задачу, для которой есть квалифицированная capability или которую Tool Factory безопасно создаст и квалифицирует», а не неограниченное исполнение произвольного кода/кликов.
