# Семантика поверх JSON Schema

Schemas проверяют форму. Application validator дополнительно проверяет:

- RAW_BYTES: 0≤start≤end≤raw_size; range hash соответствует measured original.
- JSON_POINTER: locator обязателен, raw byte coordinates не выдумываются.
- DERIVED_UTF8_BYTES: extraction revision обязательна; raw reverse map может UNKNOWN.
- LINE_ONLY: anchor quality LINE_ONLY; точные spans не выводятся из line number.
- UNKNOWN/MULTI_RANGE имеют typed result с gaps/segments, а не fake exact span.
- Scoped refs должны принадлежать authorized namespace/profile/projects ДО read.
- RESOLVED_LOCAL требует target в frozen snapshot, unambiguous qualified rule.
- EXTERNAL/DYNAMIC/AMBIGUOUS/MISSING требуют reason; DYNAMIC не получает exact target.
- OBSERVED_COVERAGE требует registered build/scope receipt; имя test файла недостаточно.
- Runtime PASS нельзя записать по PACKAGE example или по copied source statement.
- Group complete относится к membership; raw/parsed/graph/selected/exported независимы.
- Checkpoint не принимается при request/config/source/version mismatch.
- Schema proposal адаптируется к canonical owner; existing public fields не переименовываются молча.
