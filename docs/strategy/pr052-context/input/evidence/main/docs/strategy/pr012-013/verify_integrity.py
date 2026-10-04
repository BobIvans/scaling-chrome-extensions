"""Verify every supplied ZIP member and the complete continuation criterion set."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


ROOT = Path(__file__).resolve().parent
ARCHIVE_SHA256 = 'bd4ff79d06bbdd581617ad12455e53ba0a2bf0c664519ebfe72082ab4f6b06a3'


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))


def main():
    manifest = load('verification/SOURCE_INTEGRITY.json')
    archive = ROOT / manifest['archive_path']
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == ARCHIVE_SHA256, 'Archive bytes changed'
    assert manifest['archive_sha256'] == ARCHIVE_SHA256
    assert archive.stat().st_size == manifest['archive_bytes']
    members = manifest['members']
    assert len(members) == 19
    assert len({m['archive_member'] for m in members}) == 19
    assert len({m['repo_path'] for m in members}) == 19
    with zipfile.ZipFile(archive) as z:
        actual = [i.filename for i in z.infolist() if not i.is_dir()]
        assert sorted(actual) == sorted(m['archive_member'] for m in members)
        for m in members:
            path = PurePosixPath(m['repo_path'])
            assert not path.is_absolute() and '..' not in path.parts
            original = z.read(m['archive_member'])
            preserved = (ROOT / m['repo_path']).read_bytes()
            assert original == preserved, m['repo_path']
            assert len(preserved) == m['size_bytes']
            assert hashlib.sha256(preserved).hexdigest() == m['sha256']
    source = ROOT / 'input'
    hashes = (source / 'MANIFEST.sha256').read_text(encoding='utf-8').splitlines()
    assert len(hashes) == 18
    for line in hashes:
        expected, name = line.split('  ', 1)
        assert hashlib.sha256((source / name).read_bytes()).hexdigest() == expected, name
    cards = load('input/sources/ORIGINAL_CARDS.json')
    counts = {'tasks': 10, 'features': 15, 'feature_audit': 15, 'goals': 6, 'decisions': 2}
    for kind, expected in counts.items():
        assert len(cards[kind]) == expected, kind
    streams = load('input/WORKSTREAMS.json')
    assert {w['id'] for w in streams} == {'WS-002', 'WS-003', 'WS-006', 'WS-009', 'WS-010', 'WS-011'}
    original = load('input/CRITERION_COVERAGE.json')
    current = load('audit/CRITERION_STATUS.json')
    assert len(original) == len(current) == 101
    assert len({r['criterion_id'] for r in current}) == 101
    keys = ('criterion_id', 'source_kind', 'source_id', 'criterion_exact', 'owner_workstream', 'downstream_gate')
    original_by_id = {r['criterion_id']: r for r in original}
    for row in current:
        expected = original_by_id[row['criterion_id']]
        assert all(row[k] == expected[k] for k in keys), row['criterion_id']
        assert row['status'] and 'runtime_receipt_ids' in row
    cases = load('input/ACCEPTANCE_CASES.json')
    assert len(cases) == len({c['id'] for c in cases}) == 15
    for name in ('MASTER_CONTEXT.md', 'CODEX_START_HERE.md', 'README.md'):
        doc = (ROOT / name).read_text(encoding='utf-8')
        assert 'PR-012' in doc and 'PR-013' in doc and '#51' in doc, name
    print(json.dumps({'ok': True, 'supplied_files_verified': 19,
                      'supplied_manifest_hashes_verified': 18, 'criterion_ids_preserved': 101,
                      'acceptance_cases_preserved': 15, 'card_counts': counts,
                      'runtime_qualification': 'NOT_INFERRED_FROM_SOURCE_INTEGRITY'}))


if __name__ == '__main__':
    main()
