"""Bounded direct-Python transport. No database, executor or network client."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import threading
import time

PROTOCOL = 'occ.desktop-stdio.v1'
INPUT_BYTES = 16_000
OUTPUT_BYTES = 192_000
TIMEOUT_MS = 10_000
HASH = re.compile(r'^[0-9a-f]{64}$')
NAME = re.compile(r'^[A-Za-z0-9_.:-]{1,100}$')
READS = {
    'durable.info': ({'type'}, set()),
    'durable.repo.list': ({'type'}, set()),
    'durable.search': ({'type', 'namespace', 'query'}, {'limit'}),
    'durable.context': ({'type', 'namespace', 'ids'}, {'maxBytes'}),
    'durable.repo.manifest': ({'type', 'repository', 'snapshotId', 'action'},
                             {'offset', 'limit', 'fileOrdinal'}),
}
IDENTITY_KEYS = {'protocol', 'profile_digest', 'store_identity', 'adapter_sha256',
                 'backend_bundle_sha256'}


class DesktopError(ValueError):
    """A typed diagnostic, deliberately carrying no source text or raw stderr."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(condition, code='DESKTOP_SCHEMA'):
    if not condition:
        raise DesktopError(code)


def exact(value, keys):
    require(isinstance(value, dict) and set(value) == set(keys))


def number(value, low=0, high=9_007_199_254_740_991):
    require(type(value) is int and low <= value <= high)
    return value


def text_value(value):
    require(isinstance(value, str))
    # Escaped lone surrogates are legal JSON but cannot be transported as UTF8.
    try:
        value.encode('utf-8')
    except UnicodeError:
        raise DesktopError('DESKTOP_UTF8') from None
    return value


def hash_value(value, *, nullable=False):
    require(nullable and value is None or isinstance(value, str) and HASH.fullmatch(value))
    return value


def strict_json(raw):
    def pairs(values):
        out = {}
        for key, value in values:
            require(key not in out, 'DESKTOP_DUPLICATE_KEY')
            out[key] = value
        return out

    def finite(value):
        result = float(value)
        require(math.isfinite(result), 'DESKTOP_NONFINITE')
        return result

    def constant(_value):
        raise DesktopError('DESKTOP_NONFINITE')

    try:
        return json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=pairs,
                          parse_constant=constant, parse_float=finite)
    except DesktopError:
        raise
    except UnicodeError:
        raise DesktopError('DESKTOP_UTF8') from None
    except (ValueError, TypeError, RecursionError):
        raise DesktopError('DESKTOP_JSON') from None


def sha_file(path):
    hasher = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(65_536), b''):
            hasher.update(part)
    return hasher.hexdigest()


def is_link(path):
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) &
                                             getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400))


def regular_path(value, *, runtime=False):
    require(isinstance(value, str) and '\0' not in value and Path(value).is_absolute(),
            'DESKTOP_ABSOLUTE_PATH_REQUIRED')
    path = Path(value)
    try:
        # An operator-selected Python may use the OS's standard executable link.
        # Adapter/profile paths and their ancestors must be literal regular paths.
        if runtime:
            path = path.resolve(strict=True)
        else:
            require(not any(is_link(p) for p in (path, *path.parents)), 'DESKTOP_LINK_PATH')
        require(path.is_file(), 'DESKTOP_SETUP_REQUIRED')
    except OSError:
        raise DesktopError('DESKTOP_SETUP_REQUIRED') from None
    return str(path)


@dataclass(frozen=True)
class Connection:
    python_path: str
    adapter_path: str
    profile_path: str
    expected_adapter_sha256: str
    preferred_namespace: str | None = None

    @classmethod
    def from_dict(cls, value):
        exact(value, {'schema', 'python_path', 'adapter_path', 'profile_path',
                      'expected_adapter_sha256', 'preferred_namespace', 'protocol'})
        require(value['schema'] == 'occ.desktop-connection.v1' and value['protocol'] == PROTOCOL)
        preferred = value['preferred_namespace']
        require(preferred is None or isinstance(preferred, str) and NAME.fullmatch(preferred))
        return cls(regular_path(value['python_path'], runtime=True),
                   regular_path(value['adapter_path']), regular_path(value['profile_path']),
                   hash_value(value['expected_adapter_sha256']), preferred)

    @classmethod
    def load(cls, path):
        try:
            regular_path(str(Path(path).absolute()))
            with Path(path).open('rb') as stream:
                raw = stream.read(INPUT_BYTES + 1)
            require(len(raw) <= INPUT_BYTES, 'DESKTOP_INPUT_LIMIT')
            return cls.from_dict(strict_json(raw))
        except OSError:
            raise DesktopError('DESKTOP_SETUP_REQUIRED') from None

    def as_dict(self):
        return {'schema': 'occ.desktop-connection.v1', 'protocol': PROTOCOL,
                **self.__dict__}

    def verify(self):
        regular_path(self.python_path, runtime=True)
        regular_path(self.adapter_path)
        regular_path(self.profile_path)
        require(sha_file(self.adapter_path) == self.expected_adapter_sha256,
                'DESKTOP_ADAPTER_CHANGED')

    def argv(self):
        return [self.python_path, '-I', '-X', 'utf8', self.adapter_path,
                '--profile', self.profile_path, '--desktop-stdio']


def validate_request(request):
    require(isinstance(request, dict) and isinstance(request.get('type'), str))
    require(request['type'] in READS, 'DESKTOP_READ_ONLY')
    required, optional = READS[request['type']]
    require(required.issubset(request) and not set(request) - required - optional)
    for key in ('namespace', 'repository'):
        if key in request:
            require(isinstance(request[key], str) and NAME.fullmatch(request[key]))
    if request['type'] == 'durable.search':
        require(len(text_value(request['query'])) <= 1000)
        number(request.get('limit', 10), 1, 20)
    elif request['type'] == 'durable.context':
        ids = request['ids']
        require(isinstance(ids, list) and 1 <= len(ids) <= 10)
        for item_id in ids:
            hash_value(item_id)
        require(len(set(ids)) == len(ids))
        number(request.get('maxBytes', 48_000), 1, 48_000)
    elif request['type'] == 'durable.repo.manifest':
        hash_value(request['snapshotId'])
        require(isinstance(request['action'], str) and request['action'] in {'INFO', 'ENTRIES', 'PARTS'})
        if request['action'] == 'INFO':
            require(set(request) == required)
        number(request.get('offset', 0))
        number(request.get('limit', 20), 1, 20)
        if 'fileOrdinal' in request:
            require(request['action'] == 'PARTS')
            number(request['fileOrdinal'])
    return request


def validate_identity(value):
    exact(value, IDENTITY_KEYS)
    require(value['protocol'] == PROTOCOL, 'DESKTOP_PROTOCOL_UNAVAILABLE')
    for key in IDENTITY_KEYS - {'protocol'}:
        hash_value(value[key], nullable=key == 'backend_bundle_sha256')
    return value


def validate_info(value):
    exact(value, {'protocol', 'native_input_bytes', 'native_combined_output_bytes',
                  'native_timeout_ms', 'capabilities', 'namespaces', 'store_path',
                  'store_ready', 'backend_build_status', 'migration_performed'})
    require(value['protocol'] == PROTOCOL, 'DESKTOP_PROTOCOL_UNAVAILABLE')
    for key in ('native_input_bytes', 'native_combined_output_bytes', 'native_timeout_ms'):
        number(value[key], 1)
    capabilities = value['capabilities']
    require(isinstance(capabilities, list) and all(isinstance(v, str) and v in READS for v in capabilities))
    require(len(set(capabilities)) == len(capabilities) and 'durable.info' in capabilities)
    require(isinstance(value['namespaces'], list) and bool(value['namespaces']))
    require(all(isinstance(v, str) and NAME.fullmatch(v) for v in value['namespaces']))
    require(len(set(value['namespaces'])) == len(value['namespaces']))
    require(bool(text_value(value['store_path'])))
    require(type(value['store_ready']) is bool and value['migration_performed'] is False)
    require(value['backend_build_status'] == 'UNKNOWN_BUNDLE')


# Registered source DTO fields from the existing owner. Source metadata is data;
# accepting a field never makes it an executable instruction or output path.
ITEM_FIELDS = set(('schema schema_version id namespace source_key text input_sha256 '
    'input_file source_url text_sha256 kind extractor authority completeness '
    'asr_inference_performed network_fetch_performed created_at name revision '
    'parent_revision provenance file_sha256 path repo_sha logical_id byte_start '
    'byte_end start_line end_line oversized_fragment export_sha256 conversation_id '
    'conversation_title message_id node_id parent_node_id author_role content_type '
    'source_created_at revision_sha256 segments language model_files asr_settings '
    'elapsed_seconds duration_seconds media_sha256 warnings audio_seconds real_time_factor').split())


def validate_context(value, request):
    fields = {'schema', 'namespace', 'authority', 'items', 'bytes', 'sha256'}
    require(isinstance(value, dict) and fields.issubset(value)
            and not set(value) - fields - {'source_classifier_version'})
    if 'source_classifier_version' in value:
        require(value['source_classifier_version'] == 'utf8-controls-strict-lfs3.v1',
                'DESKTOP_CLASSIFIER_UNAVAILABLE')
    require(value['schema'] == 'occ.context-pack.v1' and value['namespace'] == request['namespace'])
    require(value['authority'] == 'source-content-not-action-instructions')
    items = value['items']
    require(isinstance(items, list) and len(items) == len(request['ids']))
    for item, expected in zip(items, request['ids']):
        require(isinstance(item, dict) and {'id', 'namespace', 'source_key', 'text', 'input_sha256'}.issubset(item))
        require(not set(item) - ITEM_FIELDS, 'DESKTOP_ITEM_SCHEMA_UNAVAILABLE')
        require(item['id'] == expected and item['namespace'] == request['namespace'], 'DESKTOP_CONTEXT_BINDING')
        hash_value(item['id'])
        hash_value(item['input_sha256'])
        text_value(item['source_key'])
        text_value(item['text'])
        if 'authority' in item:
            require(item['authority'] in {'DATA_ONLY', 'source-content-not-action-instructions'})
    size = sum(len(item['text'].encode('utf-8')) for item in items)
    require(number(value['bytes']) == size and size <= request.get('maxBytes', 48_000), 'DESKTOP_CONTEXT_BINDING')
    # Match automation_core.digest, including its default JSON separators.
    encoded = json.dumps(items, ensure_ascii=False, sort_keys=True, allow_nan=False).encode('utf-8')
    require(hash_value(value['sha256']) == hashlib.sha256(encoded).hexdigest(), 'DESKTOP_CONTEXT_DIGEST')


MANIFEST_FIELDS = set(('schema batch_id binding entry_count indexed_count gap_count part_count '
    'counts index_complete inventory_complete raw_exact_for_indexed text_exportable '
    'all_tracked_bytes_exportable global_validation ai_packet ai_packet_included '
    'ai_delivery ai_read dependencies authority execution_authorized scope rows offset '
    'total nextOffset proof_scope').split())
ENTRY_FIELDS = set(('schema snapshot_id ordinal path mode git_type git_oid size state reason '
    'file_sha256 parser chunk_count part_locator packet_coverage').split())
PART_FIELDS = set(('schema snapshot_id file_ordinal path chunk_ordinal part_id logical_id '
    'revision source_start source_end bytes sha256 file_sha256 text_eligible dependency_status').split())
BINDING_FIELDS = set(('schema snapshot_id namespace repository repo_sha tree_sha profile_revision '
    'goal_revision grouping_policy parser_policy historical_scanner_build export_policy').split())


def validate_manifest(value, request):
    exact(value, MANIFEST_FIELDS)
    require(value['schema'] == 'occ.repo-manifest-view.v1')
    hash_value(value['batch_id'])
    binding = value['binding']
    exact(binding, BINDING_FIELDS)
    require(binding['schema'] == 'occ.repo-manifest-binding.v1' and
            binding['snapshot_id'] == request['snapshotId'] and binding['repository'] == request['repository'])
    text_value(binding['namespace'])
    encoded = json.dumps(binding, ensure_ascii=False, sort_keys=True, allow_nan=False).encode('utf-8')
    require(value['batch_id'] == hashlib.sha256(encoded).hexdigest(), 'DESKTOP_MANIFEST_BINDING')
    exact(value['scope'], {'action', 'file_ordinal'})
    require(value['scope'] == {'action': request['action'], 'file_ordinal': request.get('fileOrdinal')})
    require(value['authority'] == 'DATA_ONLY' and value['execution_authorized'] is False)
    require(value['index_complete'] is True and value['inventory_complete'] is True)
    require(value['ai_packet_included'] is False and value['global_validation'] == 'NOT_RUN')
    for key in ('entry_count', 'indexed_count', 'gap_count', 'part_count', 'total', 'offset'):
        number(value[key])
    require(value['entry_count'] == value['indexed_count'] + value['gap_count'])
    require(isinstance(value['counts'], dict) and not set(value['counts']) - {'INDEXED', 'EXCLUDED', 'ERROR'})
    require(sum(number(n) for n in value['counts'].values()) == value['entry_count'])
    rows = value['rows']
    require(isinstance(rows, list) and len(rows) <= request.get('limit', 20))
    require(value['offset'] == request.get('offset', 0))
    if request['action'] == 'INFO':
        require(not rows and value['total'] == 0 and value['nextOffset'] is None)
        return
    count = len(rows)
    require(value['offset'] + count <= value['total'], 'DESKTOP_MANIFEST_CURSOR')
    expected_next = value['offset'] + count if value['offset'] + count < value['total'] else None
    require(value['nextOffset'] == expected_next and (expected_next is None or count > 0), 'DESKTOP_MANIFEST_CURSOR')
    if value['nextOffset'] is not None:
        number(value['nextOffset'])
    for index, row in enumerate(rows):
        exact(row, ENTRY_FIELDS if request['action'] == 'ENTRIES' else PART_FIELDS)
        require(row['snapshot_id'] == request['snapshotId'])
        text_value(row['path'])
        if request['action'] == 'ENTRIES':
            require(row['schema'] == 'occ.repo-entry-manifest.v1' and
                    number(row['ordinal']) == value['offset'] + index)
            number(row['chunk_count'])
            exact(row['part_locator'], {'file_ordinal'})
            require(row['part_locator']['file_ordinal'] == row['ordinal'])
        else:
            require(row['schema'] == 'occ.repo-part-index.v1')
            for key in ('file_ordinal', 'chunk_ordinal', 'source_start', 'source_end', 'bytes'):
                number(row[key])
            require(row['source_end'] - row['source_start'] == row['bytes'])
            for key in ('part_id', 'logical_id', 'revision', 'sha256', 'file_sha256'):
                hash_value(row[key])
            require(row['part_id'] == row['revision'] and type(row['text_eligible']) is bool)
            if 'fileOrdinal' in request:
                require(row['file_ordinal'] == request['fileOrdinal'])


def validate_reply(raw, request, adapter_sha, expected_identity=None):
    value = strict_json(raw)
    require(isinstance(value, dict) and type(value.get('ok')) is bool)
    exact(value, {'schema', 'ok', 'adapter_context', 'result' if value['ok'] else 'error'})
    require(value['schema'] == 'occ.desktop-stdio-result.v1', 'DESKTOP_PROTOCOL_UNAVAILABLE')
    context = value['adapter_context']
    if context is not None:
        validate_identity(context)
        require(context['adapter_sha256'] == adapter_sha, 'DESKTOP_ADAPTER_CHANGED')
        if expected_identity is not None:
            require(context == expected_identity, 'DESKTOP_PROFILE_CHANGED')
    if not value['ok']:
        code = value['error']
        require(isinstance(code, str) and re.fullmatch(r'[A-Z_]{1,100}', code))
        raise DesktopError(code)
    require(context is not None)
    result = value['result']
    operation = request['type']
    require(isinstance(result, dict) and result.get('schema') == 'occ.native-durable-result.v1'
            and result.get('operation') == operation, 'DESKTOP_OPERATION_MISMATCH')
    field = {'durable.info': 'info', 'durable.repo.list': 'repositories',
             'durable.search': 'items', 'durable.context': 'context',
             'durable.repo.manifest': 'manifest'}[operation]
    exact(result, {'schema', 'operation', field})
    if operation == 'durable.info':
        validate_info(result[field])
    elif operation == 'durable.context':
        validate_context(result[field], request)
    elif operation == 'durable.repo.manifest':
        validate_manifest(result[field], request)
    else:
        rows = result[field]
        require(isinstance(rows, list))
        if operation == 'durable.search':
            require(len(rows) <= request.get('limit', 10))
        seen = set()
        for row in rows:
            if operation == 'durable.repo.list':
                exact(row, {'repository', 'namespace'})
                require(all(isinstance(row[k], str) and NAME.fullmatch(row[k]) for k in row))
                identity = row['repository']
            else:
                exact(row, {'id', 'source_key', 'snippet'})
                identity = hash_value(row['id'])
                text_value(row['source_key'])
                text_value(row['snippet'])
            require(identity not in seen)
            seen.add(identity)
    return value


def environment():
    value = {'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}
    for key in ('PATH', 'SystemRoot', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'LANG', 'LC_ALL'):
        if key in os.environ:
            value[key] = os.environ[key]
    return value


class DesktopClient:
    def __init__(self, connection):
        self.connection = connection
        self.identity = None
        self.info = None
        self.last_stats = {}
        self._gate = threading.Lock()
        self._state = threading.Lock()
        self._cancel = None
        self._closed = False

    @property
    def busy(self):
        return self._gate.locked()

    def cancel(self):
        with self._state:
            if self._cancel is not None:
                self._cancel.set()

    def close(self):
        with self._state:
            self._closed = True
            if self._cancel is not None:
                self._cancel.set()

    def handshake(self):
        reply = self.request({'type': 'durable.info'})
        info = reply['result']['info']
        require(info['store_ready'], 'DESKTOP_SETUP_REQUIRED')
        require(self.connection.preferred_namespace is None or
                self.connection.preferred_namespace in info['namespaces'], 'DURABLE_NAMESPACE_OUTSIDE_SCOPE')
        return reply

    def request(self, request):
        validate_request(request)
        require(self._gate.acquire(blocking=False), 'DESKTOP_BUSY')
        try:
            with self._state:
                require(not self._closed, 'DESKTOP_CLOSED')
                cancel = self._cancel = threading.Event()
            self.connection.verify()
            operation = request['type']
            if operation == 'durable.info':
                self.identity = self.info = None
            if operation != 'durable.info':
                require(self.identity is not None and self.info is not None, 'DESKTOP_HANDSHAKE_REQUIRED')
                require(operation in self.info['capabilities'], 'DESKTOP_CAPABILITY_UNAVAILABLE')
                if 'namespace' in request:
                    require(request['namespace'] in self.info['namespaces'], 'DURABLE_NAMESPACE_OUTSIDE_SCOPE')
            raw = json.dumps(request, ensure_ascii=False, allow_nan=False).encode('utf-8')
            request = strict_json(raw)
            input_limit = min(INPUT_BYTES, self.info['native_input_bytes']) if self.info else INPUT_BYTES
            output_limit = min(OUTPUT_BYTES, self.info['native_combined_output_bytes']) if self.info else OUTPUT_BYTES
            timeout = min(TIMEOUT_MS, self.info['native_timeout_ms']) if self.info else TIMEOUT_MS
            require(len(raw) <= input_limit, 'DESKTOP_INPUT_LIMIT')
            reply = self._exchange(raw, cancel, output_limit, timeout)
            value = validate_reply(reply, request, self.connection.expected_adapter_sha256,
                                   self.identity if operation != 'durable.info' else None)
            if operation == 'durable.info' and value['result']['info']['store_ready']:
                info = value['result']['info']
                require(self.connection.preferred_namespace is None or
                        self.connection.preferred_namespace in info['namespaces'], 'DURABLE_NAMESPACE_OUTSIDE_SCOPE')
                self.identity, self.info = dict(value['adapter_context']), info
            return value
        except DesktopError as exc:
            if exc.code in {'DESKTOP_ADAPTER_CHANGED', 'DESKTOP_PROFILE_CHANGED', 'DESKTOP_SETUP_REQUIRED'}:
                self.identity = self.info = None
            raise
        except (OSError, UnicodeError):
            raise DesktopError('DESKTOP_SETUP_REQUIRED') from None
        finally:
            with self._state:
                self._cancel = None
            self._gate.release()

    def _exchange(self, raw, cancel, limit, timeout_ms):
        """Drain both pipes concurrently and retain at most a single frame."""
        start = time.monotonic()
        kwargs = {'shell': False, 'stdin': subprocess.PIPE, 'stdout': subprocess.PIPE,
                  'stderr': subprocess.PIPE, 'env': environment(), 'bufsize': 0,
                  'cwd': str(Path(self.connection.adapter_path).parent)}
        if os.name == 'nt':
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        else:
            kwargs['start_new_session'] = True
        child = subprocess.Popen(self.connection.argv(), **kwargs)
        lock, overflow, io_fault = threading.Lock(), threading.Event(), threading.Event()
        total, stdout, stderr = [0], bytearray(), bytearray()
        done = [threading.Event(), threading.Event(), threading.Event()]

        def drain(stream, target, diagnostic, completed):
            try:
                while True:
                    part = stream.read(4096)
                    if not part:
                        break
                    with lock:
                        total[0] += len(part)
                        if total[0] > limit:
                            overflow.set()
                            break
                        target.extend(part[:max(0, 4096 - len(target))] if diagnostic else part)
            except (OSError, ValueError):
                io_fault.set()
            finally:
                completed.set()

        def send():
            try:
                view = memoryview(raw)
                while view and not cancel.is_set():
                    written = child.stdin.write(view)
                    if not written:
                        raise OSError('closed input')
                    view = view[written:]
                child.stdin.close()
            except (OSError, ValueError):
                io_fault.set()
            finally:
                done[2].set()

        threads = [threading.Thread(target=drain, args=(child.stdout, stdout, False, done[0]), daemon=True),
                   threading.Thread(target=drain, args=(child.stderr, stderr, True, done[1]), daemon=True),
                   threading.Thread(target=send, daemon=True)]
        for thread in threads:
            thread.start()
        failure = None
        try:
            while True:
                if cancel.is_set():
                    failure = 'DESKTOP_CANCELLED'
                elif overflow.is_set():
                    failure = 'DESKTOP_OUTPUT_LIMIT'
                elif time.monotonic() - start >= timeout_ms / 1000:
                    failure = 'DESKTOP_TIMEOUT'
                elif child.poll() is not None and all(event.is_set() for event in done):
                    break
                if failure:
                    raise DesktopError(failure)
                cancel.wait(0.01)
            if child.returncode != 0:
                raise DesktopError('DESKTOP_PROTOCOL_UNAVAILABLE')
            require(not io_fault.is_set(), 'DESKTOP_PIPE_FAILED')
            return bytes(stdout)
        finally:
            # Only this isolated read adapter is owned here; it cannot start jobs.
            # On POSIX also close its process group if an unexpected child inherited
            # pipes. Windows read owners launch no descendants; device QA is separate.
            if os.name != 'nt':
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif child.poll() is None:
                child.kill()
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=2)
            for thread in threads:
                thread.join(timeout=1)
            for stream in (child.stdin, child.stdout, child.stderr):
                stream.close()
            self.last_stats = {'elapsed_ms': round((time.monotonic() - start) * 1000),
                               'combined_bytes': total[0], 'stderr_retained_bytes': len(stderr),
                               'exit_code': child.returncode, 'child_reaped': child.poll() is not None,
                               'pipes_closed': all(s.closed for s in (child.stdin, child.stdout, child.stderr)),
                               'io_threads_stopped': all(not t.is_alive() for t in threads)}

    def manifest_pages(self, repository, snapshot_id, action='ENTRIES', *, file_ordinal=None, cancel=None):
        """Real continuation to EOF; no total file/part cap and one page in RAM."""
        require(action in {'ENTRIES', 'PARTS'})
        offset, batch, total = 0, None, None
        while True:
            if cancel is not None and cancel.is_set():
                raise DesktopError('DESKTOP_CANCELLED')
            request = {'type': 'durable.repo.manifest', 'repository': repository,
                       'snapshotId': snapshot_id, 'action': action, 'offset': offset, 'limit': 20}
            if file_ordinal is not None:
                request['fileOrdinal'] = file_ordinal
            value = self.request(request)['result']['manifest']
            require(value['binding']['namespace'] in self.info['namespaces'])
            if batch is None:
                batch, total = value['batch_id'], value['total']
            require(value['batch_id'] == batch and value['total'] == total, 'DESKTOP_MANIFEST_BINDING')
            yield value
            if value['nextOffset'] is None:
                return
            offset = value['nextOffset']
