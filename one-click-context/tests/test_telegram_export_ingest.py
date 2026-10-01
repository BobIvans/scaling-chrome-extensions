"""Offline synthetic tests; actual acoustic quality needs separate qualification."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / "tools" / "telegram_export_ingest.py"
SPEC = importlib.util.spec_from_file_location("telegram_ingest", PATH)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def chat(text="Не включать live", chat_id=1):
    return {"id": chat_id, "messages": [{"id": 1, "date": "2026-10-01", "text": text}]}


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_export(self, data, **kwargs):
        return mod.normalize_export(data, self.root, authorized=True, **kwargs)

    def test_authorization_required(self):
        with self.assertRaises(PermissionError):
            mod.normalize_export(chat(), self.root)

    def test_rich_text_is_preserved(self):
        result = self.run_export(chat(["Тест ", {"type": "bold", "text": "Solana"}, "\n✅"]))
        self.assertEqual(result[0]["text"], "Тест Solana\n✅")
        self.assertEqual(result[0]["authority"], "UNTRUSTED_DATA")

    def test_unsupported_entity_fails(self):
        with self.assertRaises(ValueError):
            self.run_export(chat([{"unexpected": "text"}]))

    def test_cross_chat_message_ids_are_distinct(self):
        result = self.run_export({"chats": {"list": [chat(chat_id=1), chat(chat_id=2)]}})
        self.assertEqual(len({r["source_id"] for r in result}), 2)

    def test_duplicate_record_is_deduplicated(self):
        data = chat()
        data["messages"] *= 2
        self.assertEqual(len(self.run_export(data)), 1)

    def test_edits_preserve_versions(self):
        data = chat()
        edited = copy.deepcopy(data["messages"][0])
        edited["text"] = "Новый план"
        data["messages"].append(edited)
        result = self.run_export(data)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["source_id"], result[1]["source_id"])
        self.assertNotEqual(result[0]["record_sha256"], result[1]["record_sha256"])

    def test_repeat_is_deterministic_and_does_not_mutate_input(self):
        data = chat()
        before = copy.deepcopy(data)
        self.assertEqual(self.run_export(data), self.run_export(data))
        self.assertEqual(data, before)

    def voice(self, file="voice.ogg"):
        data = chat("")
        data["messages"][0].update(media_type="voice_message", file=file)
        return data

    def test_voice_without_model_stays_untranscribed(self):
        record = self.run_export(self.voice("missing.ogg"))[0]
        self.assertEqual(record["asr_status"], "NOT_REQUESTED")
        self.assertEqual(record["segments"], [])

    def test_asr_adapter_provenance(self):
        (self.root / "voice.ogg").write_bytes(b"synthetic-not-real-audio")
        result = self.run_export(self.voice(), model_id="fixture-only", transcribe=lambda _: [
            {"start": 0.0, "end": 1.0, "text": "Не торговать"}])
        self.assertEqual(result[0]["asr_status"], "TRANSCRIBED_UNVERIFIED")
        self.assertEqual(result[0]["model_id"], "fixture-only")
        self.assertEqual(result[0]["audio_sha256"], hashlib.sha256(b"synthetic-not-real-audio").hexdigest())

    def test_path_traversal_and_urls_are_blocked(self):
        for path in ("../voice.ogg", "/tmp/voice.ogg", "C:\\voice.ogg", "https://host/a.ogg"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.run_export(self.voice(path), model_id="fixture", transcribe=lambda _: [])

    def test_symlink_is_blocked(self):
        (self.root / "voice.ogg").write_bytes(b"a")
        (self.root / "link.ogg").symlink_to(self.root / "voice.ogg")
        with self.assertRaises(ValueError):
            mod.media_path(self.root, "link.ogg")

    def test_invalid_timestamps_are_blocked(self):
        for start, end in [(False, 1), (float("nan"), 1), (2, 1), (-1, 0)]:
            with self.subTest(start=start), self.assertRaises(ValueError):
                mod.checked_segments([{"start": start, "end": end, "text": "x"}])

    def test_boolean_ids_are_blocked(self):
        with self.assertRaises(ValueError):
            self.run_export(chat(chat_id=True))

    def test_provenance_required_for_asr(self):
        with self.assertRaises(ValueError):
            self.run_export(self.voice(), transcribe=lambda _: [])

    def test_incomplete_local_checkpoint_is_blocked(self):
        with self.assertRaises(ValueError):
            mod.local_whisper(self.root, "ru")

    def test_local_whisper_call_contract_without_real_inference(self):
        for name in ("model.bin", "config.json", "tokenizer.json"):
            (self.root / name).write_bytes(b"synthetic")
        observed = {}

        class FakeModel:
            def __init__(self, path, **options):
                observed.update(options)

            def transcribe(self, path, **options):
                observed["transcribe"] = options
                return iter([SimpleNamespace(start=0, end=1, text="fixture")]), None

        with patch.dict("sys.modules", {"faster_whisper": SimpleNamespace(WhisperModel=FakeModel)}):
            with patch.object(mod.importlib.metadata, "version", return_value="fixture"):
                transcriber, model_id = mod.local_whisper(self.root, "ru")
                segments = list(transcriber(self.root / "voice.ogg"))
        self.assertTrue(observed["local_files_only"])
        self.assertEqual(observed["device"], "cpu")
        self.assertEqual(observed["transcribe"]["language"], "ru")
        self.assertEqual(segments[0]["text"], "fixture")
        self.assertTrue(model_id.startswith("faster-whisper:fixture:"))

    def test_bundle_ready_hashes_and_no_overwrite(self):
        out = self.root / "out"
        records = self.run_export(chat())
        mod.write_bundle(out, records, "a" * 64)
        ready = json.loads((out / "READY.json").read_text())
        for filename, digest in ready["files"].items():
            self.assertEqual(mod.sha256((out / filename).read_bytes()), digest)
        self.assertIn("Не включать live", (out / "transcript.md").read_text())
        with self.assertRaises(FileExistsError):
            mod.write_bundle(out, records, "a" * 64)


if __name__ == "__main__":
    unittest.main()
