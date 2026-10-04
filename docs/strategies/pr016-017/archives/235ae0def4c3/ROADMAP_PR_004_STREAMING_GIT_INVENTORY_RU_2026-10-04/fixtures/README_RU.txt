stream_golden: 55 synthetic ls-tree metadata records. Последняя record должна
сохраниться после 20/39. raw output — NUL binary; expected rows имеют path_b64.
Expected rows — независимые fixture expectations; oracle не выполняет Git,
source repo, SQLite stage или приложение. Все application cases NOT_RUN.

tools/make_large_git_fixture.py --output /absolute/path/empty-new-synthetic-directory
создаёт обычный Git repo без checkout, ~160k long-path entries и один blob.
Скрипт отказывается от existing output. Требуется installed Git; writes только
новый fixture directory, не user repo. Expected stdout bytes >32 MiB.
Generation/stream verification измеряется отдельно от будущего CLI qualification.
Этот ZIP не включает huge generated tree; recipe portable и воспроизводим.
