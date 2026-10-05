# Scenario: скачать GitHub repo → открыть local UI → whole scan → focused work

## User journey

1. Launch the installed Context Library / Voice AgentOS app.
2. Open **Repository Workbench**.
3. Press **Скачать / клонировать GitHub repo**.
4. Paste repository URL or select a previously registered repository.
5. Choose destination workspace and ref/branch/commit. Authentication is referenced from operator configuration; secret/token values are never written into mission/context artifacts.
6. The registered `repo_acquire_github` capability performs clone/fetch/checkout through a fixed Git adapter, not a model-generated shell line.
7. Persist receipt: remote URL identity, local root identity, commit SHA, tree SHA, operation, timestamp and adapter version.
8. Register repo alias in the existing repo profile/store.
9. UI automatically opens the repository dashboard.
10. Run **Первичное полное сканирование**. Resume after restart using the same durable run.
11. When capture is complete, build `WHOLE_REPO_INDEXED`: complete accounting + logical groups + full overview.
12. Optionally run focused modes: interconnected / tech debt / errors / high value / tests / runtime / delta.
13. Select a Grok/Grok Build tab in **AI Targets**, bind and observe it.
14. Speak/type the mission, for example: «Найди критический tech debt, собери связанные файлы и спроси выбранный Grok Build что чинить первым».
15. Mission Loop builds a focused pack, Laya routes the step, the registered AI transport sends it, reads the result, imports it as a claim and builds a feedback/evidence document.
16. If the AI proposes code work, create a pinned coding task/worktree. Run tests/verifiers. Feed results back.
17. Finish only when acceptance criteria are verified; otherwise continue with more context, another qualified capability or BLOCKED/UNKNOWN.

## Revision rules

A mission is pinned to a repo snapshot/commit. A fetch/checkout to a new HEAD invalidates packets derived from the old revision. The UI must show STALE and require a delta/rebuild before sending stale context as current truth.

## Installed-app definition of done

On a target Windows machine:
- installer creates versioned app/backend and Start Menu shortcut;
- app launches without source checkout;
- Repository Workbench opens;
- clone/open local repo works;
- whole scan survives restart;
- logical packs export and reopen;
- AI tab picker/binding works;
- voice/text mission preview works;
- STOP works independently;
- data/store stay outside version directory;
- update/rollback read back installed version;
- device receipt records actual environment and results.
