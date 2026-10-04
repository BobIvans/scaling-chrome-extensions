# Первичные технические источники

Проверены 2026-10-04; документация служит основанием предложенного контракта,
не доказательством установленной реализации.

- Git LFS specification: https://github.com/git-lfs/git-lfs/blob/main/docs/spec.md
  Pointer содержит descriptor внешнего content, а не этот content. Предлагаемый
  MVP распознаёт canonical v1; другие recognized forms остаются явными gaps.
- Git ls-tree: https://git-scm.com/docs/git-ls-tree
  Mode/kind/OID и -z paths используются как metadata pinned tree.
- Git cat-file: https://git-scm.com/docs/git-cat-file
  Blob read должен оставаться raw object read, без filters/textconv.

Все остальные code claims основаны на сохранённых source excerpts и их hashes,
а статус параллельных чатов — на переданном пользователем тексте.
