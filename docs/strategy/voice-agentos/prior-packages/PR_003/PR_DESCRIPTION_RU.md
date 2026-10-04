Verified manifest сейчас связывает sources с chunks, но не выдаёт полный
переносимый payload archive и возобновление после прерывания. PR добавляет
foreground export всех captured INDEXED chunks с atomic stage, hash-checked
resume, static offline source↔part navigation и проверяемым ZIP/receipt.

Оставляет existing snapshot/batch IDs и source store владельцами данных.
Gaps видимы; corrupted/disk-full output не становится ready. ZIP assembly
после прерывания пересобирается из уже сохранённых parts.

Validation: заполнить actual commands/results и fault case evidence из
implementation receipt. Этот файл — шаблон будущего PR description;
подготовка ZIP/fixture не является actual application test/merge/Windows result.
