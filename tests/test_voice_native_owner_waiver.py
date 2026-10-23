"""Explicit owner-waived native speech stays distinct from machine verification."""
import json
from pathlib import Path
import math
import struct
import sys
import tempfile
import unittest
import wave
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "src")]
from greia_voice_core.audio import AudioPipeline
from greia_voice_core.engine import VoiceEngine
from greia_voice_core.locking import NullGenerationLock
from greia_voice_core.models import (
    GeneratedTake, GenerationDisposition, ProviderStatus, SpeechKind,
    VerificationDisposition, VerificationMode, VoiceProfile, VoiceRequest,
    SYSTEM_TTS_WAIVER_AUTHORIZATION,
)


class NativeFixture:
    provider_id = "macos-native-say"
    supports_delivery_prompt = False

    def __init__(self, root):
        self.root = root
        self.calls = 0

    def supports(self, request, profile):
        return (request.kind is SpeechKind.CHARACTER_DIALOGUE
                and request.owner_authorization == SYSTEM_TTS_WAIVER_AUTHORIZATION)

    def probe(self):
        return ProviderStatus(self.provider_id, True, "fixture")

    def generate(self, request, profile):
        self.calls += 1
        path = self.root / "native.wav"
        rate = 22050
        samples = [round(3000 * math.sin(i * 0.08)) for i in range(rate // 2)]
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(struct.pack(f"<{len(samples)}h", *samples))
        return GeneratedTake(self.provider_id, path, rate, {
            "voice": "Samantha", "rate_wpm": 180,
            "synthesis_text": request.spoken_text or request.text,
        })

    def close(self):
        pass


class ForbiddenVerifier:
    verifier_id = "must-not-run"

    def probe(self):
        raise AssertionError("owner-waived system request must not probe ASR")

    def verify(self, request, path):
        raise AssertionError("owner-waived system request must not call ASR")


class NativeOwnerWaiverTests(unittest.TestCase):
    def test_explicit_native_character_fallback_packages_without_claiming_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            provider = NativeFixture(root)
            profile = VoiceProfile("leo", "greia.leo", "cloned_reference", "fixture")
            registry = SimpleNamespace(registry_version="fixture", get=lambda name: profile,
                                       verify_anchor=lambda value: None)
            engine = VoiceEngine(repo, registry, [provider], verifier=ForbiddenVerifier(),
                                 generation_lock=NullGenerationLock())
            request = VoiceRequest(
                speaker="leo", kind=SpeechKind.CHARACTER_DIALOGUE, locale="en",
                text="Y as Yacht", spoken_text="why as Yacht", output=root / "published.wav",
                verification=VerificationMode.OFF, max_attempts=1, short_text_mode="off",
                owner_authorization=SYSTEM_TTS_WAIVER_AUTHORIZATION,
            )
            result = engine.generate(request)
            self.assertEqual(result.disposition, GenerationDisposition.OWNER_WAIVED, result.detail)
            self.assertEqual(result.verification.disposition, VerificationDisposition.NOT_RUN)
            self.assertEqual(provider.calls, 1)
            receipt = json.loads(result.receipt_path.read_text())
            self.assertEqual(receipt["provider_id"], "macos-native-say")
            self.assertEqual(receipt["generation_parameters"]["voice"], "Samantha")
            self.assertEqual(receipt["human_review"], "WAIVED_BY_OWNER")
            self.assertEqual(receipt["owner_authorization"], SYSTEM_TTS_WAIVER_AUTHORIZATION)
            self.assertEqual(receipt["verification"]["disposition"], "NOT_RUN")
            self.assertEqual(receipt["request"]["text"], "Y as Yacht")
            self.assertEqual(receipt["generation_parameters"]["synthesis_text"], "why as Yacht")
            self.assertTrue(result.output_path.is_file())

    def test_waiver_is_rejected_for_wrong_scope_or_missing_authorization(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            provider = NativeFixture(root)
            profile = VoiceProfile("leo", "greia.leo", "cloned_reference", "fixture")
            engine = VoiceEngine(repo, SimpleNamespace(registry_version="fixture", get=lambda name: profile,
                                                       verify_anchor=lambda value: None), [provider],
                                 verifier=ForbiddenVerifier(), generation_lock=NullGenerationLock())
            base = dict(speaker="leo", locale="en", text="Y as Yacht", spoken_text="why as Yacht",
                        output=root / "published.wav", verification=VerificationMode.OFF,
                        max_attempts=1, short_text_mode="off")
            missing = engine.generate(VoiceRequest(kind=SpeechKind.CHARACTER_DIALOGUE, **base))
            wrong_kind = engine.generate(VoiceRequest(
                kind=SpeechKind.PEDAGOGICAL_SPEECH,
                owner_authorization=SYSTEM_TTS_WAIVER_AUTHORIZATION, **base))
            self.assertEqual(missing.disposition, GenerationDisposition.REJECTED)
            self.assertEqual(wrong_kind.disposition, GenerationDisposition.REJECTED)
            self.assertEqual(provider.calls, 0)

    def test_owner_authorized_route_prefers_native_over_character_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            profile = VoiceProfile("leo", "greia.leo", "cloned_reference", "fixture")
            registry = SimpleNamespace(registry_version="fixture", get=lambda name: profile,
                                       verify_anchor=lambda value: None)
            native = NativeFixture(root)

            class CharacterProvider(NativeFixture):
                provider_id = "voxstage-voxcpm2"
                def supports(self, request, voice_profile): return True
                def generate(self, request, voice_profile):
                    raise AssertionError("owner-waived route must not call cloned provider")

            character = CharacterProvider(root)
            engine = VoiceEngine(repo, registry, [character, native], verifier=ForbiddenVerifier(),
                                 generation_lock=NullGenerationLock())
            request = VoiceRequest(
                speaker="leo", kind=SpeechKind.CHARACTER_DIALOGUE, locale="en",
                text="Y as Yacht", spoken_text="why as Yacht", output=root / "published.wav",
                verification=VerificationMode.OFF, max_attempts=1, short_text_mode="off",
                owner_authorization=SYSTEM_TTS_WAIVER_AUTHORIZATION,
            )
            result = engine.generate(request)
            self.assertEqual(result.disposition, GenerationDisposition.OWNER_WAIVED)
            self.assertEqual(native.calls, 1)
            self.assertEqual(character.calls, 0)


if __name__ == "__main__":
    unittest.main()
