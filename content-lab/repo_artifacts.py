"""Local artifact primitives shared by foreground repository projections."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat

BUFFER_BYTES = 65536


def oid_hasher(oid, size):
    if not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', oid):
        raise ValueError('REPO_GIT_OID_REQUIRED')
    hasher = hashlib.sha1() if len(oid) == 40 else hashlib.sha256()
    hasher.update(b'blob ' + str(size).encode('ascii') + b'\0')
    return hasher


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def safe_path(path, *, directory=False):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError('ABSOLUTE_ARTIFACT_PATH_REQUIRED')
    for component in (path, *path.parents):
        if component.is_symlink() or getattr(component, 'is_junction', lambda: False)():
            raise ValueError('ARTIFACT_LINK_FORBIDDEN')
        if component.exists() and component != path and not component.is_dir():
            raise ValueError('ARTIFACT_DIRECTORY_REQUIRED')
    if path.exists() and (not path.is_dir() if directory else not path.is_file()):
        raise ValueError('ARTIFACT_TYPE_REQUIRED')
    return path.resolve()


def outside(path, *roots):
    target = safe_path(path, directory=True)
    for root in roots:
        root = Path(root).resolve()
        if target.is_relative_to(root) or root.is_relative_to(target):
            raise ValueError('OUTPUT_MUST_BE_OUTSIDE_SOURCE_STORE_INPUT')
    return target


def sync_dir(path):
    if os.name == 'posix':
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


@contextmanager
def atomic_file(path):
    path = safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    safe_path(temporary)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(temporary, flags, 0o600), 'wb') as stream:
        yield stream
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    sync_dir(path.parent)


def atomic_json(path, value):
    with atomic_file(path) as stream:
        stream.write(json_bytes(value))


def file_proof(path, buffer_bytes=BUFFER_BYTES):
    path = safe_path(path)
    size, hasher = 0, hashlib.sha256()
    with path.open('rb') as stream:
        while raw := stream.read(buffer_bytes):
            size += len(raw)
            hasher.update(raw)
    return {'bytes': size, 'sha256': hasher.hexdigest()}


def copy_file(source, target, buffer_bytes=BUFFER_BYTES, progress=lambda: None):
    safe_path(source)
    with Path(source).open('rb') as incoming, atomic_file(target) as outgoing:
        while raw := incoming.read(buffer_bytes):
            progress()
            outgoing.write(raw)


@contextmanager
def process_lock(path):
    """Kernel lock: process death releases it on Windows and POSIX."""
    path = safe_path(path)
    flags = os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, 0o600)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise ValueError('ARTIFACT_TYPE_REQUIRED')
    stream = os.fdopen(fd, 'r+b', buffering=0)
    acquired = False
    try:
        if os.name == 'nt':
            import msvcrt
            if os.fstat(fd).st_size == 0:
                stream.write(b'0')
            stream.seek(0)
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise ValueError('EXPORT_LOCKED') from exc
        else:
            import fcntl
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ValueError('EXPORT_LOCKED') from exc
        acquired = True
        yield
    finally:
        if acquired:
            if os.name == 'nt':
                stream.seek(0)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_UN)
        stream.close()
