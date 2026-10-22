from __future__ import annotations

import math
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))

from greia_voice_core.audio import AudioPipeline
from greia_voice_core.models import GenerationDisposition, GenerationResult, SpeechKind, VerificationResult, VerificationDisposition
from greia_voice_corpus.carrier_generation import generate_candidate, prepare_saved_candidate, CarrierExtractionFailure
from greia_voice_corpus.carriers import freeze_row
from greia_voice_corpus.inventory import digest, receipt_path
from greia_voice_corpus.store import write_json


def synthetic_result(words):
    return {"text": " ".join(word for word, _, _ in words),
            "segments": [{"words": [{"word": word, "start": start, "end": end}
                                    for word, start, end in words]}]}


class FakeEngine:
    def __init__(self, root):
        self.root = root
        self.audio = AudioPipeline()
        self.calls = []

    def generate(self, request):
        self.calls.append(request)
        rate, duration = 22050, 3.2
        samples = [0] * round(rate * duration)
        for start, end in ((.1, 1.45), (2.0, 2.8)):
            left, right = round(start * rate), round(end * rate)
            for index in range(left, right):
                samples[index] = int(5000 * math.sin(index * .07))
        import struct
        with wave.open(str(request.output), "wb") as output:
            output.setnchannels(1); output.setsampwidth(2); output.setframerate(rate)
            output.writeframes(struct.pack(f"<{len(samples)}h", *samples))
        profile = SimpleNamespace(voice_id="greia.dani.v3", anchor_sha256="master-hash")
        receipt = {"request": request.to_dict(), "provider_id": "voxstage-voxcpm2",
                   "voice_id": profile.voice_id, "reference_sha256": profile.anchor_sha256,
                   "voice_registry_version": "v0.3", "created_utc": "2026-10-21T00:00:00Z",
                   "human_review": "PENDING",
                   "generation_parameters": {"delivery_prompt": request.delivery_prompt},
                   "output": {"sha256": digest(request.output), "bytes": request.output.stat().st_size}}
        write_json(receipt_path(request.output), receipt)
        verification = VerificationResult(VerificationDisposition.NOT_RUN, "off")
        return GenerationResult(GenerationDisposition.REVIEW_REQUIRED, request, "voxstage-voxcpm2",
                               request.output, receipt_path(request.output), verification, 1)


class CarrierGenerationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def row(self, suffix):
        relative = f"activities/example/assets/audio/fr/phrase.{suffix}"
        row = {"path": relative, "state": "READY", "request": {
            "speaker": "dani", "kind": "character_dialogue", "locale": "fr",
            "text": "Trouve Luna.", "cue_id": "example.trouve-luna",
            "delivery_prompt": "Clear and kind.",
        }}
        return row | {"spoken_carrier": freeze_row(row, "warn")}

    def transcriber(self, raw_path):
        raw = synthetic_result([
            ("Cette", .1, .3), ("phrase", .31, .55), ("est", .56, .7),
            ("en", .71, .82), ("français", .83, 1.45), ("Trouve", 1.95, 2.24),
            ("l'une", 2.25, 2.5), ("à", 2.51, 2.7),
        ])
        extracted = synthetic_result([("l'une", .1, .3), ("à", .31, .45)])
        return lambda path, _locale: raw if path == raw_path else extracted

    def test_runner_collaborator_packages_target_as_wav_and_ogg(self):
        for suffix in ("wav", "ogg"):
            with self.subTest(suffix=suffix):
                row = self.row(suffix)
                engine = FakeEngine(self.work)
                store = SimpleNamespace(work=self.work)
                profile = SimpleNamespace(voice_id="greia.dani.v3", anchor_sha256="master-hash")
                raw = self.work / "carrier-raw" / (row["path"] + ".raw.wav")
                candidate = generate_candidate(engine, store, row, profile, "off", transcriber=self.transcriber(raw))
                receipt = __import__("json").loads(receipt_path(candidate).read_text())
                self.assertTrue(candidate.is_file())
                self.assertEqual(candidate.suffix, "." + suffix)
                self.assertEqual(receipt["target_request"], row["request"])
                self.assertTrue(receipt["raw_audio"]["receipt_sha256"])
                self.assertEqual(receipt["extraction"]["status"], "EXTRACTED_TARGET_WARN_PENDING_LISTENING")
                self.assertEqual(receipt["extraction"]["target_verification_policy"], "warn")
                self.assertEqual(len(engine.calls), 1)

    def test_required_target_mismatch_retains_raw_and_emits_failure_evidence(self):
        row = self.row("wav")
        row["spoken_carrier"]["target_verification"] = "required"
        engine = FakeEngine(self.work)
        store = SimpleNamespace(work=self.work)
        profile = SimpleNamespace(voice_id="greia.dani.v3", anchor_sha256="master-hash")
        raw = self.work / "carrier-raw" / (row["path"] + ".raw.wav")
        with self.assertRaises(Exception):
            generate_candidate(engine, store, row, profile, "off", transcriber=self.transcriber(raw))
        self.assertTrue(raw.exists())
        self.assertTrue(receipt_path(raw).exists())
        self.assertFalse((self.work / "candidates" / row["path"]).exists())
        self.assertTrue((self.work / "carrier-evidence" / f"{row['path']}.failure.json").exists())

    def test_required_scores_only_cut_target_and_raw_verification_is_off(self):
        row = self.row("wav")
        engine = FakeEngine(self.work)
        store = SimpleNamespace(work=self.work)
        profile = SimpleNamespace(voice_id="greia.dani.v3", anchor_sha256="master-hash")
        raw = self.work / "carrier-raw" / (row["path"] + ".raw.wav")
        calls = []
        def transcribe(path, locale):
            calls.append(path)
            return synthetic_result([("garbled", .1, 1.45), ("Trouve", 2., 2.3), ("Luna", 2.31, 2.8)]) if path == raw else synthetic_result([("Trouve", .1, .4), ("Luna", .41, .9)])
        candidate = generate_candidate(engine, store, row, profile, "required", transcriber=transcribe)
        receipt = __import__("json").loads(receipt_path(candidate).read_text())
        self.assertEqual(engine.calls[0].verification.value, "off")
        self.assertEqual(receipt["verification"]["disposition"], "PASS")
        self.assertEqual(receipt["verification"]["score"], 1.)
        self.assertEqual(len(calls), 3, "delivery trimming changes PCM and requires final delivered ASR")

    def test_saved_recovery_checks_quality_without_synthesizing(self):
        row = self.row("wav")
        engine = FakeEngine(self.work)
        store = SimpleNamespace(work=self.work)
        profile = SimpleNamespace(voice_id="greia.dani.v3", anchor_sha256="master-hash")
        raw = self.work / "carrier-raw" / (row["path"] + ".raw.wav")
        generate_candidate(engine, store, row, profile, "off", transcriber=self.transcriber(raw))
        for path in (self.work / "candidates" / row["path"], receipt_path(self.work / "candidates" / row["path"]),
                     self.work / "carrier-extracted" / (row["path"] + ".extracted.wav"),
                     self.work / "carrier-extracted" / (row["path"] + ".delivery.wav")):
            path.unlink()
        with self.assertRaises(CarrierExtractionFailure):
            prepare_saved_candidate(engine, store, row, profile, "required", transcriber=self.transcriber(raw))
        self.assertEqual(len(engine.calls), 1)


if __name__ == "__main__":
    unittest.main()
