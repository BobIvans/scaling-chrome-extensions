# F-28: статически проверяемый OpenShell profile

## Подтверждённый gap

После F-26/F-27 backend adapters имели закреплённые provider endpoints, но не
было review owner для OpenShell profile, который связывает native endpoint с
конкретным binary и явно фиксирует статус Windows WSL2. F-28 добавляет этот
owner без установки OpenShell, provider credentials или запуска sandbox.

## Контракт

`content-lab/openshell-openai-profile.example.json` — узкий provider profile для
F-26 Responses adapter. Он объявляет `OPENAI_API_KEY`, разрешает только
`api.openai.com:443`, `POST /v1/responses`, `protocol=rest`,
`enforcement=enforce`, запрещает uninspected credentials и называет один binary
`/opt/occ/bin/python3`. Значение ключа в файле отсутствует.

`content-lab/openshell-review.example.json` независимо закрепляет profile ID,
provider instance name, native base/request URL, endpoint, binary, обязательный
provider attachment, нулевой provider budget и статус
`windows-wsl2-docker-desktop-x86_64 = EXPERIMENTAL_NOT_RUNTIME_QUALIFIED`.

`content-lab/openshell_profile.py` принимает только эти exact bindings. Другой
host/port/path/protocol, wildcard или другой binary, audit вместо enforce,
расширенный REST path/method, uninspected credentials, отсутствующий attachment,
заявленный runtime smoke либо изменённый WSL2 status завершаются стабильным
BLOCKED code. Результат содержит только digest и публичные bindings, без secret.

```sh
python content-lab/openshell_profile.py \
  --profile content-lab/openshell-openai-profile.example.json \
  --review content-lab/openshell-review.example.json
```

Успешный статический результат имеет `runnable=false` и
`STATICALLY_REVIEWED_RUNTIME_UNQUALIFIED`. Он не равен `openshell profile lint`,
import, provider create/attach или runtime smoke и не разрешает эти эффекты.

## Основание и границы

Сверка сделана с официальными OpenShell 0.1.2 docs от 2026-10-01:

- provider profile владеет endpoints/binaries, а sandbox provider attachment —
  тем, какой workload получает доступ;
- native inference path требует profile endpoint binding, attachment и вызов
  реального provider endpoint;
- credential подставляется только после network policy и endpoint binding;
- Windows x86_64 через WSL 2 + Docker Desktop имеет статус Experimental;
- broad binary globs и audit/uninspected grants не используются.

Источники:
[Inference](https://docs.nvidia.com/openshell/latest/how-it-works/inference),
[Profiles](https://docs.nvidia.com/openshell/latest/how-it-works/providers/profiles),
[Policy schema](https://docs.nvidia.com/openshell/latest/how-it-works/policies/schema),
[Support matrix](https://docs.nvidia.com/openshell/latest/about/support-matrix).

OpenShell/WSL2/Docker не устанавливались и не запускались; `profile lint`, import,
provider create/attach, sandbox runtime и реальный API вызов не выполнялись.
Binary path обязан соответствовать будущему проверенному image layout; до этого
runtime qualification остаётся BLOCKED. Существующие SQLite/library/job queue,
browser/voice/Laya, signer/sender и Web3 owners не изменены.
