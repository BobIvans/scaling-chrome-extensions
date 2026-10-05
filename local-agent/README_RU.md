# Voice AgentOS Mini

Это локальный Windows UI, а не extension UI. Chrome extension остается невидимым transport/observer.

Главное окно — маленький always-on-top полупрозрачный блок справа снизу с тремя кнопками: Observe, Automate+, STOP.

Observe захватывает активную Chrome-вкладку через local control bridge; если direct bridge недоступен, используется существующий OCC shortcut Alt+Shift+C и verified clipboard capture. Automate+ открывает Mission editor. STOP ставит durable Core fence независимо от Laya/LLM.

GitHub merge watch: public polling не требует платной услуги. Без token GitHub дает 60 REST requests/hour; Mini не опрашивает чаще примерно 65 секунд. С token доступно 5,000/hour. Default 90 seconds.

В watch_folders можно указать папки экспортов ChatGPT/Grok/Telegram, Downloads, локальные R&D/output папки и локально синхронизированную или экспортированную Google Drive папку. Cloud-only .gdoc pointer не считается содержимым: для него нужен Drive export/API/OAuth.

Laya: Mini поддерживает локальный HTTP endpoint /v1/systemone и typed questions из laya_questions.json. Если endpoint не настроен, Laya не подделывается.
