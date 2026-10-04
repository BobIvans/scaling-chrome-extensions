# Exact input adapter к полученному №5

Получен PR005 input. Его storage key: repo_entries.analysis.format_eligibility.
Wire schema: occ.format-eligibility.v1; classifier_version=utf8-controls-strict-lfs3.v1.
Оригинальные contract/schema сохранены byte-for-byte в previous/PR_005_*.
Это подтверждает design input, не наличие фактов или implementation в actual DB.

Default parser preflight требует schema-valid facts, bound snapshot_id,
canonical decimal-string ordinal/git_size, exact path/mode/kind/git_oid,
disposition и file_sha256. Classifier/schema version и hashes входят в
interpretation digest. Нельзя converting decimal ordinal через JavaScript Number.
Текст допускается только при INDEXED + blob/nonlink + raw_capture=RECORDED +
text_eligibility=ELIGIBLE + UTF8_TEXT_CANDIDATE/EMPTY и matching source hash.

raw_integrity=NOT_RUN не является byte proof. №7 независимо reconstructs captured
chunks/ranges/revisions/hashes перед parser. FAIL/CORRUPT блокирует. Missing facts
-> ELIGIBILITY_FACTS_UNAVAILABLE, unknown -> explicit gap; не fallback by chunk UTF8.
Только отдельный opt-in legacy guard допускается до implementation №5 и маркируется
LEGACY_CAPTURE_GUARD_UNVERIFIED_PR005. Default не обходит known eligibility policy.
LFS pointers, links, binary/protected/missing остаются metadata/gaps по №5;
classifier не дублируется. Derived JS analysis never changes raw capture.
