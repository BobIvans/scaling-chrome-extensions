"""Verify preserved strategy bytes and unchanged original criterion wording."""
import hashlib
import json
from pathlib import Path
import zipfile


def main():
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / 'PRESERVATION_MANIFEST.json').read_text(encoding='utf-8'))
    for row in manifest['files']:
        path = root / row['path']
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing or linked preserved file: ' + row['path'])
        content = path.read_bytes()
        if len(content) != row['size_bytes'] or hashlib.sha256(content).hexdigest() != row['sha256']:
            raise ValueError('Preserved file changed: ' + row['path'])
    with zipfile.ZipFile(root / 'original-strategy.zip') as source:
        for entry in source.infolist():
            if not entry.is_dir():
                relative = Path(*Path(entry.filename).parts[1:])
                if source.read(entry) != (root / 'source' / relative).read_bytes():
                    raise ValueError('Original member differs: ' + entry.filename)
    for row in json.loads((root / 'ARCHIVE_INDEX.json').read_text(encoding='utf-8')):
        with zipfile.ZipFile(root / row['archive']) as archive:
            for entry in archive.infolist():
                if not entry.is_dir() and archive.read(entry) != (
                        root / row['extracted_tree'] / entry.filename).read_bytes():
                    raise ValueError('Nested member differs: ' + entry.filename)
    original = json.loads((root / 'source/acceptance/CRITERION_COVERAGE.json').read_text(encoding='utf-8'))
    current = json.loads((root.parents[2] / 'docs/automation/pr016-017/CRITERION_COVERAGE.json').read_text(encoding='utf-8'))
    wording = lambda rows: {row['criterion_id']: row['criterion_exact'] for row in rows}
    if len(original) != 220 or wording(original) != wording(current):
        raise ValueError('Criterion IDs or exact wording differ')
    print(json.dumps({'status': 'PASS', 'preserved_files': len(manifest['files']),
                      'source_members': manifest['source_member_count'],
                      'unique_nested_archives': manifest['unique_nested_archives'],
                      'original_criteria_preserved': len(original),
                      'runtime_or_device_qualification': 'NOT_CLAIMED'}))


if __name__ == '__main__':
    main()
