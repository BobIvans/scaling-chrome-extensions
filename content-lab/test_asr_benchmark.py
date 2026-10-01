import json
from pathlib import Path
import tempfile
import unittest

import asr_benchmark as bench
import content_lab as lab


class ASRBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.model = self.root / "model"
        self.model.mkdir()
        for name in lab.MODEL_FILES:
            (self.model / name).write_bytes(b"local fixture")

    def tearDown(self):
        self.temp.cleanup()

    def suite(self, cases, consent=None):
        for case in cases:
            (self.root / case["audio_file"]).write_bytes(b"RIFF synthetic owned audio")
        path = self.root / "suite.json"
        path.write_text(
            json.dumps(
                {
                    "schema": bench.SUITE_SCHEMA,
                    "consent": consent
                    or {"owned_or_licensed": True, "benchmark_use_authorized": True},
                    "cases": cases,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return path

    def case(self, identifier="ru-1", language="ru", reference="сравнить документы", action="ANALYZE_SELECTED_CONTEXT"):
        return {
            "id": identifier,
            "language": language,
            "audio_file": f"{identifier}.wav",
            "reference_transcript": reference,
            "expected_action": action,
            "accepted_action_transcripts": [reference] if action else [],
        }

    def test_unicode_word_error_rate_is_deterministic(self):
        self.assertEqual(
            bench.score_transcript("Pārbaudīt 42 darījumus", "pārbaudīt darījumus"),
            {"reference_words": 3, "hypothesis_words": 2, "word_errors": 1, "wer_milli": 333},
        )

    def test_suite_requires_explicit_consent_and_bounded_ru_lv_files(self):
        case = self.case()
        with self.assertRaisesRegex(ValueError, "ASR_CONSENT_REQUIRED"):
            bench.load_suite(self.suite([case], {"owned_or_licensed": True, "benchmark_use_authorized": False}))
        case = self.case(language="en")
        with self.assertRaisesRegex(ValueError, "ASR_CASE_LANGUAGE"):
            bench.load_suite(self.suite([case]))
        case = self.case()
        case["audio_file"] = "../outside.wav"
        with self.assertRaisesRegex(ValueError, "ASR_CASE_AUDIO_PATH"):
            bench.load_suite(self.suite([case]))

    def test_duplicate_keys_ids_and_action_alias_drift_fail_closed(self):
        path = self.root / "duplicate.json"
        path.write_text('{"schema":"a","schema":"b"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "ASR_SUITE_DUPLICATE_KEY"):
            bench.load_suite(path)
        case = self.case()
        with self.assertRaisesRegex(ValueError, "ASR_CASE_DUPLICATE"):
            bench.load_suite(self.suite([case, dict(case)]))
        case = self.case()
        case["accepted_action_transcripts"] = ["другая фраза"]
        with self.assertRaisesRegex(ValueError, "ASR_CASE_ACTION_TRANSCRIPTS"):
            bench.load_suite(self.suite([case]))

    def test_ru_lv_report_has_wer_action_p95_ram_without_transcript_text(self):
        cases = [
            self.case(),
            self.case("lv-1", "lv", "veidot darba failus", "BUILD_JOB_ARTIFACTS"),
        ]
        hypotheses = iter(["Сравнить документы", "veidot failus"])
        model_files = {name: lab._digest_file(self.model / name) for name in lab.MODEL_FILES}

        def fake(path, model_dir, *, language, threads):
            self.assertEqual(model_dir, self.model)
            self.assertEqual(threads, 2)
            return {
                "text": next(hypotheses),
                "language": language,
                "asr_inference_performed": True,
                "input_sha256": lab._digest_file(path),
                "model_files": model_files,
            }

        rss = iter([100, 150, 200, 180])
        report = bench.run_benchmark(
            self.suite(cases),
            self.model,
            threads=2,
            transcriber=fake,
            rss_reader=lambda: next(rss),
            sample_interval_seconds=1,
        )
        self.assertEqual(report["wer_milli"], 200)
        self.assertEqual(report["action_accuracy_milli"], 500)
        self.assertIsInstance(report["latency_p95_ms"], int)
        self.assertEqual(report["sampled_peak_process_rss_bytes"], 200)
        self.assertEqual(report["model_files"], model_files)
        self.assertFalse(report["action_authority"])
        self.assertFalse(report["dispatch_allowed"])
        encoded = json.dumps(report, ensure_ascii=False)
        for private in ["Сравнить документы", "veidot failus", "veidot darba failus"]:
            self.assertNotIn(private.casefold(), encoded.casefold())

    def test_unknown_action_and_unsupported_rss_remain_null(self):
        case = self.case(action=None)
        model_files = {name: lab._digest_file(self.model / name) for name in lab.MODEL_FILES}

        def fake(path, _model, **_kwargs):
            return {
                "text": "сравнить документы",
                "language": "ru",
                "asr_inference_performed": True,
                "input_sha256": lab._digest_file(path),
                "model_files": model_files,
            }

        report = bench.run_benchmark(
            self.suite([case]),
            self.model,
            transcriber=fake,
            rss_reader=lambda: None,
            sample_interval_seconds=1,
        )
        self.assertIsNone(report["action_accuracy_milli"])
        self.assertIsNone(report["sampled_peak_process_rss_bytes"])
        self.assertEqual(
            report["unknown_measurements"],
            ["action_accuracy_milli", "sampled_peak_process_rss_bytes"],
        )

    def test_backend_without_inference_receipt_cannot_claim_measurement(self):
        with self.assertRaisesRegex(ValueError, "ASR_BACKEND_RECEIPT"):
            bench.run_benchmark(
                self.suite([self.case()]),
                self.model,
                transcriber=lambda *_args, **_kwargs: {"text": "сравнить документы"},
                rss_reader=lambda: None,
                sample_interval_seconds=1,
            )

    def test_report_write_is_atomic_and_module_has_no_network_or_dispatch(self):
        report = {"schema": bench.REPORT_SCHEMA, "unknown_measurements": ["all"]}
        output = self.root / "reports" / "result.json"
        bench.write_report(output, report)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), report)
        source = Path(bench.__file__).read_text(encoding="utf-8")
        for forbidden in ["requests", "urllib", "socket", "subprocess", "os.system", "shell=True", "dispatch("]:
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
