"""Bounded foreground parser subprocesses; repository input is never executable."""
import base64
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import struct
import subprocess
import threading
import time

from repo_artifacts import file_proof, safe_path

LAB = Path(__file__).resolve().parent
DEFAULT_BUDGET = {
    'schema': 'occ.repo-js-analysis-budget.v1', 'file_bytes': 8388608,
    'parser_input_frame_bytes': 12582912, 'parser_output_frame_bytes': 1048576,
    'stderr_total_bytes': 65536, 'stderr_retained_bytes': 8192,
    'file_timeout_seconds': 5, 'global_timeout_seconds': None,
    'cleanup_timeout_seconds': 2, 'node_old_space_mib': 256,
    'stage_max_bytes': None, 'projection_batch_rows': 256,
    'projection_batch_bytes': 262144, 'progress_interval_ms': 1000,
}
LIMITS = {'file_bytes': (1, 8388608), 'parser_input_frame_bytes': (1024, 33554432),
          'parser_output_frame_bytes': (1024, 8388608), 'stderr_total_bytes': (1024, 1048576),
          'stderr_retained_bytes': (0, 65536), 'file_timeout_seconds': (1, 60),
          'cleanup_timeout_seconds': (1, 5), 'node_old_space_mib': (64, 1024),
          'projection_batch_rows': (1, 1024), 'projection_batch_bytes': (65536, 1048576),
          'progress_interval_ms': (100, 1000)}


def stable_digest(value):
    # The JS dialect has its own compact canonical JSON contract. Existing
    # snapshot/chunk identity retains automation_core.digest byte for byte.
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf8')
    return hashlib.sha256(raw).hexdigest()


def budget(value=None):
    result = dict(DEFAULT_BUDGET)
    if value is not None:
        if not isinstance(value, dict) or set(value) - set(result):
            raise ValueError('ANALYSIS_BUDGET_SCHEMA')
        result.update(value)
    if result['schema'] != DEFAULT_BUDGET['schema']:
        raise ValueError('ANALYSIS_BUDGET_SCHEMA')
    for key, (minimum, maximum) in LIMITS.items():
        if type(result[key]) is not int or not minimum <= result[key] <= maximum:
            raise ValueError('ANALYSIS_BUDGET_SCHEMA')
    for key in ('global_timeout_seconds', 'stage_max_bytes'):
        if result[key] is not None and (type(result[key]) is not int or result[key] < 1):
            raise ValueError('ANALYSIS_BUDGET_SCHEMA')
    if result['stderr_retained_bytes'] > result['stderr_total_bytes']:
        raise ValueError('ANALYSIS_BUDGET_SCHEMA')
    return result


def rss(pid):
    """Observed working set, not a hard memory limit. No optional dependencies."""
    try:
        if os.name == 'posix':
            for line in Path(f'/proc/{pid}/status').read_text().splitlines():
                if line.startswith('VmRSS:'):
                    return int(line.split()[1]) * 1024
        elif os.name == 'nt':
            import ctypes
            from ctypes import wintypes
            class Counters(ctypes.Structure):
                _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
                    (key, ctypes.c_size_t) for key in ('PeakWorkingSetSize', 'WorkingSetSize',
                    'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                    'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.restype = wintypes.HANDLE
            kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
            kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
            psapi = ctypes.WinDLL('psapi', use_last_error=True)
            psapi.GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
            handle = kernel.OpenProcess(0x1000 | 0x10, False, pid)
            if handle:
                try:
                    value = Counters(); value.cb = ctypes.sizeof(value)
                    if psapi.GetProcessMemoryInfo(handle, ctypes.byref(value), value.cb):
                        return value.WorkingSetSize
                finally:
                    kernel.CloseHandle(handle)
    except (OSError, ValueError):
        pass
    return None


class Control:
    def __init__(self, limits, progress=lambda value: None):
        self.limits, self.progress = limits, progress
        self.started, self.last_progress = time.monotonic(), 0
        self.counts = {'processed_entries': 0, 'candidate_files': 0, 'relations': 0}
        self.reason, self.peak_rss, self.child_peak, self.rss_observed = None, 0, 0, False

    def pulse(self, child=None):
        parent_rss = rss(os.getpid())
        child_rss = rss(child.pid) if child is not None else 0
        if parent_rss is not None and child_rss is not None:
            self.peak_rss = max(self.peak_rss, parent_rss + child_rss)
            self.child_peak = max(self.child_peak, child_rss)
            self.rss_observed = True
        now = time.monotonic()
        if now - self.last_progress >= self.limits['progress_interval_ms'] / 1000:
            self.progress(dict(self.counts, state='ANALYZING'))
            self.last_progress = now
        if self.limits['global_timeout_seconds'] is not None and now - self.started >= self.limits['global_timeout_seconds']:
            self.reason = 'GLOBAL_TIME_BUDGET'
            raise ValueError(self.reason)


def parser_pin():
    pin = json.loads(safe_path(LAB / 'js-parser/PIN.json').read_text('utf8'))
    if pin.get('name') != '@babel/parser' or pin.get('version') != '7.28.5' or pin.get('runtime_dependencies') != []:
        raise ValueError('PARSER_PIN_MISMATCH')
    expected = {'babel-parser.cjs': '4fad5d076afb8c346159a06bb942d6e14c6167d590082b7c3bdebd4c108af201',
                'LICENSE': '2e97627cb278aa7556fb9e8817368302301a595b6c7582512b8d74c57b773652',
                'package.json': '06e89556fea2851b071797c63c0565725ba8b889014a07ac6ad62dbde52157de'}
    if set(pin.get('files', {})) != set(expected):
        raise ValueError('PARSER_PIN_MISMATCH')
    for name, sha256 in expected.items():
        proof = file_proof(LAB / 'js-parser' / name)
        if proof != pin['files'][name] or proof['sha256'] != sha256:
            raise ValueError('PARSER_PIN_MISMATCH')
    return pin


def parser_environment():
    return {key: value for key, value in os.environ.items()
            if key in {'PATH', 'SystemRoot', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP'}}


def node_path():
    executable = shutil.which('node')
    if executable is None:
        raise ValueError('TRUSTED_NODE_UNAVAILABLE')
    # Node installations commonly use symlinks; pin the resolved executable.
    return str(Path(executable).resolve())


def interpretation(limits, legacy=False):
    pin = parser_pin()
    node = node_path()
    result = subprocess.run([node, '--version'], cwd=LAB, env=parser_environment(),
                            capture_output=True, timeout=5, check=True)
    node_version = result.stdout.decode('ascii').strip()
    if len(node_version) > 40 or not node_version.startswith('v'):
        raise ValueError('TRUSTED_NODE_VERSION')
    options = {'sourceType': 'unambiguous', 'errorRecovery': False, 'attachComment': False,
               'createImportExpressions': True, 'typescript_dts': False,
               'jsx_extensions': ['.jsx', '.tsx'], 'mts_cts_disallow_ambiguous_jsx': True,
               'file_budget': limits}
    return {'schema': 'occ.repo-js-interpretation.v1', 'parser_id': pin['name'],
            'parser_version': pin['version'], 'parser_artifact_sha256': pin['tarball_sha256'],
            'parser_runtime_sha256': pin['files']['babel-parser.cjs']['sha256'],
            'license_sha256': pin['files']['LICENSE']['sha256'],
            'pin_sha256': file_proof(LAB / 'js-parser/PIN.json')['sha256'],
            'helper_sha256': file_proof(LAB / 'repo_js_parser.cjs')['sha256'],
            'adapter_sha256': file_proof(LAB / 'repo_js.py')['sha256'],
            'input_adapter_sha256': file_proof(LAB / 'repo_js_input.py')['sha256'],
            'runtime_adapter_sha256': file_proof(LAB / 'repo_js_runtime.py')['sha256'],
            'adapter_version': 'JS_TS_AST_CAPTURE_V1', 'resolver_version': 'RELATIVE_SOURCE_EXACT_V1',
            'options': options, 'options_digest': stable_digest(options),
            'eligibility_policy_version': 'LEGACY_CAPTURE_GUARD_UNVERIFIED_PR005' if legacy else 'utf8-controls-strict-lfs3.v1',
            'eligibility_schema_sha256': file_proof(LAB / 'js-contracts/ELIGIBILITY.schema.json')['sha256'],
            'output_schema_hashes': {name: file_proof(LAB / 'js-contracts' / name)['sha256']
                                     for name in ('JS_ANALYSIS.schema.json', 'RELATION.schema.json')},
            'symbol_identity': 'PATH_KIND_NAME_OCCURRENCE; anonymous semantic binding unknown',
            'node_version': node_version, 'node_executable_sha256': file_proof(node)['sha256'],
            'node_heap_is_rss_limit': False, 'source_execution': False,
            'symbol_binding': 'NOT_TYPECHECKED', 'group_consumer': 'NOT_INTEGRATED_PR006_PYTHON_ONLY'}


def parse_file(raw, extension, control):
    limits = control.limits
    failure = lambda reason: {'status': 'PARSER_FAILED', 'reason': reason, 'refs': [], 'symbols': []}
    payload = json.dumps({'raw_base64': base64.b64encode(raw).decode('ascii'), 'extension': extension},
                         separators=(',', ':')).encode('ascii')
    if len(payload) > limits['parser_input_frame_bytes']:
        return failure('PARSER_INPUT_BUDGET')
    events = queue.Queue(maxsize=2)
    stopped = threading.Event()
    child = subprocess.Popen([node_path(), f"--max-old-space-size={limits['node_old_space_mib']}",
                              str(LAB / 'repo_js_parser.cjs'), str(limits['parser_input_frame_bytes']),
                              str(limits['parser_output_frame_bytes'])], cwd=LAB, env=parser_environment(),
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
                             creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    def enqueue(event):
        while not stopped.is_set():
            try:
                events.put(event, timeout=.05)
                return
            except queue.Full:
                pass
    def reader(name, stream):
        try:
            while chunk := stream.read1(65536):
                enqueue((name, chunk))
            enqueue((name, None))
        finally:
            stream.close()
    def writer():
        try:
            child.stdin.write(struct.pack('<I', len(payload)) + payload)
            child.stdin.flush()
        except (OSError, ValueError):
            pass
        finally:
            child.stdin.close()
    threads = [threading.Thread(target=reader, args=(name, stream), daemon=True)
               for name, stream in (('out', child.stdout), ('err', child.stderr))]
    threads.append(threading.Thread(target=writer, daemon=True))
    for thread in threads:
        thread.start()
    output, errors, error_bytes, ended = bytearray(), bytearray(), 0, set()
    started = time.monotonic()
    reason = None
    try:
        while len(ended) < 2:
            control.pulse(child)
            if time.monotonic() - started >= limits['file_timeout_seconds']:
                reason = 'PARSER_TIMEOUT'; break
            try:
                name, chunk = events.get(timeout=.05)
            except queue.Empty:
                continue
            if chunk is None:
                ended.add(name); continue
            if name == 'out':
                if len(output) + len(chunk) > limits['parser_output_frame_bytes'] + 4:
                    reason = 'PARSER_OUTPUT_BUDGET'; break
                output.extend(chunk)
                if len(output) >= 4 and struct.unpack('<I', output[:4])[0] > limits['parser_output_frame_bytes']:
                    reason = 'PARSER_OUTPUT_BUDGET'; break
            else:
                error_bytes += len(chunk)
                errors.extend(chunk[:max(0, limits['stderr_retained_bytes'] - len(errors))])
                if error_bytes > limits['stderr_total_bytes']:
                    reason = 'PARSER_STDERR_BUDGET'; break
        if reason:
            return failure(reason)
        try:
            code = child.wait(timeout=limits['cleanup_timeout_seconds'])
        except subprocess.TimeoutExpired:
            return failure('PARSER_TIMEOUT')
        if code or len(output) < 4 or struct.unpack('<I', output[:4])[0] != len(output) - 4:
            return failure('PARSER_PROCESS_FAILED')
        try:
            parsed = json.loads(output[4:])
        except (ValueError, UnicodeDecodeError):
            return failure('PARSER_PROTOCOL_INVALID')
        if (not isinstance(parsed, dict) or parsed.get('parser_version') != '7.28.5'
                or parsed.get('status') not in {'AST_SYNTAX_ONLY', 'PARSER_FAILED'}
                or not isinstance(parsed.get('refs'), list) or not isinstance(parsed.get('symbols'), list)
                or type(parsed.get('peak_rss_bytes')) is not int or parsed['peak_rss_bytes'] < 0
                or parsed['status'] == 'PARSER_FAILED' and (parsed['refs'] or parsed['symbols'])):
            return failure('PARSER_PROTOCOL_INVALID')
        control.child_peak = max(control.child_peak, parsed['peak_rss_bytes'])
        parent = rss(os.getpid())
        if parent is not None:
            control.peak_rss = max(control.peak_rss, parent + parsed['peak_rss_bytes'])
        return parsed
    finally:
        stopped.set()
        cleanup_deadline = time.monotonic() + limits['cleanup_timeout_seconds']
        if child.poll() is None:
            child.kill()
        child.wait(timeout=max(.01, cleanup_deadline - time.monotonic()))
        for thread in threads:
            thread.join(timeout=max(0, cleanup_deadline - time.monotonic()))
        if any(thread.is_alive() for thread in threads):
            raise ValueError('PARSER_CLEANUP_FAILED')
