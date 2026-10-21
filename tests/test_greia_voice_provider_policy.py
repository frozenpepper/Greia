from __future__ import annotations

import inspect
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from greia_voice_core.models import SpeechKind, VerificationDisposition, VoiceRequest
from greia_voice_core.providers import ChatterboxMLXProvider
from greia_voice_core.verification import WhisperVerifier
from record_shared_character_utterances import _result_counts_as_success


class ChatterboxProviderPolicyTests(unittest.TestCase):
    def test_character_speech_does_not_use_word_count_token_budget(self):
        self.assertFalse(hasattr(ChatterboxMLXProvider, "_token_budget"))
        source = inspect.getsource(ChatterboxMLXProvider.generate)
        self.assertNotIn("max_new_tokens", source)

    def test_short_speech_trim_does_not_stop_at_internal_gap(self):
        source = inspect.getsource(ChatterboxMLXProvider._trim_audio)
        self.assertNotIn("if int(idx) - end_frame > 12", source)
        self.assertNotIn("for idx in active[1:]", source)
        self.assertIn("end_frame = int(active[-1])", source)

    def test_shared_asr_warning_is_unresolved_production_work(self):
        self.assertTrue(_result_counts_as_success("REVIEW_REQUIRED"))
        self.assertTrue(_result_counts_as_success("EXISTING_REVIEW_CANDIDATE"))
        self.assertFalse(_result_counts_as_success("REVIEW_REQUIRED_ASR_WARNING"))
        self.assertFalse(_result_counts_as_success("REJECTED"))
        self.assertFalse(_result_counts_as_success("UNAVAILABLE"))
        self.assertFalse(_result_counts_as_success("BLOCKED_PARTIAL_OUTPUT"))


class WhisperMemoryPolicyTests(unittest.TestCase):
    def test_verifier_releases_mlx_transient_memory_before_and_after_transcription(self):
        fake_whisper = types.SimpleNamespace(
            transcribe=lambda *args, **kwargs: {"text": "Ottimo lavoro!"}
        )
        request = VoiceRequest(
            "leo",
            SpeechKind.CHARACTER_DIALOGUE,
            "it",
            "Ottimo lavoro!",
        )
        with patch.dict(sys.modules, {"mlx_whisper": fake_whisper}), patch(
            "greia_voice_core.verification.cached_asr_model", return_value=Path("/fake/cached-base")
        ):
            with patch(
                "greia_voice_core.verification._release_mlx_transient_memory"
            ) as cleanup:
                result = WhisperVerifier().verify(request, Path("unused.wav"))

        self.assertEqual(result.disposition, VerificationDisposition.PASS)
        self.assertEqual(cleanup.call_count, 2)


if __name__ == "__main__":
    unittest.main()
