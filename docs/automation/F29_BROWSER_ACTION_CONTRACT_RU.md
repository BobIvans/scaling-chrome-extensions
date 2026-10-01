# F-29: Browser action contract

## Подтверждённый gap

Существующие `background.js` и capture handlers уже ограничивают отдельные
операции активной вкладкой, document ID и пользовательским жестом. Однако единого
одноразового контракта, который до browser transport связывает зарегистрированное
действие с точными tab/document/origin и терминальной отменой, не было.

F-29 добавляет этот контракт без Chrome dispatch. F-30 остаётся отдельной
квалификацией установленного Chrome transport, handshake/reconnect/revoke и
точного package hash.

## Контракт

`one-click-context/library/browser-action-contract.mjs` принимает grant только
из настоящего события с `isTrusted=true`. Grant:

- живёт от 1 до 30 секунд и хранится только в памяти;
- связывает один `action_id` с точными `tab_id`, `document_id` и каноническим
  HTTP(S) origin;
- разрешает только пять существующих capture-действий: loaded, chat, document,
  chat+document и visible screenshot;
- использует фиксированные code-owned handler/options, а не текст страницы;
- возвращает `transport_qualified=false` и `dispatch_allowed=false`.

Plan принимает только `grant_id` и `request_id`. Повтор того же request
идемпотентен, другой request для grant отклоняется. Action, target, handler,
options, selector, URL, script, argv и page instruction не принимаются. Текст
страницы имеет authority `DATA_ONLY` и не может зарегистрировать команду.

Cancel требует настоящего UI/keyboard gesture, создаёт терминальный receipt и
блокирует последующий plan. Receipt явно подтверждает
`action_dispatched=false` и `transport_invoked=false`. Перезапуск теряет
ephemeral grants и поэтому закрывается безопасно.

## Основание и границы

Контракт следует официальной модели Chrome Extensions:

- `activeTab` даёт временный доступ к текущей вкладке после явного жеста
  пользователя и отзывается при уходе на другой origin;
- `runtime.MessageSender` предоставляет `tab`, `documentId` и `origin` для
  проверки источника сообщения;
- `scripting` требует tab ID и `activeTab` либо host permission;
- сообщения от content scripts следует считать недоверенными и валидировать.

Источники:
[activeTab](https://developer.chrome.com/docs/extensions/develop/concepts/activeTab),
[MessageSender](https://developer.chrome.com/docs/extensions/reference/api/runtime#type-MessageSender),
[scripting](https://developer.chrome.com/docs/extensions/reference/api/scripting),
[security](https://developer.chrome.com/docs/extensions/develop/security-privacy/stay-secure).

Модуль не вызывает `chrome.*`, сеть, Native Host, shell, dynamic code или
провайдерский API; он не создаёт host permissions и не нажимает произвольные
элементы страницы. Реальный Chrome не запускался, установленный пакет не
квалифицировался, а точный package hash ещё не проверен. Существующие
SQLite/library/job queue, voice/Laya, Web3 sender/signer и provider-budget owners
не изменены.
