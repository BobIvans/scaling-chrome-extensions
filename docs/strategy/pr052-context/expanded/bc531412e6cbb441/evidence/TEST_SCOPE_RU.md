# Фактически выполненная проверка

24 теста архиватора/импортера прошли на Linux. Команда: `python -m unittest discover -s tests -v`. Лог: `TOOLKIT_TEST_LOG.txt`.

В том числе: 1 007 файлов; UTF-8 Unicode и разрез внутри multibyte; файл >8MiB; пустой файл; binary/UTF-16 raw preservation; dotfiles/неизвестные suffix; pinned Git вместо dirty bytes; links не обходятся; LFS pointer flagged; corrupted object/manifest/export обнаруживаются; context reconstruction; invalid ref/path traversal; interrupted scan; duplicate chat JSON rejected; alternate chat branches; static parser не исполняет source.

16 workflow JSON прошли только consistency/DAG validation, executed=0. Python tools синтаксически компилируются. Это не проверка внешних API и не запуск этих планов.

NOT_RUN: интерактивный Tk UI; Windows/Dell; ASR/микрофон/доступность; Laya/Jev/HF inference; ChatGPT API; CI и tests исходных пользовательских repo; bot qualification; market paper campaign; live trading.
