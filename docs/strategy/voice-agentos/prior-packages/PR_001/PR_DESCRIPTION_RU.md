# Предлагаемый title

feat(context): add resumable whole-repo scan controls

# Body template — уточнить по фактическому diff

Сейчас Repo Review обрабатывает одну scan page на ручной клик. Изменение
добавляет один запуск до конца pinned snapshot с progress, Pause/Continue/Stop
и сохранённым control state в existing Content Lab SQLite. Cursor и raw chunks
остаются у существующего repo_context owner; cancelled intent не возобновляется
после restart, а lost page reply разрешается по stored cursor.

Проверено: [actual focused/native/UI/compatibility tests и результат].
Base/head: [actual SHA]. Windows device: [actual receipt либо NOT_RUN].
Remaining M5-02 scope: full portable manifest/ZIP, streaming Git inventory,
expanded format policy и related code/test groups.

Это шаблон описания будущего PR. Не отправлять его с незаполненными evidence
полями и не использовать как утверждение, что implementation уже завершена.
