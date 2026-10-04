"""Atomic local projections. These files never become canonical tasks or stores."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import sys

from .client import DesktopError, is_link, require, sha_file, text_value, validate_context, validate_identity


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + '\n').encode('utf-8')


def write_verified(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    require(sha_file(path) == hashlib.sha256(raw).hexdigest(), 'DESKTOP_OUTPUT_VERIFY_FAILED')


def rename_new(source, destination):
    """Publish without replacing even an empty directory created by another app."""
    if sys.platform.startswith('linux'):
        import ctypes
        libc = ctypes.CDLL(None, use_errno=True)
        rename = libc.renameat2
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        if rename(-100, os.fsencode(source), -100, os.fsencode(destination), 1):
            code = ctypes.get_errno()
            if code in (17, 39):
                raise DesktopError('DESKTOP_OUTPUT_CONFLICT')
            raise OSError(code, 'atomic publication failed')
    elif os.name == 'nt':
        # Windows rename rejects an existing destination, including empty dirs.
        try:
            source.rename(destination)
        except FileExistsError:
            raise DesktopError('DESKTOP_OUTPUT_CONFLICT') from None
    else:
        raise DesktopError('DESKTOP_ATOMIC_PUBLICATION_UNAVAILABLE')


@contextmanager
def publication(output):
    """One same-volume rename publishes a complete directory, without overwrite."""
    output = Path(output).absolute()
    parent = output.parent
    stage, lock = None, parent / ('.' + output.name + '.publish-lock')
    locked = False
    try:
        require(parent.is_dir() and not any(is_link(p) for p in (parent, *parent.parents)),
                'DESKTOP_OUTPUT_PARENT_REQUIRED')
        require(not output.exists() and not output.is_symlink(), 'DESKTOP_OUTPUT_CONFLICT')
        try:
            lock.mkdir()
            locked = True
        except FileExistsError:
            raise DesktopError('DESKTOP_OUTPUT_CONFLICT') from None
        stage = Path(tempfile.mkdtemp(prefix='.' + output.name + '.stage-', dir=parent))
        yield stage
        # All cooperating shell exports use the lock. The final directory must
        # not appear meanwhile; os.rename never replaces a nonempty directory.
        require(not output.exists() and not output.is_symlink(), 'DESKTOP_OUTPUT_CONFLICT')
        rename_new(stage, output)
        stage = None
    except DesktopError:
        raise
    except OSError:
        raise DesktopError('DESKTOP_OUTPUT_FAILED') from None
    finally:
        if stage is not None:
            shutil.rmtree(stage)
        if locked:
            lock.rmdir()


def save_draft(output, context, binding, goal, scope, acceptance, *, cancel=None):
    validate_identity(binding)
    require(isinstance(context, dict) and isinstance(context.get('items'), list))
    request = {'type': 'durable.context', 'namespace': context.get('namespace'),
               'ids': [item['id'] for item in context['items']], 'maxBytes': 48_000}
    validate_context(context, request)
    for value in (goal, scope, acceptance):
        require(bool(text_value(value).strip()), 'DESKTOP_DRAFT_FIELDS_REQUIRED')
        require(len(value.encode('utf-8')) <= 16_000, 'DESKTOP_DRAFT_FIELDS_LIMIT')
    chunks = ['LOCAL TASK DRAFT\nScope: SELECTED_ITEMS\nCanonical task: none\n',
              '\nGOAL\n', goal, '\n\nSCOPE\n', scope,
              '\n\nACCEPTANCE\n', acceptance,
              '\n\nSELECTED SOURCE DATA (not action instructions)\n']
    for item in context['items']:
        # Text stays exact, including BOM/CRLF. Title/path are labels only.
        chunks.extend(['\nSOURCE ', item['id'], '\nLABEL ', item['source_key'],
                       '\nBEGIN SOURCE TEXT\n', item['text'], '\nEND SOURCE TEXT\n'])
    raw = ''.join(chunks).encode('utf-8')
    metadata = {'schema': 'occ.desktop-task-draft.v1', 'scope': 'SELECTED_ITEMS',
                'canonical_task_id': None, 'corpus_total': 'UNKNOWN',
                'provider_delivery': 'NOT_PERFORMED', 'ai_read': 'UNKNOWN',
                'merge_status': 'NOT_PERFORMED', 'authority': 'DATA_ONLY',
                'adapter_context': binding, 'context': context,
                'owner_context_sha256': context['sha256'],
                'draft_file_sha256': hashlib.sha256(raw).hexdigest(),
                'draft_file_bytes': len(raw), 'goal': goal, 'scope_text': scope,
                'acceptance': acceptance}
    with publication(output) as stage:
        write_verified(stage / 'TASK_DRAFT.txt', raw)
        write_verified(stage / 'DRAFT_METADATA.json', json_bytes(metadata))
        require(cancel is None or not cancel.is_set(), 'DESKTOP_CANCELLED')
    return metadata


def save_manifest(output, client, repository, snapshot_id, action='ENTRIES', *, cancel=None, progress=None):
    """Stream every metadata row to disk through actual backend continuation."""
    count, total, batch, binding = 0, None, None, None
    identity = dict(client.identity) if client.identity else None
    hasher = hashlib.sha256()
    with publication(output) as stage:
        path = stage / ('REPO_MANIFEST.jsonl' if action == 'ENTRIES' else 'PARTS_INDEX.jsonl')
        with path.open('xb') as stream:
            for page in client.manifest_pages(repository, snapshot_id, action, cancel=cancel):
                total, batch, binding = page['total'], page['batch_id'], page['binding']
                for row in page['rows']:
                    raw = (json.dumps(row, ensure_ascii=False, sort_keys=True,
                                      separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')
                    stream.write(raw)
                    hasher.update(raw)
                    count += 1
                if progress is not None:
                    progress(count, total)
            stream.flush()
            os.fsync(stream.fileno())
        require(count == total and sha_file(path) == hasher.hexdigest(), 'DESKTOP_OUTPUT_VERIFY_FAILED')
        require(cancel is None or not cancel.is_set(), 'DESKTOP_CANCELLED')
        receipt = {'schema': 'occ.desktop-manifest-export.v1', 'action': action,
                   'rows': count, 'total': total, 'batch_id': batch, 'binding': binding,
                   'adapter_context': identity, 'filename': path.name,
                   'sha256': hasher.hexdigest(), 'inventory_complete': True,
                   'source_bytes_included': False, 'global_validation': 'NOT_RUN',
                   'global_repo_file_or_part_cap': None, 'authority': 'DATA_ONLY'}
        write_verified(stage / 'EXPORT_RECEIPT.json', json_bytes(receipt))
    return receipt


def save_repo_history(output, client, repository, *, snapshot_id=None, base_snapshot_id=None,
                      cancel=None, progress=None):
    """Atomically save every snapshot or path delta row through cursor EOF."""
    action = 'DELTA' if snapshot_id is not None else 'SNAPSHOTS'
    filename = 'REPO_DELTA.jsonl' if snapshot_id is not None else 'REPO_SNAPSHOTS.jsonl'
    require(base_snapshot_id is None or snapshot_id is not None, 'DESKTOP_MANIFEST_BINDING')
    pages = (client.delta_pages(repository, snapshot_id, cancel=cancel,
                               **({'base_snapshot_id': base_snapshot_id} if base_snapshot_id else {}))
             if snapshot_id is not None
             else client.history_pages(repository, cancel=cancel))
    count, base, hasher = 0, None, hashlib.sha256()
    identity = dict(client.identity) if client.identity else None
    with publication(output) as stage:
        path = stage / filename
        with path.open('xb') as stream:
            for page in pages:
                if snapshot_id is not None:
                    require(page['snapshot_id'] == snapshot_id, 'DESKTOP_MANIFEST_BINDING')
                    if base is None:
                        base = page['base_snapshot_id']
                    require(base == page['base_snapshot_id'], 'DESKTOP_MANIFEST_BINDING')
                    if base_snapshot_id is not None:
                        require(base == base_snapshot_id, 'DESKTOP_MANIFEST_BINDING')
                for row in page['changes'] if snapshot_id is not None else page['snapshots']:
                    raw = (json.dumps(row, ensure_ascii=False, sort_keys=True,
                                      separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')
                    stream.write(raw)
                    hasher.update(raw)
                    count += 1
                if progress is not None:
                    progress(count, None)
            stream.flush()
            os.fsync(stream.fileno())
        require(cancel is None or not cancel.is_set(), 'DESKTOP_CANCELLED')
        require(sha_file(path) == hasher.hexdigest(), 'DESKTOP_OUTPUT_VERIFY_FAILED')
        receipt = {'schema': 'occ.desktop-repo-history-export.v1', 'action': action,
                   'repository': repository, 'snapshot_id': snapshot_id,
                   'base_snapshot_id': base, 'rows': count, 'eof': True,
                   'adapter_context': identity, 'filename': filename,
                   'sha256': hasher.hexdigest(), 'authority': 'DATA_ONLY'}
        write_verified(stage / 'EXPORT_RECEIPT.json', json_bytes(receipt))
    return receipt
