"""Diagnose the configured runtime and existing store without creating a corpus."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import sys

# Direct isolated launch imports only the installed shell package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from desktop import SHELL_VERSION
from desktop.client import Connection, DesktopClient, DesktopError, require, sha_file, strict_json

RUNTIME_PROBE = ('import json,sys,tkinter; '
                 'print(json.dumps({"python":sys.version.split()[0],'
                 '"compatible":sys.version_info >= (3,11),"tk":str(tkinter.TkVersion)}))')


def check(connection):
    connection.verify()
    client = DesktopClient(connection)
    try:
        # Reuse bounded dual-pipe transport even for the fixed runtime probe.
        class Probe:
            adapter_path = connection.adapter_path

            def argv(self):
                return [connection.python_path, '-I', '-X', 'utf8', '-c', RUNTIME_PROBE]

        probe = DesktopClient(Probe())
        import threading
        try:
            runtime = strict_json(probe._exchange(b'', threading.Event(), 4096, 5000))
        except DesktopError:
            raise DesktopError('DESKTOP_RUNTIME_TK_REQUIRED') from None
        require(runtime.get('compatible') is True, 'DESKTOP_RUNTIME_TK_REQUIRED')
        hello = client.handshake()
        return {'schema': 'occ.desktop-preflight.v1', 'shell_version': SHELL_VERSION,
                'shell_files': {p.name: sha_file(p) for p in Path(__file__).parent.glob('*.py')},
                'runtime': runtime, 'os': platform.platform(),
                'adapter_context': hello['adapter_context'], 'info': hello['result']['info'],
                'transport': client.last_stats, 'windows_installed': 'NOT_RUN'}
    finally:
        client.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = check(Connection.load(args.config))
        print(json.dumps({'ok': True, 'result': result}, ensure_ascii=False, allow_nan=False))
        return 0
    except (DesktopError, OSError, ValueError):
        code = sys.exc_info()[1]
        print(json.dumps({'ok': False, 'error': code.code if isinstance(code, DesktopError) else 'DESKTOP_SETUP_REQUIRED'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
