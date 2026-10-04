# Минимальное окно и состояния

1. Открыть desktop launcher. При готовом connection profile повторный запуск
   подключается к тому же namespace. First-run позволяет выбрать установленный
   runtime/backend profile и показывает текущий путь данных/версию.
2. Подключиться. Статус: Подключено / Требуется настройка / Несовместимая версия /
   Ошибка подключения. Диагностика по кнопке, без raw corpus/profile/log dump.
3. Выбрать namespace, ввести поиск. Результаты подписаны «Лучшие совпадения»;
   selection/count относятся к отображённому bounded result.
4. Выбрать items, прочитать контекст. Source title/path отображается как data.
5. Задать цель, область, критерии; «Сохранить документ» создаёт локальный draft.
   UI показывает выбранные источники, размер и статус сохранения.

Минимальные controls: connection status, namespace list, search input/results,
selected-source preview, goal/scope/acceptance fields, save, cancel, diagnostics.
Keyboard Tab/Enter/Escape работают; IPC никогда не блокирует Tk event loop.
No implementation details in the ordinary flow; versions/data path help choose
правильную установленную библиотеку. Technical DTO/digest details only diagnostic.

State table:

| State | Доступно | Следующее событие |
| --- | --- | --- |
| DISCONNECTED/SETUP_REQUIRED | Configure/reconnect/offline index | Valid handshake |
| CONNECTING | Cancel/settings | READY or typed error |
| READY | Namespace/search | Read request → BUSY_READ |
| BUSY_READ | Cancel/close, editing invalidates old reply | Current reply → READY; old reply discarded |
| CONTEXT_READY | Goal/edit/save | Atomic draft publication |
| CLOSING | Child cleanup only | Closed; no queued widget mutation |

Current packet has SELECTED_ITEMS scope. Binary/raw/LFS eligibility belongs to
the backend, and full-repo ZIP belongs to exporter. Successful local save never
sets canonical task created/provider sent/read/merge/update statuses.
