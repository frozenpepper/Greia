from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "tools"))

from greia_voice_core.engine import VoiceEngine
from greia_voice_core.locking import GenerationLockError, InterprocessGenerationLock
from greia_voice_core.models import (
    GeneratedTake,
    GenerationDisposition,
    ProviderStatus,
    SpeechKind,
    VerificationDisposition,
    VerificationMode,
    VerificationResult,
    VoiceProfile,
    VoiceRequest,
)
from greia_voice_core.native import pedagogical_synthesis_text
from greia_voice_core.providers import VoiceProvider
from greia_voice_core.registry import VoiceRegistry
from greia_voice_core.verification import asr_eligible, transcript_similarity


class NullLock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None


class FakeAudioPipeline:
    def validate_review_wav(self, path: Path):
        return object()

    def package(self, source: Path, output: Path) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(source.read_bytes())
        return output


class FakeProvider(VoiceProvider):
    provider_id = "fake"

    def __init__(self, supported_kind: SpeechKind) -> None:
        self.supported_kind = supported_kind
        self.calls = 0

    def supports(self, request, profile) -> bool:
        return request.kind is self.supported_kind

    def probe(self):
        return ProviderStatus(self.provider_id, True, "fake")

    def generate(self, request, profile):
        self.calls += 1
        handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        handle.close()
        path = Path(handle.name)
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(22050)
            wav.writeframes(b"\x01\x00" * 4410)
        return GeneratedTake(self.provider_id, path, 22050, {"call": self.calls})


class SequenceVerifier:
    verifier_id = "fake-verifier"

    def __init__(self, dispositions):
        self.dispositions = list(dispositions)
        self.calls = 0

    def probe(self):
        return True, "fake"

    def verify(self, request, path):
        disposition = self.dispositions[min(self.calls, len(self.dispositions) - 1)]
        self.calls += 1
        return VerificationResult(disposition, self.verifier_id, transcript="hello", score=0.8)


def make_registry(root: Path) -> VoiceRegistry:
    anchor = root / "leo.flac"
    anchor.write_bytes(b"anchor")
    return VoiceRegistry(
        project_root=root,
        registry_version="test",
        profiles={
            "leo": VoiceProfile(
                character="leo",
                voice_id="greia.leo.v1",
                production="cloned_reference",
                purpose="test",
                anchor_path=anchor,
                anchor_sha256=hashlib.sha256(b"anchor").hexdigest(),
            ),
            "dani": VoiceProfile(
                character="dani",
                voice_id="greia.dani.system-v1",
                production="greia_os_tts",
                purpose="test",
            ),
        },
    )


class GenerationLockTests(unittest.TestCase):
    def test_second_worker_fails_fast_while_first_lock_is_live(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "generation.lock"
            with InterprocessGenerationLock(lock_path):
                with self.assertRaises(GenerationLockError):
                    with InterprocessGenerationLock(lock_path):
                        pass
            self.assertFalse(lock_path.exists())


class VoiceRequestTests(unittest.TestCase):
    def test_semantic_kind_not_text_length_controls_pedagogical_route(self):
        request = VoiceRequest("pedagogical", SpeechKind.PEDAGOGICAL_SPEECH, "it", "ma")
        self.assertEqual(request.kind, SpeechKind.PEDAGOGICAL_SPEECH)
        self.assertFalse(asr_eligible(request))

    def test_character_dialogue_two_words_is_asr_eligible(self):
        request = VoiceRequest("leo", SpeechKind.CHARACTER_DIALOGUE, "it", "Guarda qui!")
        self.assertTrue(asr_eligible(request))

    def test_shared_two_word_utterance_is_asr_eligible_but_tiny_reaction_is_not(self):
        self.assertTrue(
            asr_eligible(
                VoiceRequest(
                    "leo",
                    SpeechKind.SHARED_CHARACTER_UTTERANCE,
                    "it",
                    "Ottimo lavoro!",
                )
            )
        )
        self.assertFalse(
            asr_eligible(
                VoiceRequest(
                    "leo",
                    SpeechKind.SHARED_CHARACTER_UTTERANCE,
                    "it",
                    "Evviva!",
                )
            )
        )

    def test_pedagogical_macos_hints_do_not_change_request_text(self):
        request = VoiceRequest("pedagogical", SpeechKind.PEDAGOGICAL_SPEECH, "it", "Trova TO")
        self.assertEqual(request.text, "Trova TO")
        self.assertEqual(pedagogical_synthesis_text(request.text, "it"), "trova tò")

    def test_transcript_similarity_detects_close_and_bad_transcripts(self):
        self.assertGreater(transcript_similarity("Ottimo lavoro!", "Ottimo lavoro."), 0.95)
        self.assertLess(transcript_similarity("Ottimo lavoro!", "Buonanotte mondo"), 0.4)


class VoiceEngineTests(unittest.TestCase):
    def test_chatterbox_style_request_retries_after_asr_warning_and_writes_pending_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            provider = FakeProvider(SpeechKind.CHARACTER_DIALOGUE)
            verifier = SequenceVerifier([
                VerificationDisposition.WARN,
                VerificationDisposition.PASS,
            ])
            output = root / "review.wav"
            engine = VoiceEngine(
                root,
                make_registry(root),
                [provider],
                verifier=verifier,
                audio_pipeline=FakeAudioPipeline(),
                generation_lock=NullLock(),
            )
            result = engine.generate(
                VoiceRequest(
                    "leo",
                    SpeechKind.CHARACTER_DIALOGUE,
                    "it",
                    "Guarda qui!",
                    cue_id="presenter.hint",
                    output=output,
                    max_attempts=2,
                )
            )
            self.assertEqual(result.disposition, GenerationDisposition.REVIEW_REQUIRED)
            self.assertEqual(provider.calls, 2)
            self.assertTrue(output.is_file())
            receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["human_review"], "PENDING")
            self.assertEqual(receipt["attempts"], 2)
            self.assertEqual(receipt["voice_id"], "greia.leo.v1")

    def test_shared_character_library_production_routes_through_engine(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            provider = FakeProvider(SpeechKind.SHARED_CHARACTER_UTTERANCE)
            engine = VoiceEngine(
                root,
                make_registry(root),
                [provider],
                verifier=SequenceVerifier([VerificationDisposition.PASS]),
                audio_pipeline=FakeAudioPipeline(),
                generation_lock=NullLock(),
            )
            result = engine.generate(
                VoiceRequest(
                    "leo",
                    SpeechKind.SHARED_CHARACTER_UTTERANCE,
                    "it",
                    "Ottimo lavoro!",
                    cue_id="shared.praise.general.01",
                    output=root / "shared.wav",
                )
            )
            self.assertEqual(result.disposition, GenerationDisposition.REVIEW_REQUIRED)
            receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["voice_id"], "greia.leo.v1")
            self.assertEqual(receipt["request"]["kind"], "shared_character_utterance")

    def test_shared_dani_library_production_keeps_dani_system_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            provider = FakeProvider(SpeechKind.SHARED_CHARACTER_UTTERANCE)
            engine = VoiceEngine(
                root,
                make_registry(root),
                [provider],
                verifier=SequenceVerifier([VerificationDisposition.NOT_APPLICABLE]),
                audio_pipeline=FakeAudioPipeline(),
                generation_lock=NullLock(),
            )
            result = engine.generate(
                VoiceRequest(
                    "dani",
                    SpeechKind.SHARED_CHARACTER_UTTERANCE,
                    "it",
                    "Ottimo lavoro!",
                    output=root / "dani-shared.wav",
                )
            )
            self.assertEqual(result.disposition, GenerationDisposition.REVIEW_REQUIRED)
            receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["voice_id"], "greia.dani.system-v1")

    def test_asr_warning_never_becomes_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            provider = FakeProvider(SpeechKind.CHARACTER_DIALOGUE)
            verifier = SequenceVerifier([VerificationDisposition.WARN])
            engine = VoiceEngine(
                root,
                make_registry(root),
                [provider],
                verifier=verifier,
                audio_pipeline=FakeAudioPipeline(),
                generation_lock=NullLock(),
            )
            result = engine.generate(
                VoiceRequest(
                    "leo",
                    SpeechKind.CHARACTER_DIALOGUE,
                    "it",
                    "Guarda qui!",
                    output=root / "x.wav",
                )
            )
            self.assertEqual(result.disposition, GenerationDisposition.REVIEW_REQUIRED_ASR_WARNING)
            self.assertEqual(provider.calls, 2)

    def test_dani_cannot_route_through_character_dialogue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = VoiceEngine(
                root,
                make_registry(root),
                [FakeProvider(SpeechKind.CHARACTER_DIALOGUE)],
                verifier=SequenceVerifier([VerificationDisposition.PASS]),
                audio_pipeline=FakeAudioPipeline(),
                generation_lock=NullLock(),
            )
            result = engine.generate(
                VoiceRequest("dani", SpeechKind.CHARACTER_DIALOGUE, "it", "Ciao mondo")
            )
            self.assertEqual(result.disposition, GenerationDisposition.REJECTED)
            self.assertIn("dani_system_speech", result.detail)

    def test_pedagogical_speech_rejects_character_impersonation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = VoiceEngine(
                root,
                make_registry(root),
                [FakeProvider(SpeechKind.PEDAGOGICAL_SPEECH)],
                verifier=SequenceVerifier([VerificationDisposition.NOT_APPLICABLE]),
                audio_pipeline=FakeAudioPipeline(),
                generation_lock=NullLock(),
            )
            result = engine.generate(
                VoiceRequest("leo", SpeechKind.PEDAGOGICAL_SPEECH, "it", "ma")
            )
            self.assertEqual(result.disposition, GenerationDisposition.REJECTED)
            self.assertIn("pedagogical", result.detail)


if __name__ == "__main__":
    unittest.main()
