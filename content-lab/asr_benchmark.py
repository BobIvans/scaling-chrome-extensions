"""Consent-bound local RU/LV ASR benchmark; never downloads or executes actions."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import threading
import time
import unicodedata

import content_lab as lab

SUITE_SCHEMA = "occ.asr-benchmark-suite.v1"
REPORT_SCHEMA = "occ.asr-benchmark-report.v1"
MAX_SUITE_BYTES = 256 * 1024
MAX_CASES = 100
MAX_TRANSCRIPT_BYTES = 16_000
CASE_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,100}$")
LANGUAGES = {"ru", "lv"}
ACTIONS = {
    "ANALYZE_SELECTED_CONTEXT",
    "BUILD_JOB_ARTIFACTS",
    "REVIEW_REGISTERED_ACTION",
}


def _fail(code: str) -> None:
    raise ValueError(code)


def _exact(value, keys: set[str], code: str) -> None:
    if not isinstance(value, dict):
        _fail(f"{code}_TYPE")
    if set(value) != keys:
        _fail(f"{code}_SHAPE")


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            _fail("ASR_SUITE_DUPLICATE_KEY")
        value[key] = item
    return value


def _reject_constant(_value):
    _fail("ASR_SUITE_NONFINITE")


def _canonical_text(value: str) -> str:
    if not isinstance(value, str) or "\0" in value:
        _fail("ASR_TRANSCRIPT_TYPE")
    text = " ".join(unicodedata.normalize("NFKC", value).strip().split())
    if not text or len(text.encode("utf-8")) > MAX_TRANSCRIPT_BYTES:
        _fail("ASR_TRANSCRIPT_LIMIT")
    return text.casefold()


def _words(value: str) -> list[str]:
    return re.findall(r"[^\W_]+(?:['’-][^\W_]+)*|\d+", _canonical_text(value), re.UNICODE)


def _word_errors(reference: list[str], hypothesis: list[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for row, expected in enumerate(reference, 1):
        current = [row]
        for column, actual in enumerate(hypothesis, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (expected != actual),
                )
            )
        previous = current
    return previous[-1]


def score_transcript(reference: str, hypothesis: str) -> dict:
    expected, actual = _words(reference), _words(hypothesis)
    if not expected:
        _fail("ASR_REFERENCE_WORDS")
    errors = _word_errors(expected, actual)
    return {
        "reference_words": len(expected),
        "hypothesis_words": len(actual),
        "word_errors": errors,
        "wer_milli": round(errors * 1000 / len(expected)),
    }


def _read_suite(path: Path) -> tuple[dict, bytes]:
    if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".json":
        _fail("ASR_SUITE_FILE")
    before = path.stat()
    with path.open("rb") as handle:
        raw = handle.read(MAX_SUITE_BYTES + 1)
    after = path.stat()
    if path.is_symlink() or (before.st_size, before.st_mtime_ns) != (
        after.st_size,
        after.st_mtime_ns,
    ):
        _fail("ASR_SUITE_CHANGED")
    if not raw or len(raw) > MAX_SUITE_BYTES:
        _fail("ASR_SUITE_SIZE")
    try:
        value = json.loads(
            raw.decode("utf-8-sig"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("ASR_SUITE_JSON") from exc
    return value, raw


def load_suite(path: Path) -> dict:
    value, raw = _read_suite(path)
    _exact(value, {"schema", "consent", "cases"}, "ASR_SUITE")
    if value["schema"] != SUITE_SCHEMA:
        _fail("ASR_SUITE_SCHEMA")
    _exact(
        value["consent"],
        {"owned_or_licensed", "benchmark_use_authorized"},
        "ASR_CONSENT",
    )
    if value["consent"]["owned_or_licensed"] is not True or value["consent"][
        "benchmark_use_authorized"
    ] is not True:
        _fail("ASR_CONSENT_REQUIRED")
    if not isinstance(value["cases"], list) or not 1 <= len(value["cases"]) <= MAX_CASES:
        _fail("ASR_CASE_COUNT")
    root = path.resolve().parent
    seen = set()
    cases = []
    keys = {
        "id",
        "language",
        "audio_file",
        "reference_transcript",
        "expected_action",
        "accepted_action_transcripts",
    }
    for source in value["cases"]:
        _exact(source, keys, "ASR_CASE")
        if not isinstance(source["id"], str) or not CASE_ID.fullmatch(source["id"]):
            _fail("ASR_CASE_ID")
        if source["id"] in seen:
            _fail("ASR_CASE_DUPLICATE")
        seen.add(source["id"])
        if source["language"] not in LANGUAGES:
            _fail("ASR_CASE_LANGUAGE")
        if not isinstance(source["audio_file"], str) or not source["audio_file"]:
            _fail("ASR_CASE_AUDIO_PATH")
        relative = Path(source["audio_file"])
        if relative.is_absolute() or ".." in relative.parts:
            _fail("ASR_CASE_AUDIO_PATH")
        audio = (root / relative).resolve()
        if not audio.is_relative_to(root) or audio.is_symlink() or not audio.is_file():
            _fail("ASR_CASE_AUDIO_FILE")
        audio_before = audio.stat()
        audio_sha256 = lab._digest_file(audio)
        audio_after = audio.stat()
        if (audio_before.st_size, audio_before.st_mtime_ns) != (
            audio_after.st_size,
            audio_after.st_mtime_ns,
        ):
            _fail("ASR_CASE_AUDIO_CHANGED")
        if audio_after.st_size > lab.MAX_AUDIO_BYTES:
            _fail("ASR_CASE_AUDIO_SIZE")
        reference = _canonical_text(source["reference_transcript"])
        if not _words(reference):
            _fail("ASR_REFERENCE_WORDS")
        action = source["expected_action"]
        accepted = source["accepted_action_transcripts"]
        if action is None:
            if accepted != []:
                _fail("ASR_CASE_ACTION_UNKNOWN")
        else:
            if action not in ACTIONS or not isinstance(accepted, list) or not 1 <= len(accepted) <= 20:
                _fail("ASR_CASE_ACTION")
            canonical = [_canonical_text(item) for item in accepted]
            if len(set(canonical)) != len(canonical) or reference not in canonical:
                _fail("ASR_CASE_ACTION_TRANSCRIPTS")
            accepted = canonical
        cases.append(
            {
                "id": source["id"],
                "language": source["language"],
                "audio": audio,
                "audio_sha256": audio_sha256,
                "reference": reference,
                "expected_action": action,
                "accepted": accepted,
            }
        )
    return {
        "schema": SUITE_SCHEMA,
        "suite_sha256": hashlib.sha256(raw).hexdigest(),
        "root": root,
        "cases": cases,
    }


def process_rss_bytes() -> int | None:
    try:
        if sys.platform.startswith("linux"):
            for line in Path("/proc/self/status").read_text(encoding="ascii").splitlines():
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) * 1024
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            class Counters(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = Counters()
            counters.cb = ctypes.sizeof(counters)
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                return int(counters.WorkingSetSize)
    except (OSError, ValueError, AttributeError):
        return None
    return None


def _measure(call, rss_reader, interval: float) -> tuple[object, float, int | None]:
    stop = threading.Event()
    samples = [value for value in [rss_reader()] if isinstance(value, int) and value >= 0]

    def sample():
        while not stop.wait(interval):
            value = rss_reader()
            if isinstance(value, int) and value >= 0:
                samples.append(value)

    monitor = threading.Thread(target=sample, name="occ-asr-rss", daemon=True)
    started = time.perf_counter()
    monitor.start()
    try:
        result = call()
    finally:
        elapsed = time.perf_counter() - started
        stop.set()
        monitor.join(timeout=max(0.1, interval * 2))
        value = rss_reader()
        if isinstance(value, int) and value >= 0:
            samples.append(value)
    return result, elapsed, max(samples) if samples else None


def _percentile95(values: list[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]


def run_benchmark(
    suite_path: Path,
    model_dir: Path,
    *,
    threads: int = 4,
    transcriber=None,
    rss_reader=process_rss_bytes,
    sample_interval_seconds: float = 0.01,
) -> dict:
    suite = load_suite(suite_path)
    if not 1 <= threads <= 8 or not 0.001 <= sample_interval_seconds <= 1:
        _fail("ASR_BENCHMARK_LIMIT")
    transcriber = transcriber or lab.transcribe_file
    results, total_errors, total_words, latencies, rss_values = [], 0, 0, [], []
    model_files = None
    action_correct = action_cases = 0
    for case in suite["cases"]:
        item, elapsed, sampled_rss = _measure(
            lambda case=case: transcriber(
                case["audio"], model_dir, language=case["language"], threads=threads
            ),
            rss_reader,
            sample_interval_seconds,
        )
        if not isinstance(item, dict) or item.get("asr_inference_performed") is not True:
            _fail("ASR_BACKEND_RECEIPT")
        if item.get("input_sha256") != case["audio_sha256"]:
            _fail("ASR_BACKEND_AUDIO_BINDING")
        binding = item.get("model_files")
        if not isinstance(binding, dict) or set(binding) != set(lab.MODEL_FILES) or any(
            not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
            for value in binding.values()
        ):
            _fail("ASR_BACKEND_MODEL_BINDING")
        if model_files is None:
            model_files = binding
        elif model_files != binding:
            _fail("ASR_BACKEND_MODEL_CHANGED")
        hypothesis = item.get("text")
        scores = score_transcript(case["reference"], hypothesis)
        elapsed_ms = max(0, round(elapsed * 1000))
        latencies.append(elapsed_ms)
        total_errors += scores["word_errors"]
        total_words += scores["reference_words"]
        if sampled_rss is not None:
            rss_values.append(sampled_rss)
        predicted_action = None
        action_ok = None
        if case["expected_action"] is not None:
            action_cases += 1
            action_ok = _canonical_text(hypothesis) in case["accepted"]
            action_correct += int(action_ok)
            predicted_action = case["expected_action"] if action_ok else "UNMATCHED"
        results.append(
            {
                "id": case["id"],
                "language": case["language"],
                "detected_language": item.get("language"),
                "audio_sha256": case["audio_sha256"],
                "reference_sha256": hashlib.sha256(case["reference"].encode()).hexdigest(),
                "hypothesis_sha256": hashlib.sha256(_canonical_text(hypothesis).encode()).hexdigest(),
                **scores,
                "elapsed_ms": elapsed_ms,
                "sampled_peak_process_rss_bytes": sampled_rss,
                "expected_action": case["expected_action"],
                "predicted_action": predicted_action,
                "action_correct": action_ok,
            }
        )
    unknown = []
    action_accuracy = round(action_correct * 1000 / action_cases) if action_cases else None
    peak_rss = max(rss_values) if rss_values else None
    if action_accuracy is None:
        unknown.append("action_accuracy_milli")
    if peak_rss is None:
        unknown.append("sampled_peak_process_rss_bytes")
    return {
        "schema": REPORT_SCHEMA,
        "state": "MEASURED",
        "suite_sha256": suite["suite_sha256"],
        "model_files": model_files,
        "case_count": len(results),
        "languages": sorted({case["language"] for case in suite["cases"]}),
        "wer_milli": round(total_errors * 1000 / total_words),
        "action_accuracy_milli": action_accuracy,
        "latency_p95_ms": _percentile95(latencies),
        "sampled_peak_process_rss_bytes": peak_rss,
        "unknown_measurements": unknown,
        "cases": results,
        "privacy": "transcript_text_omitted; hashes_and_metrics_only",
        "owned_or_licensed_audio_asserted": True,
        "benchmark_use_authorized": True,
        "provider_api_spend": 0,
        "network_fetches": 0,
        "model_downloads": 0,
        "action_authority": False,
        "dispatch_allowed": False,
    }


def write_report(path: Path, report: dict) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        _fail("ASR_REPORT_PATH")
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".asr-report-", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", required=True, type=Path)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args(argv)
    try:
        report = run_benchmark(args.suite, args.model_dir, threads=args.threads)
        write_report(args.output, report)
        print(json.dumps({"state": "MEASURED", "report_sha256": lab._digest_file(args.output)}))
        return 0
    except (OSError, ValueError, ImportError, RuntimeError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason_code": "ASR_BENCHMARK_INPUT_OR_BACKEND_ERROR", "error_type": type(exc).__name__}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
