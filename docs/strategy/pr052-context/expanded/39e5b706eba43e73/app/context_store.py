"""Offline desktop context prototype. Python 3.11+, standard library only.

No source-count/file-size cap. Original bytes are authoritative; extracted text
is a derivative. This is NOT a production migration of SCE's content.sqlite3.
"""
from __future__ import annotations
import argparse
import codecs
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import tempfile
import time
import uuid
import zipfile

BLOCK = 65536  # I/O batch, never a total-size limit

def dumps(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True)

def stamp():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

def linklike(path):
    st = path.lstat()
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, 'st_file_attributes', 0) & 0x400)

class Paused(Exception):
    pass

class Store:
    def __init__(self, root, reserve_bytes=64 * 1024 * 1024):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.blobs = self.root / 'blobs'
        self.blobs.mkdir(exist_ok=True)
        self.reserve_bytes = reserve_bytes
        self.db = sqlite3.connect(self.root / 'desktop-prototype.sqlite3', timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS snapshots(
          id TEXT PRIMARY KEY, kind TEXT, source TEXT, archive_sha TEXT,
          state TEXT, created TEXT, error TEXT);
        CREATE TABLE IF NOT EXISTS entries(
          id INTEGER PRIMARY KEY, snapshot TEXT REFERENCES snapshots(id),
          ordinal INTEGER, path TEXT, kind TEXT, sha256 TEXT, size INTEGER,
          text_state TEXT, encoding TEXT, error TEXT, metadata TEXT,
          UNIQUE(snapshot, ordinal));
        CREATE TABLE IF NOT EXISTS chunks(
          id INTEGER PRIMARY KEY, entry INTEGER REFERENCES entries(id),
          seq INTEGER, text TEXT, UNIQUE(entry, seq));
        CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(text, entry UNINDEXED);
        CREATE TABLE IF NOT EXISTS annotations(
          entry INTEGER PRIMARY KEY REFERENCES entries(id), tags TEXT, note TEXT);
        CREATE TABLE IF NOT EXISTS derived_messages(
          id TEXT PRIMARY KEY, entry INTEGER REFERENCES entries(id),
          conversation TEXT, title TEXT, message TEXT, role TEXT, created TEXT,
          parent TEXT, text TEXT, parts_json TEXT);
        ''')
        self.db.commit()

    def close(self):
        self.db.close()

    def blob_path(self, digest):
        if not digest or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('Invalid content digest')
        return self.blobs / digest[:2] / digest

    def put(self, stream, cancel=lambda: False):
        h = hashlib.sha256()
        size = 0
        fd, temporary = tempfile.mkstemp(dir=self.root, prefix='ingest-')
        try:
            with os.fdopen(fd, 'wb') as out:
                while True:
                    if cancel():
                        raise Paused('Остановлено пользователем; сохранённые записи доступны.')
                    data = stream.read(BLOCK)
                    if not data:
                        break
                    if shutil.disk_usage(self.root).free < len(data) + self.reserve_bytes:
                        raise Paused('Недостаточно свободного диска; измените резерв или освободите место.')
                    out.write(data)
                    h.update(data)
                    size += len(data)
                out.flush()
                os.fsync(out.fileno())
            digest = h.hexdigest()
            target = self.blob_path(digest)
            target.parent.mkdir(exist_ok=True)
            if target.exists():
                # Check an existing object rather than silently trusting a damaged cache.
                with target.open('rb') as source:
                    if hashlib.file_digest(source, 'sha256').hexdigest() != digest:
                        raise ValueError('CORRUPT_EXISTING_BLOB: ' + digest)
                os.unlink(temporary)
            else:
                os.replace(temporary, target)
            return digest, size
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise

    def _derive(self, entry, digest):
        source = self.blob_path(digest)
        with source.open('rb') as f:
            prefix = f.read(4)
        encoding = 'utf-32' if prefix.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)) else (
            'utf-16' if prefix.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)) else 'utf-8')
        decoder = codecs.getincrementaldecoder(encoding)(errors='strict')
        seq = 0
        try:
            with source.open('rb') as f:
                while True:
                    raw = f.read(BLOCK)
                    text = decoder.decode(raw, final=not raw)
                    # NUL/binary controls are not treated as readable source text.
                    if any(ord(c) < 32 and c not in '\t\r\n\f' for c in text):
                        raise ValueError('BINARY_OR_CONTROL_CHARACTERS')
                    if text:
                        self.db.execute('INSERT INTO chunks(entry,seq,text) VALUES(?,?,?)', (entry, seq, text))
                        self.db.execute('INSERT INTO search(text,entry) VALUES(?,?)', (text, entry))
                        seq += 1
                    if not raw:
                        break
            return 'TEXT_COMPLETE', encoding, None
        except (UnicodeError, ValueError) as e:
            self.db.execute('DELETE FROM chunks WHERE entry=?', (entry,))
            self.db.execute('DELETE FROM search WHERE entry=?', (entry,))
            return 'RAW_ONLY', None, type(e).__name__ + ': ' + str(e)

    def _entry(self, snapshot, ordinal, path, kind, digest=None, size=0, metadata=None, error=None):
        with self.db:
            cur = self.db.execute('''INSERT INTO entries(snapshot,ordinal,path,kind,sha256,size,
                text_state,metadata,error) VALUES(?,?,?,?,?,?,?,?,?)''',
                (snapshot, ordinal, path, kind, digest, size, 'PENDING', dumps(metadata or {}), error))
            entry = cur.lastrowid
            if error:
                state, encoding = 'ERROR', None
            elif kind == 'file':
                state, encoding, error = self._derive(entry, digest)
            else:
                state, encoding = 'METADATA_ONLY' if kind == 'directory' else 'RAW_ONLY', None
            self.db.execute('UPDATE entries SET text_state=?,encoding=?,error=? WHERE id=?', (state, encoding, error, entry))
        return entry

    def import_source(self, path, progress=lambda x: None, cancel=lambda: False, resume=None):
        path = Path(path).resolve()
        if not resume and (path == self.root or (path.is_dir() and self.root.is_relative_to(path))):
            raise ValueError('Выберите библиотеку вне импортируемой папки.')
        if resume:
            row = self.db.execute('SELECT * FROM snapshots WHERE id=?', (resume,)).fetchone()
            if not row or row['kind'] != 'zip':
                raise ValueError('Продолжение доступно только для сохранённого ZIP snapshot.')
            sid, kind, archive_sha = resume, row['kind'], row['archive_sha']
            if not archive_sha:
                raise ValueError('Оригинал ZIP не успел сохраниться. Импортируйте исходник заново.')
        else:
            kind = 'folder' if path.is_dir() else ('zip' if zipfile.is_zipfile(path) else 'file')
            sid, archive_sha = uuid.uuid4().hex, None
            with self.db:
                self.db.execute('INSERT INTO snapshots VALUES(?,?,?,?,?,?,?)', (sid, kind, str(path), None, 'RUNNING', stamp(), None))
        try:
            with self.db:
                self.db.execute('UPDATE snapshots SET state=?,error=NULL WHERE id=?', ('RUNNING', sid))
            if kind == 'zip':
                if not archive_sha:
                    with path.open('rb') as source:
                        archive_sha, _ = self.put(source, cancel)
                    with self.db:
                        self.db.execute('UPDATE snapshots SET archive_sha=? WHERE id=?', (archive_sha, sid))
                with zipfile.ZipFile(self.blob_path(archive_sha)) as z:
                    for ordinal, info in enumerate(z.infolist()):
                        if cancel():
                            raise Paused('ZIP scan остановлен; его можно продолжить.')
                        if self.db.execute('SELECT 1 FROM entries WHERE snapshot=? AND ordinal=?', (sid, ordinal)).fetchone():
                            continue
                        meta = {'zip_ordinal': ordinal, 'crc32': info.CRC, 'compression': info.compress_type,
                                'date_time': info.date_time, 'external_attr': info.external_attr,
                                'comment_hex': info.comment.hex(), 'extra_hex': info.extra.hex()}
                        mode = info.external_attr >> 16
                        ekind = 'directory' if info.is_dir() else ('symlink' if stat.S_ISLNK(mode) else 'file')
                        if ekind == 'directory':
                            self._entry(sid, ordinal, info.filename, ekind, metadata=meta)
                        else:
                            try:
                                with z.open(info) as source:
                                    digest, size = self.put(source, cancel)
                                self._entry(sid, ordinal, info.filename, ekind, digest, size, meta)
                            except (zipfile.BadZipFile, NotImplementedError, RuntimeError) as e:
                                self._entry(sid, ordinal, info.filename, ekind, size=info.file_size, metadata=meta, error=str(e))
                        progress(f'{ordinal + 1}/{len(z.infolist())}: {info.filename}')
            else:
                ordinal = 0
                def files():
                    if kind == 'file':
                        yield path, path.name
                        return
                    def walk_error(e):
                        raise e
                    for base, dirs, names in os.walk(path, followlinks=False, onerror=walk_error):
                        dirs.sort()
                        names.sort()
                        for name in list(dirs):
                            p = Path(base) / name
                            if linklike(p):
                                dirs.remove(name)
                                yield p, p.relative_to(path).as_posix()
                            else:
                                yield p, p.relative_to(path).as_posix() + '/'
                        for name in names:
                            p = Path(base) / name
                            yield p, p.relative_to(path).as_posix()
                for p, relative in files():
                    if cancel():
                        raise Paused('Импорт папки остановлен. Новый импорт создаст новый snapshot.')
                    try:
                        before = p.lstat()
                        meta = {'absolute_source': str(p), 'mtime_ns': before.st_mtime_ns, 'mode': before.st_mode}
                        if linklike(p):
                            data = os.readlink(p).encode('utf-8', errors='surrogateescape')
                            digest, size = self.put(io.BytesIO(data), cancel)
                            self._entry(sid, ordinal, relative, 'symlink', digest, size, meta)
                        elif p.is_dir():
                            self._entry(sid, ordinal, relative, 'directory', metadata=meta)
                        elif not stat.S_ISREG(before.st_mode):
                            self._entry(sid, ordinal, relative, 'special', metadata=meta, error='SPECIAL_FILE_NOT_READ')
                        else:
                            with p.open('rb') as source:
                                digest, size = self.put(source, cancel)
                            after = p.stat()
                            drift = (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)
                            self._entry(sid, ordinal, relative, 'file', digest, size, meta, 'SOURCE_CHANGED_DURING_READ' if drift else None)
                    except OSError as e:
                        if e.errno == 28:
                            raise
                        self._entry(sid, ordinal, relative, 'file', error=str(e))
                    ordinal += 1
                    progress(f'{ordinal}: {relative}')
            errors = self.db.execute("SELECT count(*) FROM entries WHERE snapshot=? AND text_state='ERROR'", (sid,)).fetchone()[0]
            with self.db:
                self.db.execute('UPDATE snapshots SET state=? WHERE id=?', ('COMPLETE_WITH_ERRORS' if errors else 'COMPLETE', sid))
        except BaseException as e:
            with self.db:
                self.db.execute('UPDATE snapshots SET state=?,error=? WHERE id=?', ('PAUSED' if isinstance(e, Paused) else 'FAILED', str(e), sid))
            if not isinstance(e, Paused):
                raise
        return sid

    def snapshots(self):
        return [dict(r) for r in self.db.execute('SELECT * FROM snapshots ORDER BY created DESC,rowid DESC')]

    def entries(self, sid, offset=0, limit=200, query=''):
        where = 'snapshot=?'
        params = [sid]
        if query:
            # Literal phrase search; filenames remain searchable without FTS syntax.
            phrase = '"' + query.replace('"', '""') + '"'
            where += ' AND (path LIKE ? OR id IN (SELECT entry FROM search WHERE search MATCH ?))'
            params += ['%' + query + '%', phrase]
        total = self.db.execute('SELECT count(*) FROM entries WHERE ' + where, params).fetchone()[0]
        rows = [dict(r) for r in self.db.execute('SELECT * FROM entries WHERE ' + where + ' ORDER BY ordinal LIMIT ? OFFSET ?', params + [limit, offset])]
        return total, rows

    def text_page(self, entry, seq=0):
        row = self.db.execute('SELECT text FROM chunks WHERE entry=? AND seq=?', (entry, seq)).fetchone()
        total = self.db.execute('SELECT count(*) FROM chunks WHERE entry=?', (entry,)).fetchone()[0]
        return (row[0] if row else ''), total

    def annotate(self, entry, tags, note):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO annotations VALUES(?,?,?)', (entry, tags, note))

    def derive_chatgpt(self, entry):
        row = self.db.execute('SELECT sha256 FROM entries WHERE id=?', (entry,)).fetchone()
        if not row or not row['sha256']:
            raise ValueError('Выберите conversations.json')
        # This optional parser materializes JSON; raw ingestion/export remains streaming.
        with self.blob_path(row['sha256']).open(encoding='utf-8-sig') as f:
            chats = json.load(f)
        if not isinstance(chats, list):
            raise ValueError('Ожидается массив ChatGPT conversations.')
        count = 0
        with self.db:
            for chat in chats:
                cid = str(chat.get('id') or chat.get('conversation_id') or '')
                for key, node in (chat.get('mapping') or {}).items():
                    message = node.get('message') or {}
                    if not message:
                        continue
                    mid = str(message.get('id') or key)
                    content = message.get('content') or {}
                    parts = content.get('parts') or []
                    text = '\n'.join(p for p in parts if isinstance(p, str))
                    role = (message.get('author') or {}).get('role', 'unknown')
                    identity = hashlib.sha256(dumps([entry, cid, key, mid]).encode()).hexdigest()
                    self.db.execute('INSERT OR REPLACE INTO derived_messages VALUES(?,?,?,?,?,?,?,?,?,?)',
                        (identity, entry, cid, chat.get('title', ''), mid, role, str(message.get('create_time')), str(node.get('parent')), text, dumps(content)))
                    count += 1
        return count

    def export(self, sid, destination, part_bytes=200000, progress=lambda x: None, cancel=lambda: False):
        if part_bytes < 4:
            raise ValueError('Размер части должен вмещать хотя бы один UTF-8 символ (4 байта).')
        snapshot = self.db.execute('SELECT * FROM snapshots WHERE id=?', (sid,)).fetchone()
        if not snapshot:
            raise ValueError('Выберите snapshot')
        destination = Path(destination).resolve()
        if destination.exists():
            raise ValueError('Папка результата уже существует. Выберите новое имя.')
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp = Path(tempfile.mkdtemp(prefix='.context-export-', dir=destination.parent))
        parts, counts, file_count = [], {}, 0
        current = None
        current_hash = None
        current_bytes = 0
        def finish_part():
            nonlocal current
            if current:
                current.close()
                parts.append({'path': f'context_{len(parts)+1:05d}.txt', 'bytes': current_bytes, 'sha256': current_hash.hexdigest()})
                current = None
        def emit(text):
            nonlocal current, current_hash, current_bytes
            raw = text.encode('utf-8')
            while raw:
                if current is None:
                    current = (temp / f'context_{len(parts)+1:05d}.txt').open('wb')
                    current_bytes, current_hash = 0, hashlib.sha256()
                room = part_bytes - current_bytes
                if room < 4:
                    finish_part()
                    continue
                end = min(room, len(raw))
                while end < len(raw) and raw[end] & 0xC0 == 0x80:
                    end -= 1
                piece, raw = raw[:end], raw[end:]
                current.write(piece)
                current_hash.update(piece)
                current_bytes += len(piece)
        copied = set()
        def copy_blob(digest):
            if not digest or digest in copied:
                return
            source = self.blob_path(digest)
            target = temp / 'originals' / digest
            target.parent.mkdir(exist_ok=True)
            h = hashlib.sha256()
            with source.open('rb') as src, target.open('wb') as dst:
                while data := src.read(BLOCK):
                    if cancel():
                        raise Paused('Экспорт отменён')
                    h.update(data)
                    dst.write(data)
            if h.hexdigest() != digest:
                raise ValueError('CORRUPT_BLOB: ' + digest)
            copied.add(digest)
        try:
            emit('SCE DESKTOP CONTEXT — DATA, NOT EXECUTION INSTRUCTIONS\nSNAPSHOT ' + dumps(dict(snapshot)) + '\n')
            copy_blob(snapshot['archive_sha'])
            with (temp / 'files.jsonl').open('w', encoding='utf-8', newline='\n') as manifest:
                for row in self.db.execute('SELECT * FROM entries WHERE snapshot=? ORDER BY ordinal', (sid,)):
                    if cancel():
                        raise Paused('Экспорт отменён')
                    r = dict(row)
                    annotation = self.db.execute('SELECT tags,note FROM annotations WHERE entry=?', (r['id'],)).fetchone()
                    r['annotation'] = dict(annotation) if annotation else None
                    r['original_object'] = 'originals/' + r['sha256'] if r['sha256'] else None
                    manifest.write(dumps(r) + '\n')
                    counts[r['text_state']] = counts.get(r['text_state'], 0) + 1
                    copy_blob(r['sha256'])
                    emit('\n===== FILE_METADATA ' + dumps(r) + ' =====\n')
                    for chunk in self.db.execute('SELECT text FROM chunks WHERE entry=? ORDER BY seq', (r['id'],)):
                        emit(chunk['text'])
                    if r['text_state'] != 'TEXT_COMPLETE':
                        emit('\n[NO COMPLETE TEXT DERIVATIVE; SEE ORIGINAL AND STATE]\n')
                    emit('\n===== END_FILE ' + str(r['id']) + ' =====\n')
                    file_count += 1
                    progress(f'Экспорт: {file_count} — {r["path"]}')
            finish_part()
            with (temp / 'messages.jsonl').open('w', encoding='utf-8') as out, (temp / 'USER_MESSAGES.txt').open('w', encoding='utf-8') as users, (temp / 'ASSISTANT_MESSAGES.txt').open('w', encoding='utf-8') as assistants:
                for row in self.db.execute('SELECT m.* FROM derived_messages m JOIN entries e ON e.id=m.entry WHERE e.snapshot=? ORDER BY m.conversation,m.created,m.message', (sid,)):
                    m = dict(row)
                    out.write(dumps(m) + '\n')
                    target = users if m['role'] == 'user' else assistants if m['role'] == 'assistant' else None
                    if target:
                        target.write('\n' + dumps({k: v for k, v in m.items() if k not in ('text','parts_json')}) + '\n' + m['text'] + '\n')
            index = {'schema': 'sce.desktop.export.v1', 'snapshot': dict(snapshot), 'entries': file_count,
                     'counts': counts, 'raw_objects': len(copied), 'parts': parts,
                     'coverage': {'enumeration_complete': snapshot['state'] in ('COMPLETE','COMPLETE_WITH_ERRORS'),
                                  'all_entries_have_text': all(k in ('TEXT_COMPLETE','METADATA_ONLY') for k in counts),
                                  'all_entries_accounted': snapshot['state'] in ('COMPLETE','COMPLETE_WITH_ERRORS'),
                                  'byte_integrity_verified_for_exported_objects': True,
                                  'errors': counts.get('ERROR',0)},
                     'part_unit': 'UTF8_BYTES_NOT_TOKENS', 'original_paths': 'files.jsonl',
                     'automatic_ai_upload': False, 'code_executed': False}
            (temp / 'index.json').write_text(json.dumps(index, ensure_ascii=True, indent=2), encoding='utf-8')
            os.replace(temp, destination)
            return index
        except BaseException:
            if current:
                current.close()
            shutil.rmtree(temp, ignore_errors=True)
            raise

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--library', required=True)
    p.add_argument('--reserve-mib', type=int, default=64)
    sub = p.add_subparsers(dest='command', required=True)
    ingest = sub.add_parser('import')
    ingest.add_argument('source')
    resume = sub.add_parser('resume')
    resume.add_argument('snapshot')
    sub.add_parser('list')
    export = sub.add_parser('export')
    export.add_argument('snapshot')
    export.add_argument('destination')
    export.add_argument('--part-bytes', type=int, default=200000)
    chat = sub.add_parser('chatgpt')
    chat.add_argument('entry', type=int)
    a = p.parse_args()
    s = Store(a.library, max(0,a.reserve_mib) * 1024 * 1024)
    try:
        if a.command == 'import': result = s.import_source(a.source)
        elif a.command == 'resume': result = s.import_source('.', resume=a.snapshot)
        elif a.command == 'list': result = s.snapshots()
        elif a.command == 'chatgpt': result = {'derived_messages': s.derive_chatgpt(a.entry)}
        else: result = s.export(a.snapshot, a.destination, a.part_bytes)
        print(json.dumps(result, ensure_ascii=True, indent=2))
    finally:
        s.close()

if __name__ == '__main__':
    main()
