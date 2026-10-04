# Реальная qualification Windows 11 и измерение масштаба

Device target: Dell Latitude 5400, i7-8650U, 16GB RAM, Windows 11 — из контекста
пользователя; actual OS/build/free disk фиксируются при прогоне, здесь неизвестны.
Не проверялось этим чатом. В receipt device поля остаются null, outcome NOT_RUN.

## Inputs и baseline

Freeze checkout/build/parser/helper hashes, current migration/DB version, scope,
resource policy и verifier versions. Сначала copy старой DB fixture, безопасный
rehearsal и current baseline. После этого реальная canonical owner integration.
Каждый started attempt (completed/failed/unknown/cancelled/blocked) остаётся в
таблице; human-assisted и unattended не смешивать. Секретные bytes не логировать.

## Scale profiles

| Profile | Data | Проверка |
| --- | --- | --- |
| Smoke | 41 files/hits, 41 cycle nodes | >20 tail, paths/Unicode/restart |
| Integration | 1001 files, 1001 cycle nodes, 3MiB source | Full ledger, SCC parts, tail import |
| Capacity | 100000 entries; size policy set before run | Accounted count, RSS/disk/checkpoint, resource stop |
| Archive | 100 members × 1MiB, configured expansion budget 10MiB | Original retained, blocked tail explicit |
| Search scope | 1001 A + 1001 B private hits | No B snippets/count/rank leakage |

Generate each in empty directory with fixtures/generate_scale.py. Corpus size не
является runtime guarantee; при capacity stop уменьшить рабочую порцию/выбрать
qualified alternative и продолжить из checkpoint. Не выдавать truncated prefix
за весь input и не жёстко cap весь repo по количеству файлов/docs.

## Fault points и наблюдения

Kill worker: capture before finalize, after object finalize, before/after DB commit,
before receipt. Disconnect Core, sleep/resume, cancel, disk-full sandbox volume,
two writers/manual overlay conflict, source revision change, parser unavailable,
query/graph generation change, login/layout/target drift. Реальные user originals
не использовать как destructive fault target: все fault cases на frozen fixtures.

Для каждого case сохранить ledger до/после, operation/checkpoint versions, exact
byte reconstruction proof, FTS generation, graph digest, all member/part counts,
RSS peak, CPU, disk/temp amplification, p50/p95 latency, time-to-first-source и
time-to-resume. Порог performance freeze после измеренного baseline, до пилота;
не обещать universal latency на произвольном repo.

Device PASS — exact build и scoped cases. Installer/installed capability usability
не следуют из локального service pass; их downstream owners PR015/021. Смена
parser/build/profile/config делает зависимые результаты STALE. Restore rehearsal
должен открыть старые source addresses и сохранить manual/goal revisions.
