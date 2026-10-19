"""Provider-free corpus migration checks; no real runtime assets are replaced."""
from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

from greia_voice_core.direction import character_delivery, DEFAULT_DELIVERY_FILE
from greia_voice_core.models import (VoiceRequest, SpeechKind, GenerationDisposition,
                                     GenerationResult, VerificationResult, VerificationDisposition)
from greia_voice_core.registry import CANONICAL_MANIFEST, VoiceRegistry
from greia_voice_core.service import request_from_mapping
from greia_voice_corpus.inventory import CorpusInventory, digest, preserved_reason, receipt_path, safe_target
from greia_voice_corpus.runner import CorpusRunner
from greia_voice_corpus.store import RunStore, write_json, atomic_bytes
from greia_voice_corpus.catalogues import derived_replacements


class FakeEngine:
    def __init__(self, root, warning=False):
        self.calls = []
        self.root, self.warning = root, warning

    def generate(self, request):
        self.calls.append(request)
        atomic_bytes(request.output, b"new packaged speech")
        profile = VoiceRegistry.load(self.root).get(request.speaker)
        verification = VerificationResult(VerificationDisposition.WARN if self.warning else VerificationDisposition.NOT_RUN, "off")
        receipt = {"request": request.to_dict(), "provider_id": "voxstage-voxcpm2", "voice_id": profile.voice_id,
                   "reference_sha256": profile.anchor_sha256, "voice_registry_version": "v0.2",
                   "human_review": "PENDING", "generation_parameters": {"delivery_prompt": request.delivery_prompt},
                   "verification": verification.to_dict(), "attempts": 1,
                   "output": {"path": str(request.output), "sha256": digest(request.output), "bytes": request.output.stat().st_size}}
        write_json(receipt_path(request.output), receipt)
        return GenerationResult(GenerationDisposition.REVIEW_REQUIRED_ASR_WARNING if self.warning else GenerationDisposition.REVIEW_REQUIRED,
                                request, "voxstage-voxcpm2", request.output, receipt_path(request.output), verification, 1)


class CorpusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "repo"
        self.root.mkdir()
        self.relative = "activities/example/assets/audio/en/hello.wav"
        self.audio = self.root / self.relative
        atomic_bytes(self.audio, b"old accepted speech")
        write_json(receipt_path(self.audio), {"request": {"speaker": "leo", "kind": "character_dialogue", "locale": "en", "text": "Hello!"}})
        atomic_bytes(self.root / CANONICAL_MANIFEST, (ROOT / CANONICAL_MANIFEST).read_bytes())
        # Copy exact selected refs for the existing registry, without generation.
        for profile in VoiceRegistry.load(ROOT).profiles.values():
            atomic_bytes(self.root / profile.anchor_path.relative_to(ROOT), profile.anchor_path.read_bytes())
        self.row = {"path": self.relative, "state": "READY", "reason": "", "original_sha256": digest(self.audio),
                    "original_receipt_sha256": digest(receipt_path(self.audio)), "request": {"speaker": "leo", "kind": "character_dialogue",
                    "locale": "en", "text": "Hello!", "cue_id": "example.hello", "delivery_prompt": "Warm and curious."}}
        self.plan = {"root": str(self.root), "registry_manifest_sha256": digest(self.root / CANONICAL_MANIFEST), "rows": [self.row]}
        self.store = RunStore.create(self.base / "run", self.plan)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def run_runner(self, engine=None, **kwargs):
        engine = engine or FakeEngine(self.root)
        with redirect_stdout(io.StringIO()):
            result = CorpusRunner(self.store, engine).run(**kwargs)
        return result, engine

    def test_generate_replace_resume_and_restore_receipt_pair(self):
        old_receipt = receipt_path(self.audio).read_bytes()
        code, engine = self.run_runner()
        self.assertEqual(code, 0)
        self.assertEqual(self.audio.read_bytes(), b"new packaged speech")
        receipt = json.loads(receipt_path(self.audio).read_text())
        self.assertEqual(receipt["human_review"], "PENDING")
        self.assertEqual(receipt["request"]["output"], self.relative)
        self.assertEqual(receipt["request"]["delivery_prompt"], "Warm and curious.")
        self.assertEqual(self.run_runner(engine)[0], 0)
        self.assertEqual(len(engine.calls), 1)
        self.store.restore()
        self.assertEqual(self.audio.read_bytes(), b"old accepted speech")
        self.assertEqual(receipt_path(self.audio).read_bytes(), old_receipt)
        with self.assertRaisesRegex(ValueError, "restored"):
            self.run_runner()

    def test_destination_edit_blocks_synthesis(self):
        self.audio.write_bytes(b"concurrent owner edit")
        code, engine = self.run_runner()
        self.assertEqual(code, 2)
        self.assertEqual(engine.calls, [])
        self.assertEqual(self.audio.read_bytes(), b"concurrent owner edit")

    def test_missing_or_changed_master_blocks_run(self):
        profile = VoiceRegistry.load(self.root).get("leo")
        profile.anchor_path.write_bytes(b"wrong reference")
        with self.assertRaisesRegex(Exception, "hash mismatch"):
            self.run_runner()
        self.assertEqual(self.audio.read_bytes(), b"old accepted speech")

    def test_inflight_interruption_does_not_submit_again(self):
        self.store.set_state(self.relative, "GENERATING")
        code, engine = self.run_runner()
        self.assertEqual(code, 2)
        self.assertEqual(engine.calls, [])
        self.assertEqual(self.store.state(self.relative), "NEEDS_RECOVERY")

    def test_complete_candidate_after_interruption_is_reused(self):
        engine = FakeEngine(self.root)
        candidate = self.store.work / "candidates" / self.relative
        engine.generate(VoiceRequest(**{k: v for k, v in self.row["request"].items() if k != "kind"}, kind=SpeechKind.CHARACTER_DIALOGUE, output=candidate))
        self.store.set_state(self.relative, "GENERATING")
        self.assertEqual(self.run_runner(engine)[0], 0)
        self.assertEqual(len(engine.calls), 1)

    def test_warning_leaves_original_and_requires_operator_retry(self):
        engine = FakeEngine(self.root, warning=True)
        self.assertEqual(self.run_runner(engine)[0], 2)
        self.assertEqual(self.audio.read_bytes(), b"old accepted speech")
        self.assertEqual(self.store.state(self.relative), "FAILED")
        self.run_runner(engine)
        self.assertEqual(len(engine.calls), 1)

    def test_partial_pair_install_recovers_then_restores(self):
        candidate = self.store.work / "replacement.wav"
        atomic_bytes(candidate, b"replacement")
        target_receipt = receipt_path(self.audio)
        candidate_receipt = receipt_path(candidate)
        atomic_bytes(candidate_receipt, b"new receipt")
        transaction = self.store.prepare(self.relative, {self.relative: candidate, str(target_receipt.relative_to(self.root)): candidate_receipt})
        backup = self.store.work / "backups" / str(transaction) / self.relative
        atomic_bytes(backup, self.audio.read_bytes())
        atomic_bytes(self.audio, candidate.read_bytes())  # crash after first rename
        self.store.recover()
        self.assertEqual(target_receipt.read_bytes(), b"new receipt")
        self.assertEqual(self.store.state(self.relative), "DONE")
        self.store.restore()
        self.assertEqual(self.audio.read_bytes(), b"old accepted speech")

    def test_restore_refuses_to_erase_later_edit(self):
        self.run_runner()
        self.audio.write_bytes(b"owner edited this after production")
        with self.assertRaisesRegex(ValueError, "later edit"):
            self.store.restore()

    def test_new_receipt_is_removed_on_restore_when_original_had_none(self):
        receipt_path(self.audio).unlink()
        self.row["original_receipt_sha256"] = None
        self.store.plan["rows"] = [self.row]
        self.assertEqual(self.run_runner()[0], 0)
        self.store.restore()
        self.assertFalse(receipt_path(self.audio).exists())

    def test_inventory_uses_receipts_and_preserves_only_isolated_targets(self):
        census = {"spoken_resources": [], "structural_errors": []}
        with patch("greia_voice_corpus.inventory.build_inventory", return_value=census):
            plan = CorpusInventory(self.root, DEFAULT_DELIVERY_FILE).build()
        row = next(r for r in plan["rows"] if r["path"] == self.relative)
        self.assertEqual(row["state"], "READY")
        self.assertEqual(row["request"]["delivery_prompt"], character_delivery()["leo"])
        self.assertTrue(preserved_reason("activities/sillabe_magiche/assets/audio/en/syl_ma.wav", {}))
        self.assertTrue(preserved_reason("activities/example/en/letter.wav", {"kind": "pedagogical_speech", "text": "A"}))
        self.assertFalse(preserved_reason("activities/alfabeto_leo/assets/audio/it/letter_A.wav", {"kind": "pedagogical_speech", "text": "A come Ape"}))
        self.assertFalse(preserved_reason("activities/sillabe_magiche/assets/audio/en/find_ma.wav", {"kind": "pedagogical_speech", "text": "Find ma"}))

    def test_paths_cannot_replace_master_or_escape(self):
        for path in ("../escape.wav", "/tmp/a.wav", "assets/audio/characters/canonical/v0.2/leo-reference-v2.wav", "assets/audio/characters/shared/v0.1/old.wav"):
            with self.assertRaises(ValueError):
                safe_target(self.root, path)

    def test_prompt_survives_service_mapping_and_validation(self):
        request = request_from_mapping({**self.row["request"], "output": None})
        self.assertEqual(request.delivery_prompt, "Warm and curious.")
        with self.assertRaises(ValueError):
            replace(request, delivery_prompt="x" * 2001)

    def test_shared_metadata_and_checksum_transaction_rollback(self):
        relative = "assets/audio/characters/shared/v0.2/leo/en/hello.wav"
        target = self.root / relative
        atomic_bytes(target, b"original shared")
        shared = self.root / "assets/audio/characters/shared/v0.2"
        manifest = shared / "manifest.toml"
        atomic_bytes(manifest, b'status = "owner accepted"\n\n[[utterance]]\nfile = "leo/en/hello.wav"\nsha256 = "old"\nhuman_review = "APPROVED"\n')
        before = manifest.read_bytes()
        candidate = self.store.work / "shared.wav"
        engine = FakeEngine(self.root)
        request = VoiceRequest("leo", SpeechKind.SHARED_CHARACTER_UTTERANCE, "en", "Hello!", output=candidate, delivery_prompt="Warm smile.")
        engine.generate(request)
        receipt = json.loads(receipt_path(candidate).read_text())
        updates = derived_replacements(self.root, relative, receipt, self.store.work / "meta")
        replacements = {relative: candidate, **updates}
        # Standalone transaction fixture does not require a matching cue row.
        transaction = self.store.prepare(self.relative, replacements)
        self.store.install(transaction)
        row = tomllib.loads(manifest.read_text())["utterance"][0]
        self.assertEqual(row["human_review"], "PENDING")
        self.assertEqual(row["delivery_prompt"], "Warm smile.")
        self.store.restore()
        self.assertEqual(manifest.read_bytes(), before)
        self.assertEqual(target.read_bytes(), b"original shared")

    def test_repeated_metadata_transactions_restore_in_reverse_order(self):
        relative = "activities/example/assets/audio/audio_manifest.sha256"
        target = self.root / relative
        atomic_bytes(target, b"original catalogue")
        for index in (1, 2):
            candidate = self.store.work / f"catalogue-{index}"
            atomic_bytes(candidate, f"catalogue version {index}".encode())
            self.store.install(self.store.prepare(self.relative, {relative: candidate}))
        self.store.restore()
        self.assertEqual(target.read_bytes(), b"original catalogue")

    def test_checksum_entry_updates_only_target_recording(self):
        manifest = self.audio.parent.parent / "audio_manifest.sha256"
        atomic_bytes(manifest, b"old  en/hello.wav\nother  en/other.wav\n")
        receipt = {"output": {"sha256": "replacement"}}
        updates = derived_replacements(self.root, self.relative, receipt, self.store.work / "meta")
        text = updates[str(manifest.relative_to(self.root))].read_text()
        self.assertEqual(text, "replacement  en/hello.wav\nother  en/other.wav\n")

    def test_resolve_updates_only_blocked_rows_and_retains_done_work(self):
        import argparse
        import regenerate_voice_corpus as cli
        self.store.set_state(self.relative, "BLOCKED_METADATA", "missing old script")
        override = self.base / "overrides.json"
        write_json(override, {self.relative: {"text": "Recovered exact wording."}})
        args = argparse.Namespace(command="resolve", work_dir=self.store.work, overrides=override, delivery_file=DEFAULT_DELIVERY_FILE)
        census = {"spoken_resources": [], "structural_errors": []}
        with patch.object(cli, "PROJECT_ROOT", self.root), patch.object(cli, "voice_home", return_value=self.base / "voice"), patch("greia_voice_corpus.inventory.build_inventory", return_value=census), redirect_stdout(io.StringIO()):
            self.assertEqual(cli.mutate_command(args), 0)
        self.assertEqual(self.store.state(self.relative), "READY")
        new_plan = json.loads((self.store.work / "plan.json").read_text())
        self.assertEqual(new_plan["rows"][0]["request"]["text"], "Recovered exact wording.")
        self.assertEqual(self.audio.read_bytes(), b"old accepted speech")
        self.store.set_state(self.relative, "DONE")
        with patch.object(cli, "PROJECT_ROOT", self.root), patch.object(cli, "voice_home", return_value=self.base / "voice"):
            with self.assertRaisesRegex(ValueError, "only currently BLOCKED"):
                cli.mutate_command(args)

    def test_unknown_file_is_blocked_not_silently_treated_as_non_speech(self):
        path = self.root / "assets/audio/system/unknown.wav"
        atomic_bytes(path, b"unknown source")
        census = {"spoken_resources": [], "structural_errors": []}
        with patch("greia_voice_corpus.inventory.build_inventory", return_value=census):
            plan = CorpusInventory(self.root, DEFAULT_DELIVERY_FILE).build()
        row = next(r for r in plan["rows"] if r["path"] == "assets/audio/system/unknown.wav")
        self.assertEqual(row["state"], "BLOCKED_METADATA")
        self.assertIn("text", row["reason"])


if __name__ == "__main__":
    unittest.main()
