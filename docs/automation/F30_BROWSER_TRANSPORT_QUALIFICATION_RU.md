# F-30: квалификация установленного Browser transport

## Подтверждённый gap

F-14/F-29 имели NativeClient, hello и fail-closed browser action plan, а
packager печатал SHA-256 ZIP. Но не было одного qualification owner, который на
установленном расширении проверяет exact package bytes, два независимых native
handshake, fresh reconnect и последующий revoke optional permission.

F-30 добавляет воспроизводимый harness. В текущей среде нет установленного
Windows Chrome/native host, поэтому фактический device verdict остаётся
`BLOCKED_INPUTS`, а не PASS.

## Package identity

`package_chrome_ready.py` теперь создаёт `PACKAGE_IDENTITY.json`. Он содержит
version, отсортированный список путей, byte counts и SHA-256 каждого исходного
файла. `TREE_SHA256` вычисляется length-prefixed по пути и точным bytes; identity
не включён в собственный digest. Отдельный `ZIP_SHA256` идентифицирует архив.

Installed verifier читает каждый перечисленный `chrome-extension://` файл и
пересчитывает tree digest. Изменённый/пропавший файл, path traversal, duplicate,
order drift, неизвестное поле или другой expected hash дают BLOCKED.

## Native handshake, reconnect и revoke

`browser-transport-qualification.mjs` допускает qualification только при уже
выданном `nativeMessaging`. Для каждого из двух подключений он отправляет fresh
nonce/request ID и требует binding exact:

- extension ID и manifest version;
- package-tree SHA-256;
- host name `com.one_click_context.codex`;
- echo nonce и новый UUID host session;
- `action_dispatch_allowed=false`.

Первый disconnect обязан наблюдаться до второго connection. Одинаковый session
ID означает отсутствие fresh reconnect. После второго disconnect verifier
удаляет optional `nativeMessaging` и проверяет, что permission действительно
отозвано. PASS receipt не разрешает ни одно browser action.

`Install.ps1` требует exact extension ID, version и TREE_SHA256 и сохраняет их в
host config. Host отклоняет schema drift и любое несовпадение binding.

## Основание и границы

Официальная модель Chrome подтверждает, что `connectNative()` требует permission,
создаёт Port к зарегистрированному host, передаёт host origin вызывающего
extension, а `onDisconnect` фиксирует закрытие. Для MV3 Chrome отдельно советует
учитывать crash/disconnect native host и выполнять reconnect осознанно.

Источники:
[Native messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging),
[runtime.connectNative](https://developer.chrome.com/docs/extensions/reference/api/runtime/#method-connectNative),
[service-worker lifecycle](https://developer.chrome.com/docs/extensions/develop/concepts/service-workers/lifecycle).

В репозитории проверены package generation, byte tamper detection, exact binding,
fresh reconnect, disconnect observation и revoke failures на deterministic
fixtures. Они не являются installed-device evidence. Реальный PASS требует:

1. собрать и сохранить TREE_SHA256/ZIP_SHA256;
2. распаковать exact ZIP и загрузить его в Windows Chrome;
3. зарегистрировать host для exact ID/version/TREE_SHA256;
4. открыть `qualification.html`, нажать trusted button и сохранить PASS receipt.

Chrome/registry/device не изменялись в этой автоматизации. Provider/model API,
browser action, job, merge, deploy, signup, purchase, Web3 signing/send и market
campaign не выполнялись. SQLite/library/job queue owners не изменены.
