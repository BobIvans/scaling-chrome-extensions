"""Test-only fault transport; configuration never flows from UI requests."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument('--profile', required=True, type=Path)
parser.add_argument('--desktop-stdio', action='store_true')
args = parser.parse_args()
profile = json.loads(args.profile.read_text(encoding='utf-8'))
request = json.loads(sys.stdin.buffer.read(16_001))
scenario = profile['scenario']
root = Path(__file__).parent / 'fixtures'

if scenario == 'timeout':
    time.sleep(2)
elif scenario in {'stdout_flood', 'stderr_flood', 'combined_flood'}:
    if scenario == 'combined_flood':
        for _ in range(25):
            sys.stdout.buffer.write(b'x' * 4096)
            sys.stdout.buffer.flush()
            sys.stderr.buffer.write(b'x' * 4096)
            sys.stderr.buffer.flush()
    else:
        stream = sys.stdout.buffer if scenario == 'stdout_flood' else sys.stderr.buffer
        for _ in range(64):
            stream.write(b'x' * 4096)
            stream.flush()
elif scenario == 'nonzero':
    raise SystemExit(7)
elif scenario in {'invalid_utf8', 'duplicate_keys', 'nonfinite', 'trailing_json'}:
    sys.stdout.buffer.write((root / (scenario + '.bin')).read_bytes())
else:
    files = {'hello': 'hello.json', 'search': 'search_utf8.json', 'context': 'selected_context.json',
             'profile_changed': 'profile_changed.json', 'operation_mismatch': 'operation_mismatch.json',
             'protocol_mismatch': 'protocol_mismatch.json', 'setup_required': 'setup_required.json'}
    value = json.loads((root / files.get(scenario, 'hello.json')).read_bytes())
    if value['adapter_context'] is not None:
        value['adapter_context']['adapter_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if scenario == 'unknown_field':
        value['unexpected'] = True
    if scenario == 'tampered_context':
        value = json.loads((root / 'selected_context.json').read_bytes())
        value['adapter_context']['adapter_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        value['result']['context']['items'][0]['text'] += 'changed'
        value['result']['context']['bytes'] += 7
    if scenario == 'stderr_small':
        sys.stderr.buffer.write(b'PRIVATE_FIXTURE_DO_NOT_LOG' * 100)
    raw = json.dumps(value, ensure_ascii=False).encode('utf-8')
    for start in range(0, len(raw), 7):
        sys.stdout.buffer.write(raw[start:start + 7])
    sys.stdout.buffer.flush()
