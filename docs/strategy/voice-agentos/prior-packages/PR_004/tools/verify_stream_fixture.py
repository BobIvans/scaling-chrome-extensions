"""Check golden data through varied boundaries and rejected malformed streams."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from inventory_fixture_oracle import decoded, records

ROOT = Path(__file__).resolve().parents[1]


def run():
    p = ROOT/'fixtures/stream_golden'
    raw = (p/'LS_TREE_OUTPUT.bin').read_bytes()
    expected = json.loads((p/'EXPECTED_ENTRIES.json').read_text())
    assert len(raw)==expected['raw_bytes'] and hashlib.sha256(raw).hexdigest()==expected['raw_sha256']
    assert len(expected['entries'])==expected['count']==55
    splits = [1,2,3,7,31,257,4096,65536]
    for step in splits:
        assert list(decoded(raw[i:i+step] for i in range(0,len(raw),step)))==expected['entries']
    # Check every possible two-block cut, including cuts within TAB and UTF8/path data.
    for i in range(len(raw)+1):
        assert list(decoded(iter([raw[:i],raw[i:]])))==expected['entries']
    for e in expected['entries']:
        if e['path'].startswith('git-path-hex:'):
            assert bytes.fromhex(e['path'].split(':',1)[1]) == base64.b64decode(e['path_b64'])
    assert expected['entries'][-1]['path']=='zz-LAST_AFTER_39.py'
    assert expected['entries'][53]['size']==8388609 and expected['entries'][53]['state']=='PENDING'
    assert list(decoded(iter([])))==[]
    bad=[raw[:-1],b'\0',b'header\tpath\0',b'100644 blob BAD 2\tfile.py\0',
         b'100644 commit '+b'1'*40+b' -\tsub\0',b'100644 blob '+b'1'*40+b' 2\t\0',
         b'100644 blob '+b'1'*40+b' nope\tfile.py\0']
    rejected=0
    for stream in bad:
        try:
            list(decoded(iter([stream])))
        except ValueError:
            rejected += 1
    try:
        list(records(iter([b'x'*65537])))
    except ValueError:
        rejected+=1
    assert rejected==len(bad)+1
    # Missing-object metadata is an explicit existing gap, not silent dropping.
    missing=list(decoded(iter([b'100644 blob '+b'2'*40+b' BAD\tmissing.py\0'])))
    assert missing[0]['state']=='ERROR' and missing[0]['reason']=='BLOB_SIZE_UNAVAILABLE'
    return {'status':'PASS','scope':'Synthetic fixture codec only; no application imported',
            'entries':55,'raw_bytes':len(raw),'split_sizes':splits,
            'exhaustive_two_block_cuts':len(raw)+1,'malformed_streams_rejected':rejected,
            'application_runtime_executed':False}


if __name__=='__main__':
    print(json.dumps(run(),ensure_ascii=False,indent=2))
