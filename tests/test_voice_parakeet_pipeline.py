"""Pinned Parakeet adapter contract and strict target-negative controls."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "tools"))

from greia_voice_core.asr_policy import (
    DEFAULT_ASR_MODEL, DEFAULT_ASR_REVISION, DEFAULT_PARAKEET_MODEL,
    DEFAULT_PARAKEET_REVISION,
)
from greia_voice_core.number_comparison import PARAKEET_COMPARISON_POLICY
from greia_voice_core.models import SpeechKind, VerificationDisposition, VoiceRequest
from greia_voice_core.parakeet_asr import ParakeetTranscriber
from greia_voice_core.verification import ParakeetVerifier, WhisperVerifier

HAS_MLX_AUDIO = importlib.util.find_spec("mlx_audio") is not None


class ParakeetContractTests(unittest.TestCase):
    def test_default_metadata_does_not_relabel_historical_whisper_receipts(self):
        self.assertEqual(ParakeetTranscriber().model_id, DEFAULT_PARAKEET_MODEL)
        self.assertEqual(ParakeetTranscriber().model_revision, DEFAULT_PARAKEET_REVISION)
        self.assertEqual(WhisperVerifier().model_id, DEFAULT_ASR_MODEL)
        self.assertEqual(WhisperVerifier().verifier_id, "mlx-whisper-base")
        self.assertEqual(DEFAULT_ASR_REVISION, "1e3e249fb8d01c655324bd6841b1deadffd6d04c")

    @unittest.skipUnless(
        HAS_MLX_AUDIO,
        "optional mlx_audio voice-provider dependency is not installed",
    )
    def test_local_model_loader_uses_explicit_parakeet_architecture(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            with patch("greia_voice_core.parakeet_asr.cached_parakeet_model", return_value=path), \
                 patch("mlx_audio.stt.utils.load", return_value=object()) as load:
                self.assertIsNotNone(ParakeetTranscriber()._load())
            load.assert_called_once_with(str(path), model_type="parakeet")

    def test_adapter_preserves_real_token_timestamps_without_claiming_word_alignment(self):
        token = SimpleNamespace(text=" Luna", start=0.31, end=0.62)
        sentence = SimpleNamespace(tokens=[token])
        result = SimpleNamespace(text="Trouve Luna", sentences=[sentence])
        transcriber = ParakeetTranscriber()
        transcriber._model = SimpleNamespace(generate=lambda path: result)
        observation = transcriber.transcribe(Path("saved.wav"), "fr")
        self.assertEqual(observation["text"], "Trouve Luna")
        self.assertEqual(observation["segments"][0]["tokens"],
                         [{"text": " Luna", "start": 0.31, "end": 0.62}])
        self.assertNotIn("words", observation["segments"][0])

    def test_negative_number_and_extra_word_controls_fail_without_threshold_relaxation(self):
        class FixtureTranscriber:
            recognizer_id = "fixture-parakeet"
            model_id = DEFAULT_PARAKEET_MODEL
            model_revision = DEFAULT_PARAKEET_REVISION
            text = ""
            def transcribe(self, path, locale=None):
                return {"text": self.text, "model_id": self.model_id,
                        "model_revision": self.model_revision, "recognizer": self.recognizer_id}

        transcriber = FixtureTranscriber()
        verifier = ParakeetVerifier(transcriber=transcriber)
        request = VoiceRequest("tito", SpeechKind.CHARACTER_DIALOGUE, "en", "Count to ten")
        self.assertNotIn("comparison_policy", request.to_dict())
        with patch("greia_voice_core.review.signal_metrics", return_value=({}, [])):
            transcriber.text = "Count to nine"
            wrong_number = verifier.verify(request, Path("unused.wav"))
            self.assertEqual(wrong_number.disposition, VerificationDisposition.WARN)
            self.assertIn("TARGET_NUMBER_MISMATCH", wrong_number.flags)

            transcriber.text = "Count to ten ten"
            extra_word = verifier.verify(request, Path("unused.wav"))
            self.assertEqual(extra_word.disposition, VerificationDisposition.WARN)
            self.assertIn("TARGET_WORD_COUNT_MISMATCH", extra_word.flags)

            transcriber.text = "Count to ten"
            exact = verifier.verify(request, Path("unused.wav"))
            self.assertEqual(exact.disposition, VerificationDisposition.PASS)
            self.assertEqual(exact.comparison_policy, PARAKEET_COMPARISON_POLICY)

            oskar_request = VoiceRequest(
                "tito", SpeechKind.CHARACTER_DIALOGUE, "it", "Trova Oskar"
            )
            transcriber.text = "Trova Oscar."
            oskar = verifier.verify(oskar_request, Path("unused.wav"))
            self.assertEqual(oskar.disposition, VerificationDisposition.PASS)
            self.assertEqual(oskar.transcript, "Trova Oscar.")
            self.assertEqual(oskar_request.text, "Trova Oskar")
            self.assertEqual(oskar.comparison_policy, PARAKEET_COMPARISON_POLICY)

            historical_request = VoiceRequest(
                "tito", SpeechKind.CHARACTER_DIALOGUE, "it", "Trova Oskar",
                comparison_policy="locale-number-tokens-v2",
            )
            historical = verifier.verify(historical_request, Path("unused.wav"))
            self.assertEqual(historical.disposition, VerificationDisposition.WARN)
            self.assertEqual(historical.comparison_policy, "locale-number-tokens-v2")
            self.assertEqual(historical_request.to_dict()["comparison_policy"], "locale-number-tokens-v2")


if __name__ == "__main__":
    unittest.main()
