python verification/validate_package.py
Требуется только Python 3 standard library, без pip/network.
Validator проверяет hashes/полноту критериев/ссылки/examples/golden data/DAG.
Schema checker реализует ровно использованный subset (types/anyOf/required/
const/enum/pattern/bounds/additionalProperties), не общий Draft2020-12 engine.
Не запускает importer/parser/UI/service приложения, не квалифицирует Windows.
Runtime tests, holdout и device checks NOT_RUN.
