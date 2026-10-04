
## Корневые документы при интеграции main

После docs-передачи к девяти app conflicts добавляются add/add conflicts в root
MASTER_CONTEXT.md и CODEX_START_HERE.md: main имеет общий handoff #51/#49/#53,
а ветка #52 — scoped handoff этой передачи. Сохранить оба полноценных контекста.
Оставить current PR52 navigation явной, а общий main handoff сохранить/связать
через docs/strategy/voice-agentos и docs/strategy/pr012-013. Его exact root copies
уже сохранены в input/evidence/main/. Оригинальные source plans не переписывать.
.gitattributes этой передачи включает текущие main rules плюс immutable source rules;
при новом drift объединять обе группы правил. Проверять actual conflict set заново.
