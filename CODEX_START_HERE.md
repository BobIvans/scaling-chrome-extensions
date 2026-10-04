# Codex: начать здесь

Целевой repo: `BobIvans/scaling-chrome-extensions`.
Цель и authoritative sources: [MASTER_CONTEXT.md](MASTER_CONTEXT.md).

## Перед кодом

1. Прочитай применимые `AGENTS.md`; зафиксируй `git status`, branch, HEAD, main и
   PR #49. Не перезаписывай чужие изменения. Обнови remote refs и повторно проверь
   статусы prerequisites #50/#51, поскольку параллельные чаты меняют main.
2. Прочитай `MASTER_CONTEXT.md`, затем
   `docs/strategies/pr016-017/EXECUTION_AUDIT.md` и `NEXT_IMPLEMENTATION.md`.
3. Прочитай исходные `source/01_PR_DESCRIPTION_RU.md`, `02_IMPLEMENTATION_RU.md`,
   `03_FUNCTIONS_RU.md`, `contracts/`, `schemas/`, `plan/DEPENDENCIES.json` и
   `acceptance/`. Префикс всех этих путей: `docs/strategies/pr016-017/`.
4. Сверь `FUNCTION_AUDIT.json` с actual symbols и runtime tests. Прочитай
   `docs/automation/pr016-017/README_RU.md`, `QUALIFICATION_RU.md`,
   `FUNCTIONS_IMPLEMENTATION.json`, `CRITERION_COVERAGE.json`.
5. Проверь сохранённые bytes:
   `python docs/strategies/pr016-017/verify_context.py`.

## Реализация

Выполни следующий scoped этап из `NEXT_IMPLEMENTATION.md`, сохраняя полный
исходный roadmap. Переиспользуй canonical SQLite/Core/jobs/grants/STOP и реальные
packet owners. Scope нельзя автоматически закрывать по fixture или тексту AI.
При отсутствии зависимостей сохрани точный blocker/owner/next evidence и продолжай
независимые части. Не заменяй реальные UI/device receipts выдуманными PASS.
Разрешённые read-only/reversible подготовительные работы выполняй автономно.
Для effects используй актуальный пользовательский scope и configured grants.

## Проверки и передача

Запусти targeted independent tests, затем применимую регрессию:

```sh
python -m unittest discover -s content-lab -p 'test_*.py' -q
python -m unittest discover -s desktop/tests -p 'test_*.py' -q
python -I -X utf8 desktop/package.py verify --shell desktop
node --test agent-bridge/*.test.mjs
python -m unittest discover -s agent-bridge -p test_qualification_adapter.py -q
node --test one-click-context/tests/*.test.*
git diff --check
```

Tk display tests требуют Xvfb на Linux; deterministic-core CI использует Xvfb и
Windows. При изменении owned shell files пересоздай desktop manifest после edits.
Перед merge нужен actual tested head и свежий exact-head CI, без bypass checks.
Если main изменился, сверить diff/конфликты и повторить затронутые проверки.

Обновляй `EXECUTION_AUDIT.md`, `VALIDATION.json`, function/criterion evidence и
следующий этап; source сохраняй без изменения bytes. В отчёте укажи actual code
changes, commands/results, PR/head/merge, все remaining gates и одну следующую
команду. Не объявляй весь Voice AgentOS готовым по завершению одного baseline PR.
