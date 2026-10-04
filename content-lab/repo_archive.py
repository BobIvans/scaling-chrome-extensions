"""Verified portable ZIP64 export with explicit, hash-checked part recovery."""
import argparse
import errno
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import sys
import time
import uuid
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from automation_core import digest, load_json
import repo_manifest as manifest
from repo_artifacts import (BUFFER_BYTES, atomic_file, atomic_json, copy_file,
                            file_proof, json_bytes, outside, process_lock, safe_path, sync_dir)
from repo_artifacts import oid_hasher

PAGE_ROWS = 20  # Page size, never a corpus cap.
STATES = {'NEW', 'STAGING', 'ASSEMBLING', 'VERIFYING', 'PUBLISHED', 'BLOCKED', 'CANCELLED'}
BASE_NAMES = ('BATCH.json', 'BUNDLE.json', 'INDEX.html', 'PARTS_INDEX.jsonl',
              'README_RU.txt', 'REPO_MANIFEST.jsonl', 'VALIDATION.json')


def boundary(event, **context):
    """No-op seam for subprocess crash/I/O qualification; no runtime env hook."""


class Budget:
    def __init__(self, output, disk_bytes=None, seconds=None, buffer_bytes=BUFFER_BYTES):
        if type(buffer_bytes) is not int or not 1024 <= buffer_bytes <= 16 * 1024 * 1024:
            raise ValueError('BUFFER_BUDGET_REQUIRED')
        if disk_bytes is not None and (type(disk_bytes) is not int or disk_bytes <= 0):
            raise ValueError('DISK_BUDGET_REQUIRED')
        if seconds is not None and (type(seconds) not in {int, float} or not math.isfinite(seconds) or seconds <= 0):
            raise ValueError('TIME_BUDGET_REQUIRED')
        self.output, self.disk_bytes, self.seconds = output, disk_bytes, seconds
        self.buffer_bytes, self.started = buffer_bytes, time.monotonic()

    def check(self):
        if self.seconds is not None and time.monotonic() - self.started > self.seconds:
            raise ValueError('RESOURCE_BUDGET_EXCEEDED')

    def preflight(self, batch, directory):
        # Conservative capacity estimate: raw stage + uncompressed ZIP + metadata
        # and bounded static pages. Operator budget is optional and explicit.
        metadata = sum((directory / name).stat().st_size for name in manifest.METADATA)
        estimate = 2 * batch['captured_bytes'] + 4 * metadata + 4096 * (batch['entry_count'] + batch['part_count'] + 1)
        if self.disk_bytes is not None and estimate > self.disk_bytes:
            raise ValueError('RESOURCE_BUDGET_EXCEEDED')
        self.check()


def export_binding(batch, directory):
    return {'schema': 'occ.repo-archive-binding.v1', 'batch_id': batch['batch_id'],
            'metadata_sha256': {name: file_proof(directory / name)['sha256'] for name in manifest.METADATA},
            'format': 'ZIP64_V1', 'payload_policy': 'ALL_CAPTURED_INDEXED_RAW_V1',
            'index_policy': 'STATIC_PAGED_RELATIVE_HTML_V1'}


def entry_page(ordinal):
    return f'navigation/entries_{ordinal // PAGE_ROWS:020d}.html'


def part_page(ordinal, page=0):
    return f'navigation/source_{ordinal:020d}_parts_{page:020d}.html'


def approved_paths(db, snap, *, include_manifest=False):
    for name in BASE_NAMES:
        if include_manifest and name == 'INDEX.html':
            yield 'EXPORT_MANIFEST.jsonl'
        yield name
    for page in range((snap['total'] + PAGE_ROWS - 1) // PAGE_ROWS):
        yield entry_page(page * PAGE_ROWS)
    for entry in manifest.entry_rows(db, snap):
        for page in range((entry['chunk_count'] + PAGE_ROWS - 1) // PAGE_ROWS):
            yield part_page(entry['ordinal'], page)
    for part in manifest.part_rows(db, snap, order='id'):
        yield f"parts/{part['part_id']}.bin"


def shell(title, body):
    return ('<!doctype html><html lang="ru"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
            '<title>' + html.escape(title) + '</title><style>body{font:16px system-ui;max-width:1100px;'
            'margin:2rem auto;padding:0 1rem}td,th{padding:.5rem;border:1px solid #bbb;text-align:left}'
            'table{border-collapse:collapse;width:100%}code{overflow-wrap:anywhere}a{color:#1557a0}'
            '</style><h1>' + html.escape(title) + '</h1>' + body + '</html>').encode('utf-8')


def link(path, text):
    # All hrefs are generated ASCII; source paths are escaped text only.
    return '<a href="' + html.escape(path, quote=True) + '">' + html.escape(str(text)) + '</a>'


def write_html(path, title, body):
    with atomic_file(path) as stream:
        stream.write(shell(title, body))


def page_links(previous, following):
    return '<p>' + (link(previous, '← Previous') if previous else '') + ' ' + (link(following, 'Next →') if following else '') + '</p>'


def navigation(db, snap, payload, batch, budget):
    total_pages = (snap['total'] + PAGE_ROWS - 1) // PAGE_ROWS
    rows, page = [], 0

    def flush_entries():
        path = entry_page(page * PAGE_ROWS)
        body = '<p>' + link('../INDEX.html', 'Index') + '</p><table><tr><th>Source</th><th>State / reason</th><th>Parts</th></tr>' + ''.join(rows) + '</table>'
        body += page_links(Path(entry_page((page - 1) * PAGE_ROWS)).name if page else None,
                           Path(entry_page((page + 1) * PAGE_ROWS)).name if page + 1 < total_pages else None)
        write_html(payload / path, 'Sources ' + str(page + 1), body)

    for entry in manifest.entry_rows(db, snap):
        budget.check()
        ordinal = entry['ordinal']
        state = entry['state'] + (' / ' + entry['reason'] if entry['reason'] else '')
        parts = link(Path(part_page(ordinal)).name, str(entry['chunk_count'])) if entry['chunk_count'] else '0'
        rows.append(f'<tr id="source-{ordinal}"><td><code>{html.escape(entry["path"])}</code></td><td>{html.escape(state)}</td><td>{parts}</td></tr>')
        if len(rows) == PAGE_ROWS:
            flush_entries()
            page, rows = page + 1, []
        if not entry['chunk_count']:
            continue
        pages = (entry['chunk_count'] + PAGE_ROWS - 1) // PAGE_ROWS
        part_rows, part_number = [], 0

        def flush_parts():
            back = Path(entry_page(ordinal)).name + f'#source-{ordinal}'
            body = '<p><code>' + html.escape(entry['path']) + '</code> · ' + link(back, 'Source') + '</p><table><tr><th>Part</th><th>Bytes [start,end)</th><th>SHA256</th><th>Text</th></tr>' + ''.join(part_rows) + '</table>'
            body += page_links(Path(part_page(ordinal, part_number - 1)).name if part_number else None,
                               Path(part_page(ordinal, part_number + 1)).name if part_number + 1 < pages else None)
            write_html(payload / part_page(ordinal, part_number), 'Source parts', body)

        for part in db.execute('SELECT ordinal,revision,byte_start,byte_end,raw FROM repo_chunks WHERE snapshot_id=? AND path=? ORDER BY ordinal', (snap['id'], entry['path'])):
            try:
                part['raw'].decode('utf-8')
                text = True
            except UnicodeDecodeError:
                text = False
            raw_link = link('../parts/' + part['revision'] + '.bin', part['ordinal'])
            part_rows.append(f'<tr><td>{raw_link}</td><td>[{part["byte_start"]},{part["byte_end"]})</td><td><code>{hashlib.sha256(part["raw"]).hexdigest()}</code></td><td>{text}</td></tr>')
            if len(part_rows) == PAGE_ROWS:
                flush_parts()
                part_number, part_rows = part_number + 1, []
        if part_rows:
            flush_parts()
    if rows:
        flush_entries()
    body = '<p>Full captured repository context · DATA_ONLY</p><p><code>' + html.escape(snap['head']) + '</code></p>'
    body += '<p>' + html.escape(f"Entries: {batch['entry_count']} · Parts: {batch['part_count']} · Gaps: {batch['gap_count']}") + '</p>'
    body += '<p>Captured export complete. All tracked bytes exportable: ' + str(batch['all_tracked_bytes_exportable']) + '. Dependencies: NOT_GENERATED. AI delivery: NOT_PERFORMED. AI read: UNKNOWN.</p>'
    if total_pages:
        body += '<p>' + link(entry_page(0), 'All sources — paged navigation') + '</p>'
    body += '<ul>' + ''.join('<li>' + link(name, name) + '</li>' for name in ('BUNDLE.json', *manifest.METADATA, 'EXPORT_MANIFEST.jsonl', 'README_RU.txt')) + '</ul>'
    write_html(payload / 'INDEX.html', 'Portable repository context', body)


def state_value(export_id, batch, run_id, state='NEW', **fields):
    value = {'schema': 'occ.repo-export-state.v1', 'export_id': export_id,
             'batch_id': batch['batch_id'], 'run_id': run_id, 'state': state,
             'phase': state, 'completed_parts': 0, 'expected_parts': batch['part_count'],
             'completed_bytes': 0, 'last_committed_part': None, 'reason': None}
    value.update(fields)
    return value


def read_state(path, export_id, batch_id):
    safe_path(path)
    if not path.exists():
        return None
    state = load_json(safe_path(path))
    if (not isinstance(state, dict) or state.get('schema') != 'occ.repo-export-state.v1' or state.get('export_id') != export_id
            or state.get('batch_id') != batch_id or state.get('state') not in STATES
            or not re.fullmatch(r'[0-9a-f]{32}', str(state.get('run_id', '')))):
        raise ValueError('CHECKPOINT_IDENTITY_MISMATCH')
    return state


def stage_parts(db, snap, payload, state, checkpoint, budget):
    completed = size = reused = rewritten = 0
    for part, raw in manifest.part_rows(db, snap, raw=True):
        budget.check()
        target = payload / 'parts' / (part['part_id'] + '.bin')
        expected = {k: part[k] for k in ('bytes', 'sha256')}
        if target.exists() and file_proof(target, budget.buffer_bytes) == expected:
            reused += 1
        else:
            boundary('part_write', part_id=part['part_id'])
            with atomic_file(target) as stream:
                hasher = hashlib.sha256()
                for offset in range(0, len(raw), budget.buffer_bytes):
                    piece = raw[offset:offset + budget.buffer_bytes]
                    stream.write(piece)
                    hasher.update(piece)
                if len(raw) != part['bytes'] or hasher.hexdigest() != part['sha256']:
                    raise ValueError('PAYLOAD_HASH_MISMATCH')
                boundary('part_before_rename', part_id=part['part_id'])
            boundary('part_after_rename', part_id=part['part_id'])
            rewritten += 1
        completed, size = completed + 1, size + part['bytes']
        state.update(state='STAGING', phase='PARTS', completed_parts=completed,
                     completed_bytes=size, last_committed_part=part['part_id'], reason=None)
        # Files are the durable truth. Avoid a second fsync per reused part;
        # interrupted cursors/counts are always rebuilt by hashing the files.
        if completed % 100 == 0:
            atomic_json(checkpoint, state)
    atomic_json(checkpoint, state)
    return {'reused_parts': reused, 'written_parts': rewritten}


def prepare_payload(db, snap, source, directory, payload, bind, batch, budget):
    for name in manifest.METADATA:
        copy_file(directory / name, payload / name, budget.buffer_bytes, budget.check)
    # Revalidate the frozen copy; never mix metadata read before/after a change.
    manifest.verify_manifest(db, snap, source, payload)
    if export_binding(batch, payload) != bind:
        raise ValueError('BATCH_BINDING_MISMATCH')
    bundle = {'schema': 'occ.repo-archive-bundle.v1', 'export_id': digest(bind), 'binding': bind,
              'snapshot_id': snap['id'], 'repo_sha': snap['head'], 'entry_count': batch['entry_count'],
              'part_count': batch['part_count'], 'gap_count': batch['gap_count'],
              'inventory_complete': True, 'captured_export_complete': True,
              'all_tracked_bytes_exportable': batch['all_tracked_bytes_exportable'],
              'ai_delivery': 'NOT_PERFORMED', 'ai_read': 'UNKNOWN', 'dependency_graph': 'NOT_GENERATED',
              'payload_paths': 'parts/<PR002 revision>.bin', 'page_rows': PAGE_ROWS,
              'output_manifest_self_record': 'EXCLUDED_EXPLICITLY'}
    atomic_json(payload / 'BUNDLE.json', bundle)
    with atomic_file(payload / 'README_RU.txt') as stream:
        stream.write(('Откройте INDEX.html после распаковки. Все ссылки относительные и работают офлайн.\n'
                      'Исходные пути — метаданные; байты сохранены как parts/<revision>.bin.\n'
                      'Объединяйте части по source_start из PARTS_INDEX.jsonl. Диапазоны [start,end), байты exact.\n'
                      'Все INDEXED bytes включены; EXCLUDED/ERROR остаются явными gaps. Код не исполнялся.\n'
                      'EXPORT_MANIFEST.jsonl содержит SHA256 каждого output, кроме себя.\n'
                      'SHA ZIP и SHA output manifest находятся во внешнем receipt.\n').encode('utf-8'))
    navigation(db, snap, payload, batch, budget)


def write_output_manifest(db, snap, payload, budget):
    with atomic_file(payload / 'EXPORT_MANIFEST.jsonl') as stream:
        for path in approved_paths(db, snap):
            budget.check()
            proof = file_proof(payload / path, budget.buffer_bytes)
            stream.write(json_bytes(dict(schema='occ.repo-archive-output.v1', path=path, **proof)))


def assemble(db, snap, payload, partial, budget):
    safe_path(partial)
    boundary('zip_write')
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(partial, flags, 0o600), 'wb') as archive:
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
            for path in approved_paths(db, snap, include_manifest=True):
                budget.check()
                # Explicit ZIP64 even for small fixtures, exact generated paths.
                info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100600 << 16
                with safe_path(payload / path).open('rb') as incoming, zf.open(info, 'w', force_zip64=True) as outgoing:
                    while raw := incoming.read(budget.buffer_bytes):
                        budget.check()
                        outgoing.write(raw)
                        boundary('zip_chunk', path=path)
        archive.flush()
        os.fsync(archive.fileno())


def stream_proof(stream, budget):
    size, hasher = 0, hashlib.sha256()
    while raw := stream.read(budget.buffer_bytes):
        budget.check()
        size += len(raw)
        hasher.update(raw)
    return {'bytes': size, 'sha256': hasher.hexdigest()}


def verify_zip(path, db, snap, payload, budget):
    try:
        with zipfile.ZipFile(safe_path(path)) as zf:
            # NameToInfo overwrites duplicates; compare lengths before lookup.
            if len(zf.filelist) != len(zf.NameToInfo):
                raise ValueError('ZIP_INVALID')
            count = 1
            with (payload / 'EXPORT_MANIFEST.jsonl').open('rb') as expected:
                for line in expected:
                    output = json.loads(line)
                    with zf.open(output['path']) as member:
                        proof = stream_proof(member, budget)
                    if proof != {k: output[k] for k in ('bytes', 'sha256')}:
                        raise ValueError('ZIP_INVALID')
                    count += 1
            if count != len(zf.filelist):
                raise ValueError('ZIP_INVALID')
            with zf.open('EXPORT_MANIFEST.jsonl') as member:
                if stream_proof(member, budget) != file_proof(payload / 'EXPORT_MANIFEST.jsonl', budget.buffer_bytes):
                    raise ValueError('ZIP_INVALID')
            # Independently reconstruct sources from archive members, including
            # empty and binary sources; original Git OID is verified again.
            for entry in manifest.entry_rows(db, snap):
                if entry['state'] != 'INDEXED':
                    continue
                cursor, hasher = 0, hashlib.sha256()
                git_hash = oid_hasher(entry['git_oid'], entry['size'])
                for part in db.execute('SELECT revision,byte_start,byte_end FROM repo_chunks WHERE snapshot_id=? AND path=? ORDER BY ordinal', (snap['id'], entry['path'])):
                    if part['byte_start'] != cursor:
                        raise ValueError('ZIP_INVALID')
                    with zf.open('parts/' + part['revision'] + '.bin') as member:
                        while raw := member.read(budget.buffer_bytes):
                            budget.check()
                            hasher.update(raw)
                            git_hash.update(raw)
                            cursor += len(raw)
                    if cursor != part['byte_end']:
                        raise ValueError('ZIP_INVALID')
                if cursor != entry['size'] or hasher.hexdigest() != entry['file_sha256'] or git_hash.hexdigest() != entry['git_oid']:
                    raise ValueError('ZIP_INVALID')
    except (zipfile.BadZipFile, KeyError, RuntimeError, EOFError) as exc:
        raise ValueError('ZIP_INVALID') from exc
    return file_proof(path, budget.buffer_bytes)


def build(profile_path, alias, directory, output, *, action='BUILD',
          disk_bytes=None, seconds=None, buffer_bytes=BUFFER_BYTES):
    started = time.monotonic()
    if action not in {'BUILD', 'RESUME', 'STATUS', 'NEW_RUN'}:
        raise ValueError('EXPORT_ACTION_REQUIRED')
    store, source = manifest.operator_scope(profile_path, alias)
    directory = safe_path(directory, directory=True)
    if not all((directory / name).is_file() for name in manifest.METADATA):
        raise ValueError('PR002_PREREQUISITE_MISSING')
    batch_input = load_json(directory / 'BATCH.json')
    if not isinstance(batch_input, dict) or not isinstance(batch_input.get('binding'), dict):
        raise ValueError('BATCH_BINDING_MISMATCH')
    with manifest.snapshot_view(store, source, alias, batch_input.get('binding', {}).get('snapshot_id')) as (db, snap):
        batch = manifest.verify_manifest(db, snap, source, directory)
        bind = export_binding(batch, directory)
        export_id = digest(bind)
        output = outside(output, source['root'], store, directory)
        stage = output / ('.stage-' + export_id)
        payload, checkpoint = stage / 'payload', stage / 'EXPORT_STATE.json'
        final = output / ('REPO_' + export_id + '.zip')
        partial = output / (final.name + '.partial')
        receipt_path = output / ('REPO_' + export_id + '.receipt.json')
        for path in (stage, payload):
            safe_path(path, directory=True)
        state = read_state(checkpoint, export_id, batch['batch_id'])
        if action == 'STATUS':
            status = dict(state) if state else state_value(export_id, batch, None)
            completed = size = 0
            for part in manifest.part_rows(db, snap):
                target = payload / 'parts' / (part['part_id'] + '.bin')
                if target.exists() and file_proof(target) == {k: part[k] for k in ('bytes', 'sha256')}:
                    completed += 1
                    size += part['bytes']
            status.update(completed_parts=completed, completed_bytes=size)
            return status
        output.mkdir(parents=True, exist_ok=True, mode=0o700)
        budget = Budget(output, disk_bytes, seconds, buffer_bytes)
        budget.started = started
        with process_lock(output / ('.lock-' + export_id)):
            # Reload under the writer lock; pre-lock state may have moved.
            state = read_state(checkpoint, export_id, batch['batch_id'])
            if state and action == 'RESUME' and state['state'] == 'CANCELLED':
                raise ValueError('CANCELLED_REQUIRES_NEW_RUN')
            if state and action == 'BUILD' and state['state'] != 'PUBLISHED':
                raise ValueError('EXPLICIT_RESUME_REQUIRED')
            stage.mkdir(exist_ok=True, mode=0o700)
            payload.mkdir(exist_ok=True, mode=0o700)
            if state and action == 'NEW_RUN':
                atomic_json(stage / ('RUN_' + state['run_id'] + '.json'), state)
                state = None
            if state is None:
                state = state_value(export_id, batch, uuid.uuid4().hex)
            atomic_json(checkpoint, state)
            try:
                budget.preflight(batch, directory)
                state.update(state='STAGING', phase='METADATA', reason=None)
                atomic_json(checkpoint, state)
                prepare_payload(db, snap, source, directory, payload, bind, batch, budget)
                stats = stage_parts(db, snap, payload, state, checkpoint, budget)
                write_output_manifest(db, snap, payload, budget)
                # Profile revocation during a run blocks publication.
                if manifest.operator_scope(profile_path, alias) != (store, source):
                    raise ValueError('PROFILE_CHANGED')
                if final.exists():
                    try:
                        archive_proof = verify_zip(final, db, snap, payload, budget)
                    except (ValueError, OSError) as exc:
                        if str(exc) == 'RESOURCE_BUDGET_EXCEEDED':
                            raise
                        raise ValueError('OUTPUT_CONFLICT') from exc
                    reconciled = True
                else:
                    state.update(state='ASSEMBLING', phase='ZIP')
                    atomic_json(checkpoint, state)
                    assemble(db, snap, payload, partial, budget)
                    state.update(state='VERIFYING', phase='ZIP')
                    atomic_json(checkpoint, state)
                    archive_proof = verify_zip(partial, db, snap, payload, budget)
                    boundary('publish_before_rename')
                    if manifest.operator_scope(profile_path, alias) != (store, source):
                        raise ValueError('PROFILE_CHANGED')
                    os.replace(partial, final)
                    sync_dir(output)
                    boundary('publish_after_rename')
                    reconciled = False
                if manifest.operator_scope(profile_path, alias) != (store, source):
                    raise ValueError('PROFILE_CHANGED')
                receipt = {'schema': 'occ.repo-archive-receipt.v1', 'export_id': export_id,
                           'batch_id': batch['batch_id'], 'run_id': state['run_id'],
                           'state': 'PUBLISHED', 'archive': dict(path=final.name, **archive_proof),
                           'output_manifest': file_proof(payload / 'EXPORT_MANIFEST.jsonl', buffer_bytes),
                           'entry_count': batch['entry_count'], 'part_count': batch['part_count'],
                           'captured_bytes': batch['captured_bytes'], 'gap_count': batch['gap_count'],
                           'inventory_complete': True, 'captured_export_complete': True,
                           'all_tracked_bytes_exportable': batch['all_tracked_bytes_exportable'],
                           'proof_scope': 'ARCHIVE_MEMBERS_AND_INDEXED_GIT_BYTES_V1',
                           'ai_delivery': 'NOT_PERFORMED', 'ai_read': 'UNKNOWN', 'dependencies': 'NOT_GENERATED'}
                with atomic_file(final.with_name(final.name + '.sha256')) as stream:
                    stream.write((archive_proof['sha256'] + '  ' + final.name + '\n').encode('ascii'))
                atomic_json(receipt_path, receipt)
                state.update(state='PUBLISHED', phase='COMPLETE', reason=None)
                atomic_json(checkpoint, state)
                return dict(receipt, **stats, reconciled=reconciled, archive_path=str(final))
            except (ValueError, OSError, KeyboardInterrupt) as exc:
                reason = ('CANCELLED' if isinstance(exc, KeyboardInterrupt) else
                          'DISK_FULL' if isinstance(exc, OSError) and exc.errno == errno.ENOSPC else
                          'PERMISSION_DENIED' if isinstance(exc, OSError) and exc.errno in {errno.EACCES, errno.EPERM} else
                          'IO_ERROR' if isinstance(exc, OSError) else str(exc))
                state.update(state='CANCELLED' if isinstance(exc, KeyboardInterrupt) else 'BLOCKED', reason=reason)
                try:
                    atomic_json(checkpoint, state)
                except OSError:
                    pass  # Genuine disk-full may also prevent checkpoint writes.
                raise ValueError(reason) from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    flags = parser.add_mutually_exclusive_group()
    flags.add_argument('--resume', action='store_true')
    flags.add_argument('--status', action='store_true')
    flags.add_argument('--new-run', action='store_true')
    parser.add_argument('--disk-budget-bytes', type=int)
    parser.add_argument('--time-budget-seconds', type=float)
    parser.add_argument('--buffer-bytes', type=int, default=BUFFER_BYTES)
    args = parser.parse_args(argv)
    action = 'RESUME' if args.resume else 'STATUS' if args.status else 'NEW_RUN' if args.new_run else 'BUILD'
    try:
        result = build(args.profile, args.repository, args.manifest, args.output, action=action,
                       disk_bytes=args.disk_budget_bytes, seconds=args.time_budget_seconds,
                       buffer_bytes=args.buffer_bytes)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'state': 'BLOCKED', 'reason': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
