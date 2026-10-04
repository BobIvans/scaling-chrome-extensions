#!/usr/bin/env python3
"""Verify delivery files against PACKAGE_MANIFEST.json; no downloads/execution."""
import hashlib
import json
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[1]
manifest = json.loads((root/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
errors=[]
for row in manifest['files']:
    p=root/row['path']
    if p.is_symlink() or not p.resolve().is_relative_to(root) or not p.is_file():
        errors.append(row['path']+': missing or unsafe'); continue
    h=hashlib.sha256()
    with p.open('rb') as f:
        for raw in iter(lambda:f.read(1024*1024),b''): h.update(raw)
    if h.hexdigest()!=row['sha256'] or p.stat().st_size!=row['bytes']:
        errors.append(row['path']+': mismatch')
print(json.dumps({'state':'VERIFIED' if not errors else 'FAILED','files_checked':len(manifest['files']),'errors':errors},indent=2))
sys.exit(bool(errors))
