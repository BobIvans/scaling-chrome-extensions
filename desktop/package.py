"""Verify/remove only the versioned shell; retain backend, profile and corpus."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from desktop import SHELL_VERSION
from desktop.client import (Connection, DesktopError, exact, hash_value, is_link,
                            require, sha_file, strict_json)
from desktop.draft import publication, write_verified, json_bytes

FILES = ('__init__.py', 'app.py', 'client.py', 'draft.py', 'state.py', 'preflight.py',
         'package.py', 'Launch_Windows.ps1', 'connection.example.json', 'README_RU.md')


def make_manifest(shell, source_sha):
    require(isinstance(source_sha, str) and len(source_sha) == 40 and
            all(c in '0123456789abcdef' for c in source_sha))
    return {'schema': 'occ.desktop-owned-files.v1', 'shell_version': SHELL_VERSION,
            'source_sha': source_sha, 'files': {name: sha_file(shell / name) for name in FILES},
            'backend_external_reference': 'connection.json:adapter_path/profile_path',
            'data_preserve_roots': 'operator-profile:store/policy_file and all chosen output folders',
            'optional_owned_config': 'connection.json', 'windows_installed': 'NOT_RUN'}


def verify(shell):
    shell = Path(shell).absolute()
    require(not any(is_link(p) for p in (shell, *shell.parents)), 'DESKTOP_LINK_PATH')
    path = shell / 'OWNED_FILES.json'
    require(path.is_file() and not is_link(path), 'DESKTOP_PACKAGE_MANIFEST_REQUIRED')
    with path.open('rb') as stream:
        raw = stream.read(16_001)
    require(len(raw) <= 16_000)
    manifest = strict_json(raw)
    exact(manifest, {'schema', 'shell_version', 'source_sha', 'files',
                     'backend_external_reference', 'data_preserve_roots',
                     'optional_owned_config', 'windows_installed'})
    require(manifest['schema'] == 'occ.desktop-owned-files.v1' and
            manifest['shell_version'] == SHELL_VERSION and manifest['optional_owned_config'] == 'connection.json')
    source = manifest['source_sha']
    require(isinstance(source, str) and len(source) == 40 and all(c in '0123456789abcdef' for c in source))
    exact(manifest['files'], FILES)
    for name, expected in manifest['files'].items():
        hash_value(expected)
        path = shell / name
        require(not is_link(path) and path.is_file() and sha_file(path) == expected,
                'DESKTOP_PACKAGE_CHANGED')
    return manifest


def stage_shell(shell, output):
    """Copy the verified shell only, excluding test fixtures and external data."""
    shell = Path(shell).absolute()
    manifest = verify(shell)
    with publication(output) as stage:
        for name, expected in manifest['files'].items():
            shutil.copyfile(shell / name, stage / name)
            require(sha_file(stage / name) == expected, 'DESKTOP_PACKAGE_CHANGED')
        write_verified(stage / 'OWNED_FILES.json', json_bytes(manifest))
    return manifest


def uninstall(shell, config=None):
    """Prevalidate everything before deleting any owned file. No recursive root rm."""
    shell = Path(shell).absolute()
    manifest = verify(shell)
    config = Path(config).absolute() if config else shell / 'connection.json'
    require(config.is_file(), 'DESKTOP_CONNECTION_REQUIRED_FOR_UNINSTALL')
    connection = Connection.load(config)
    with Path(connection.profile_path).open('rb') as stream:
        raw = stream.read(2_200_001)
    require(len(raw) <= 2_200_000)
    profile = strict_json(raw)
    require(isinstance(profile, dict) and isinstance(profile.get('store'), str) and
            isinstance(profile.get('policy_file'), str))
    roots = [Path(connection.adapter_path).parent, Path(connection.profile_path),
             Path(profile['store']), Path(profile['policy_file'])]
    require(all(p.is_absolute() and not p.resolve().is_relative_to(shell.resolve()) and
                not shell.resolve().is_relative_to(p.resolve()) for p in roots),
            'DESKTOP_PRESERVE_ROOT_OVERLAP')
    names = set(FILES) | {'OWNED_FILES.json', 'connection.json', '__pycache__'}
    require(all(p.name in names and not is_link(p) for p in shell.iterdir()), 'DESKTOP_UNKNOWN_OWNED_PATH')
    cache = shell / '__pycache__'
    if cache.exists():
        require(cache.is_dir() and all(p.is_file() and not is_link(p) and
                p.name.endswith('.pyc') and any(p.name.startswith(Path(name).stem + '.')
                for name in FILES if name.endswith('.py')) for p in cache.iterdir()),
                'DESKTOP_UNKNOWN_OWNED_PATH')
    # Do not remove the shell root or any output directory. Unknown children cause
    # a preflight error, preserving even an accidentally colocated output sentinel.
    for name in FILES:
        (shell / name).unlink()
    if config == shell / 'connection.json':
        config.unlink()
    if cache.exists():
        for path in cache.iterdir():
            path.unlink()
        cache.rmdir()
    (shell / 'OWNED_FILES.json').unlink()
    return {'schema': 'occ.desktop-uninstall.v1', 'shell_files_removed': len(FILES),
            'external_roots_retained': all(p.exists() for p in roots),
            'backend': connection.adapter_path, 'profile': connection.profile_path,
            'store': profile['store'], 'windows_installed': 'NOT_RUN'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('manifest', 'verify', 'stage', 'uninstall'))
    parser.add_argument('--shell', type=Path, default=Path(__file__).parent)
    parser.add_argument('--source-sha')
    parser.add_argument('--config', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == 'manifest':
            value = make_manifest(args.shell, args.source_sha)
            (args.shell / 'OWNED_FILES.json').write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
        elif args.action == 'verify':
            value = verify(args.shell)
        elif args.action == 'stage':
            require(args.output is not None, 'DESKTOP_OUTPUT_PARENT_REQUIRED')
            value = stage_shell(args.shell, args.output)
        else:
            value = uninstall(args.shell, args.config)
        print(json.dumps({'ok': True, 'result': value}, ensure_ascii=False))
        return 0
    except (OSError, DesktopError, ValueError):
        exc = sys.exc_info()[1]
        print(json.dumps({'ok': False, 'error': exc.code if isinstance(exc, DesktopError) else 'DESKTOP_PACKAGE_FAILED'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
