# RND-50 — Foreground-preserving parallel workspace
**Статус:** refinement; proposed R&D, не установленная интеграция.

## Зачем
Пользователь продолжает печатать, пока агенты читают и готовят код.

## Устройство
Фоновые API/FS workers не трогают focus; UI input lease выдаётся одной активной цепочке и отзывается при ручном вводе.

## Эксперимент
Во время ASR/retrieval/edit worktree пользователь работает в Chrome.

## Acceptance
Ни stolen focus, ни набора текста в чужом окне; independent tasks продолжаются.

## Функции
- `detect_foreground_user_activity()`
- `lease_desktop_input_channel()`
- `suspend_conflicting_gui_path()`
- `continue_noninterfering_background_tasks()`

Requirements: REQ-034 REQ-020. Sources: S03 S25.
