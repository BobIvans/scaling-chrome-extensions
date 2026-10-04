# Примеры, не автоматически запущенные команды

`qualification-request.example.json` и `qualification-profile.example.json` соответствуют полям прочитанного bot bridge [G08,G09]. Пути примерные; до исполнения нужны reviewed checkout/установка/профиль. Пример НЕ добавляет signer/live права. Пустой source_refs означает, что в эту демонстрационную форму не выдуманы отсутствующие hashes истории.

`laya-prediction-request.example.json` — state/questions, то есть запрос классификации. Он НЕ workflow и не запускает квалификацию. Конкретный SDK/runtime/model revision, token accounting и server binding ещё надо проверить. Не отправлять туда JSON из `workflows` как будто это та же schema.

`schemas/openai_tools.responses.json` — декларации tools для будущего API adapter; они не подключены к какому-либо аккаунту и сами ничего не выполняют.
