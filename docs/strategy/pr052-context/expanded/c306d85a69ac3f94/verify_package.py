"""Verify the original package byte inventory using only Python's standard library.
This checks accidental modification, not publisher authenticity or code safety.
Run from any directory: python -B /path/to/verify_package.py
New demo outputs in other directories do not alter listed files.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys


def main() -> int:
    root = Path(__file__).resolve().parent
    errors: list[str] = []
    try:
        inventory = json.loads((root / 'inventory.json').read_text(encoding='utf-8'))
        expected_inventory = None
        for line in (root / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
            checksum, name = line.split('  ', 1)
            if name == 'inventory.json':
                expected_inventory = checksum
        actual_inventory = hashlib.sha256((root / 'inventory.json').read_bytes()).hexdigest()
        if expected_inventory != actual_inventory:
            errors.append('inventory.json does not match SHA256SUMS.txt')
        seen: set[str] = set()
        for item in inventory['files']:
            name = item['path']
            rel = PurePosixPath(name)
            if rel.is_absolute() or '..' in rel.parts or '\\' in name or name in seen:
                errors.append(f'invalid or duplicate path: {name}')
                continue
            seen.add(name)
            path = root.joinpath(*rel.parts)
            if not path.resolve().is_relative_to(root):
                errors.append(f'path escapes package: {name}')
                continue
            if not path.is_file():
                errors.append(f'missing: {name}')
                continue
            data = path.read_bytes()
            if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
                errors.append(f'changed: {name}')
        print(json.dumps({'verified_files': len(seen), 'errors': errors,
                          'status': 'PASS' if not errors else 'FAIL',
                          'scope': 'byte integrity only; not authenticity or integration testing'},
                         ensure_ascii=False, indent=2))
        return 1 if errors else 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'Cannot verify package: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
