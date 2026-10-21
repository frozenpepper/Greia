"""Automated screening tests: corrupt/silent audio must be detectable, never approved."""
from dataclasses import replace
from pathlib import Path
import json
import math
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import wave
from array import array

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

from greia_voice_core.review import AudioReviewer, signal_metrics, probe_cached_asr
from greia_voice_core.models import VoiceRequest, SpeechKind, VerificationResult, VerificationDisposition
from greia_voice_core.registry import CANONICAL_MANIFEST, VoiceRegistry
from greia_voice_corpus.review import CorpusReview
from greia_voice_corpus.store import RunStore, write_json
from greia_voice_corpus.inventory import digest, receipt_path


def tone(path, *, silence=False, lead=0, tail=0, gap=0):
    path.parent.mkdir(parents=True, exist_ok=True)
    values = [0] * int(22050 * lead)
    values += [0 if silence else int(6000 * math.sin(i * 2 * math.pi * 220 / 22050)) for i in range(22050)]
    if gap:
        at = int(22050 * lead) + 11025
        values[at:at] = [0] * int(22050 * gap)
    values += [0] * int(22050 * tail)
    data = array("h", values)
    if sys.byteorder != "little":
        data.byteswap()
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(22050)
        output.writeframes(data.tobytes())


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        self.audio = self.base / "audio.wav"
        tone(self.audio)
        self.request = VoiceRequest("leo", SpeechKind.CHARACTER_DIALOGUE, "en", "Hello my friend", delivery_prompt="Warm curious playful smile")
        self.verifier = Mock(verifier_id="test-verifier", model_id="cached-test", pass_threshold=.8)
        self.verifier.verify.return_value = VerificationResult(VerificationDisposition.PASS, "test", "Hello my friend", 1.0)
        self.pipeline = Mock()
        self.pipeline.decode_for_review.side_effect = lambda source, output: shutil.copyfile(source, output)

    def tearDown(self):
        self.temp.cleanup()

    def reviewer(self, asr=True, ready=True):
        return AudioReviewer(self.verifier, asr=asr, asr_ready=(ready, "test unavailable"), pipeline=self.pipeline)

    def test_clean_signal_and_known_silence_positive_control(self):
        metrics, flags = signal_metrics(self.audio)
        self.assertEqual(flags, [])
        self.assertAlmostEqual(metrics["duration_seconds"], 1)
        tone(self.audio, silence=True)
        with self.assertRaisesRegex(ValueError, "silent"):
            signal_metrics(self.audio)

    def test_long_silence_is_flagged(self):
        tone(self.audio, lead=.6, tail=1.6)
        _, flags = signal_metrics(self.audio)
        self.assertIn("LONG_LEADING_SILENCE", flags)
        self.assertIn("LONG_TRAILING_SILENCE", flags)

    def test_pause_and_tail_boundaries(self):
        for seconds, warned in ((1.48, False), (1.5, True), (1.52, True)):
            tone(self.audio, tail=seconds, gap=seconds)
            _, flags = signal_metrics(self.audio)
            self.assertEqual('LONG_TRAILING_SILENCE' in flags, warned)
            self.assertEqual('LONG_INTERNAL_PAUSE' in flags, warned)

    def test_saved_scores_and_old_pause_flags_follow_current_policy(self):
        from greia_voice_core.review_policy import reassess_result
        record = {'status':'WARN', 'flags':['LONG_TRAILING_SILENCE','LONG_INTERNAL_PAUSE'],
                  'metrics':{'trailing_silence_seconds':1.0,'longest_internal_pause_seconds':1.48},
                  'asr':{'status':'PASS','disposition':'PASS','score':.81}}
        self.assertEqual(reassess_result(record)['status'], 'PASS')
        self.assertEqual(record['status'], 'WARN')
        for score in (.79, .8):
            record['asr']['score'] = score
            self.assertEqual(reassess_result(record)['status'], 'WARN')
        record['asr']['score'] = 1.0
        record['flags'].append('POSSIBLE_PROMPT_LEAKAGE')
        self.assertEqual(reassess_result(record)['status'], 'WARN')

    def test_saved_reassessment_never_runs_asr_and_rejects_changed_audio(self):
        target, _ = self.corpus()
        reviewer = self.reviewer()
        source, dest = self.base / 'source-report', self.base / 'reassessed'
        with patch('builtins.print'):
            CorpusReview(self.base / 'run', reviewer).run(source)
            old = (source / 'review.jsonl').read_bytes()
            self.assertEqual(CorpusReview(self.base / 'run', reviewer).run(dest, evidence=source), 0)
            self.assertEqual(self.verifier.verify.call_count, 1)
            self.assertEqual((source / 'review.jsonl').read_bytes(), old)
            # Keep the current receipt internally valid while invalidating old evidence.
            target.write_bytes(target.read_bytes() + b'changed')
            receipt = json.loads(receipt_path(target).read_text())
            receipt['output'] = {'sha256':digest(target),'bytes':target.stat().st_size}
            write_json(receipt_path(target), receipt)
            self.assertEqual(CorpusReview(self.base / 'run', reviewer).run(self.base / 'stale', evidence=source), 2)
            self.assertEqual(self.verifier.verify.call_count, 1)

    def test_defaults_are_performance_only(self):
        from greia_voice_core.direction import character_delivery
        defaults = character_delivery()
        self.assertEqual(len(set(defaults.values())), 1)
        for value in defaults.values():
            for identity in ('robot','unicorn','fox','monster','pitch','nasal','baritone'):
                self.assertNotIn(identity, value.lower())

    def test_signal_failure_never_invokes_asr(self):
        self.audio.write_bytes(b"invalid audio")
        with self.assertRaises((wave.Error, EOFError)):
            self.reviewer().review(self.request, self.audio)
        self.verifier.verify.assert_not_called()

    def test_missing_asr_is_blocked_and_never_called(self):
        result = self.reviewer(ready=False).review(self.request, self.audio)
        self.assertEqual(result["status"], "BLOCKED")
        self.verifier.verify.assert_not_called()

    def test_disabled_asr_and_policy_exclusions_are_explicit(self):
        self.assertEqual(self.reviewer(asr=False).review(self.request, self.audio)["asr"]["status"], "DISABLED")
        for request in (replace(self.request, text="Ten!"), replace(self.request, speaker="dani")):
            self.assertEqual(self.reviewer().review(request, self.audio)["asr"]["status"], "NOT_APPLICABLE_POLICY")
        self.verifier.verify.assert_not_called()

    def test_prompt_leakage_positive_control_warns_even_with_high_score(self):
        self.verifier.verify.return_value = VerificationResult(VerificationDisposition.PASS, "test", "Hello my friend curious playful", .9)
        result = self.reviewer().review(self.request, self.audio)
        self.assertEqual(result["status"], "WARN")
        self.assertIn("POSSIBLE_PROMPT_LEAKAGE", result["flags"])

    def test_asr_runtime_error_is_blocked(self):
        self.verifier.verify.return_value = VerificationResult(VerificationDisposition.WARN, "test", detail="unavailable at runtime")
        result = self.reviewer().review(self.request, self.audio)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["asr"]["status"], "ERROR")

    def test_probe_does_not_attempt_weights_when_import_unavailable(self):
        self.verifier.probe.return_value = False, "no local ASR"
        self.assertEqual(probe_cached_asr(self.verifier), (False, "no local ASR"))

    def corpus(self):
        root = self.base / "repo"
        relative = "activities/example/assets/audio/en/hello.wav"
        target = root / relative
        target.parent.mkdir(parents=True)
        shutil.copyfile(self.audio, target)
        (root / CANONICAL_MANIFEST).parent.mkdir(parents=True)
        shutil.copyfile(ROOT / CANONICAL_MANIFEST, root / CANONICAL_MANIFEST)
        for profile in VoiceRegistry.load(ROOT).profiles.values():
            copy = root / profile.anchor_path.relative_to(ROOT)
            shutil.copyfile(profile.anchor_path, copy)
        request = self.request.to_dict()
        request = {key: request[key] for key in ("speaker", "kind", "locale", "text", "cue_id", "delivery_prompt")}
        profile = VoiceRegistry.load(ROOT).get("leo")
        write_json(receipt_path(target), {"request": request, "voice_id": profile.voice_id,
            "reference_sha256": profile.anchor_sha256, "provider_id": "voxstage-voxcpm2",
            "generation_parameters": {"delivery_prompt": request["delivery_prompt"]},
            "human_review": "PENDING", "output": {"sha256": digest(target), "bytes": target.stat().st_size}})
        plan = {"root": str(root), "rows": [{"path": relative, "state": "READY", "reason": "", "request": request}]}
        store = RunStore.create(self.base / "run", plan)
        store.set_state(relative, "DONE")
        store.close()
        return target, relative

    def test_resumable_review_never_writes_audio_receipt_or_journal(self):
        target, relative = self.corpus()
        work = self.base / "run"
        before = [p.read_bytes() for p in (target, receipt_path(target), work / "state.sqlite3")]
        review = CorpusReview(work, self.reviewer())
        with patch("builtins.print"):
            self.assertEqual(review.run(self.base / "report"), 0)
            self.assertEqual(review.run(self.base / "report"), 0)
        self.assertEqual(self.verifier.verify.call_count, 1)
        self.assertEqual(before, [p.read_bytes() for p in (target, receipt_path(target), work / "state.sqlite3")])
        summary = json.loads((self.base / "report/summary.json").read_text())
        self.assertFalse(summary["human_acceptance_granted"])
        self.assertTrue(summary["eligible_asr_complete"])
        target.write_bytes(b"changed after review")
        with patch("builtins.print"):
            self.assertEqual(review.run(self.base / "report"), 2)
        self.assertEqual(self.verifier.verify.call_count, 1)

    def test_technical_only_and_missing_asr_never_report_complete_speech_review(self):
        self.corpus()
        for name, reviewer in (("off", self.reviewer(asr=False)), ("unavailable", self.reviewer(ready=False))):
            with patch("builtins.print"):
                self.assertEqual(CorpusReview(self.base / "run", reviewer).run(self.base / name), 3)
            self.assertFalse(json.loads((self.base / name / "summary.json").read_text())["eligible_asr_complete"])

    def test_blocked_asr_is_rechecked_after_readiness_changes(self):
        self.corpus()
        report = self.base / "report"
        with patch("builtins.print"):
            self.assertEqual(CorpusReview(self.base / "run", self.reviewer(ready=False)).run(report), 3)
            self.assertEqual(CorpusReview(self.base / "run", self.reviewer()).run(report), 0)
        self.assertEqual(self.verifier.verify.call_count, 1)

    def test_required_weights_probe_is_local_only(self):
        self.verifier.probe.return_value = True, "installed"
        downloader = Mock(return_value="/cached/model")
        with patch.dict(sys.modules, {"huggingface_hub": Mock(snapshot_download=downloader)}):
            self.assertTrue(probe_cached_asr(self.verifier)[0])
        downloader.assert_called_once_with(self.verifier.model_id, local_files_only=True)


if __name__ == "__main__":
    unittest.main()
