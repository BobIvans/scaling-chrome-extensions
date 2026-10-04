"""Synthetic metadata codec only: NOT a Git/process/staging application adapter."""
from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import PurePosixPath


def records(blocks, max_record_bytes=65536):
    carry = bytearray()
    for block in blocks:
        if not isinstance(block, bytes):
            raise ValueError('BINARY_BLOCK_REQUIRED')
        carry.extend(block)
        start = 0
        while True:
            end = carry.find(0, start)
            if end < 0:
                break
            if end == start:
                raise ValueError('EMPTY_RECORD')
            if end-start > max_record_bytes:
                raise ValueError('RECORD_LIMIT')
            yield bytes(carry[start:end])
            start = end+1
        if start:
            del carry[:start]
        if len(carry) > max_record_bytes:
            raise ValueError('RECORD_LIMIT')
    if carry:
        raise ValueError('UNTERMINATED_RECORD')


def entry(raw, ordinal):
    try:
        header, path = raw.split(b'\t', 1)
        mode, kind, oid, size = header.split()
        mode, kind, oid, size = (v.decode('ascii') for v in (mode, kind, oid, size))
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError('HEADER_INVALID') from exc
    if ((mode, kind) not in {('100644','blob'),('100755','blob'),('120000','blob'),('160000','commit')}
            or re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', oid) is None
            or not path or (not size.isdecimal() and size not in {'-', 'BAD'})):
        raise ValueError('METADATA_INVALID')
    if kind == 'commit' and size != '-':
        raise ValueError('COMMIT_SIZE_INVALID')
    try:
        text = path.decode('utf-8')
        if (len(path)>800 or '\\' in text or ':' in text
                or any(v in {'','.','..'} for v in text.split('/'))
                or PurePosixPath(text).is_absolute()):
            raise ValueError('PATH_INVALID')
        state, reason = 'PENDING', None
    except (ValueError, UnicodeDecodeError):
        text = 'git-path-hex:'+path.hex()
        state, reason = 'EXCLUDED', 'UNSUPPORTED_PATH'
    if kind != 'blob' or mode == '120000':
        state, reason = 'EXCLUDED', 'LINK_OR_SUBMODULE_METADATA_ONLY'
    elif re.search(r'(^|/)(\.env($|\.)|id_rsa$|id_ed25519$|credentials\.json$|keypair\.json$)|\.(pem|p12|pfx|key)$', text, re.I):
        state, reason = 'EXCLUDED', 'PROTECTED_NAME_OR_OPERATOR_EXCLUSION'
    elif not size.isdecimal():
        state, reason = 'ERROR', 'BLOB_SIZE_UNAVAILABLE'
    return {'ordinal':ordinal,'path_b64':base64.b64encode(path).decode('ascii'),
            'path':text,'mode':mode,'kind':kind,'oid':oid,
            'size':int(size) if size.isdecimal() else None,'state':state,'reason':reason}


def decoded(blocks):
    for ordinal, raw in enumerate(records(blocks)):
        yield entry(raw, ordinal)


def summary(blocks):
    digest = hashlib.sha256()
    count, first, last = 0, None, None
    for value in decoded(blocks):
        digest.update(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()+b'\n')
        first = first or value
        last = value
        count += 1
    return {'entries':count,'first':first,'last':last,'normalized_sha256':digest.hexdigest(),
            'scope':'SYNTHETIC_FIXTURE_CODEC_ONLY_NOT_APPLICATION'}
