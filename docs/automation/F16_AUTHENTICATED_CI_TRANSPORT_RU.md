# F-16 — authenticated exact-head CI transport

## Подтверждённый gap

На head F-15 Core уже владел `occ.ci-snapshot.v1`, exact-head reconciliation и
release state. Однако snapshot создавался только внешним операторским export:
код не получал authenticated GitHub metadata и не мог fail-closed заменить
устаревший green snapshot после отзыва доступа.

## Реализация

`content-lab/github_ci_snapshot.py` — отдельный read-only transport. Он:

- принимает только зарегистрированные policy profile, repository, required
  checks и exact 40-hex head;
- читает GitHub Check Runs API через private env `OCC_*`, фиксированный
  `api.github.com`, pinned API version, TLS и запрет redirect;
- пропускает только required names с exact `check_suite.head_sha` и
  `app.slug=github-actions`;
- bounded pagination: до 10 страниц по 100 записей и до 2 MB на ответ;
- атомарно заменяет уже зарегистрированный `snapshot_file`, mode 0600 где это
  поддерживается;
- при missing/revoked credential, transport error или page overflow записывает
  BLOCKED snapshot без checks, удаляя возможность повторно принять старый green;
- никогда не сохраняет token, response body или произвольный URL.

Core остаётся единственным владельцем reconciliation. Новый origin принимается
только при совпадении repository, exact required set и `OBSERVED`; pending,
missing, wrong-SHA, foreign-app, ambiguous и BLOCKED snapshots сохраняют
`WAITING_CI`. Старый ручной origin поддержан без повышения уровня доверия.

## Границы

Transport не публикует commit, не создаёт PR и не запускает worker. Он не даёт
release authority и не подписывает результат. В этой реализации не выполняется
реальный authenticated API smoke: credential не извлекался и не создавался;
сетевой контракт проверяется deterministic injected fixtures. Provider/model API,
браузер, signer/sender и платные вызовы отсутствуют.

## Проверка

Основной Python suite покрывает exact-head/action binding, latest failure,
missing/revoked auth, stale-green clearing, pagination bound, wrong SHA/app,
policy binding и принятие snapshot существующим Core. Также выполняются полные
Native Host и extension regression suites.
