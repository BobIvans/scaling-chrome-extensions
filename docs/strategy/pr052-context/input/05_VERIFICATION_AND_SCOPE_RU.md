# Проверки, evidence и boundaries

Не выполнять повторно полный suite без изменения source/обнаруженного failure:
его current-main результат уже включён. После code changes — актуальные gates
`.github/workflows/deterministic-core.yml` и strategy integrity workflows.

Основные команды из текущего repo:

```bash
python docs/strategy/voice-agentos/verify_integrity.py
python docs/strategies/pr016-017/verify_context.py
python -m unittest discover -s content-lab -p 'test_*.py' -v
python -m unittest discover -s desktop/tests -p 'test_*.py' -v
python -I -X utf8 desktop/package.py verify --shell desktop
node --test agent-bridge/*.test.mjs
python -m unittest discover -s agent-bridge -p 'test_qualification_adapter.py' -v
node --test one-click-context/tests/*.test.*
```

Для UI Linux CI применяет Xvfb; unavailable display остаётся skip и не becomes PASS.
`tools/verify_bundle.py` проверяет SHA/size каждого файла этого ZIP и 21 status row.
`tools/refresh_github.py --output <new-audit-dir>` читает текущие GitHub states;
снимок 04.10.2026 может устареть. Оба tools — stdlib, не требуют AI tokens.

Новые shared-source tests должны использовать независимо созданные raw bytes и
известные ranges, а не encode/decode того же implementation как единственный oracle.
Перекрывающиеся ledgers объединяются по IDs+scope+binding; full-family criterion
не закрывается одним component test, hash или AI claim.

Корпус растёт без fixed total-file/doc/part ceiling. Working memory/page/provider
frames остаются explicit и дают continuation/backpressure. Scale pass требует
проверки EOF, hashes, всех origins/revisions и measured RAM/latency на реальном профиле.
Live trading, реальные paid API действия и production activation не выполнялись
в этом аудите. Стратегия сохраняет их future scopes; нулевой бюджет offline replay
не является удалением возможностей продукта.
