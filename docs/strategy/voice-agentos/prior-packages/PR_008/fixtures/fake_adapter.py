"""Synthetic test adapter only. No corpus/Git/SQLite/jobs/provider operations.

Test harness explicitly selects scenario. Production client never accepts this
flag from UI requests. Fixtures are expected data, not a real installed backend.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario',default='hello')
    args=parser.parse_args()
    raw=sys.stdin.buffer.read(16001)
    if len(raw)>16000:
        sys.stdout.buffer.write(b'{"schema":"occ.desktop-stdio-result.v1","ok":false,"adapter_context":null,"error":"DESKTOP_INPUT_LIMIT"}')
        return 0
    # Input is consumed for framing only. Fake server never interprets actions.
    fixtures=Path(__file__).resolve().parent/'replies'
    files={'hello':'hello.json','search':'search_utf8.json','context':'selected_context.json','repos':'repo_list.json',
        'invalid_utf8':'invalid_utf8.bin','duplicate_keys':'duplicate_keys.bin','trailing_json':'trailing_json.bin',
        'nonfinite':'nonfinite.bin','profile_changed':'profile_changed.json','operation_mismatch':'operation_mismatch.json',
        'protocol_mismatch':'protocol_mismatch.json','setup_required':'setup_required.json','write_rejected':'write_rejected.json'}
    if args.scenario in files:
        reply=(fixtures/files[args.scenario]).read_bytes()
        # Small deterministic chunks exercise pipe segmentation without long waits.
        for start in range(0,len(reply),7):
            sys.stdout.buffer.write(reply[start:start+7])
        sys.stdout.buffer.flush()
    elif args.scenario in {'output_flood','stderr_flood'}:
        stream=sys.stdout.buffer if args.scenario=='output_flood' else sys.stderr.buffer
        try:
            for _ in range(200):
                stream.write(b'SYNTHETIC_FIXTURE_DATA_'*52)
                stream.flush()
        except BrokenPipeError:
            return 0
    elif args.scenario=='timeout':
        # Test must set a shorter deadline; this helper waits only one second.
        time.sleep(1)
    elif args.scenario=='nonzero':
        return 7
    else:
        raise ValueError('UNKNOWN_SYNTHETIC_SCENARIO')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
