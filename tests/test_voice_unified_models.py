"""No model downloads or live inference: cross-platform routing and identities."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from greia_voice_core.composition import build_providers, selected_character_provider
from greia_voice_core.models import SpeechKind, VoiceProfile, VoiceRequest
from greia_voice_core.voxcpm_provider import VoxCPM2TorchProvider
from greia_voice_core.onnx_parakeet_asr import OnnxParakeetTranscriber
from greia_voice_core.verification import ParakeetVerifier


class UnifiedModelTests(unittest.TestCase):
    def test_same_tts_provider_on_every_host(self):
        for host in ("win32", "darwin", "linux"):
            with self.subTest(host=host), patch("sys.platform", host):
                with patch.dict("os.environ", {"GREIA_VOICE_CHARACTER_PROVIDER": "voxcpm2"}):
                    self.assertEqual(selected_character_provider(), "voxcpm2")
                    self.assertIsInstance(build_providers()[0], VoxCPM2TorchProvider)

    def test_same_parakeet_verifier_on_every_host(self):
        verifier = ParakeetVerifier()
        self.assertEqual(verifier.model_id, "nvidia/parakeet-tdt-0.6b-v3")
        self.assertEqual(verifier.verifier_id, "onnx-asr-parakeet-tdt-v3")

    def test_renderer_uses_canonical_reference_instead_of_os_voice(self):
        provider = VoxCPM2TorchProvider()
        ref = VoiceProfile("leo", "greia.leo.v2", "cloned_reference", "reference")
        request = VoiceRequest("leo", SpeechKind.CHARACTER_DIALOGUE, "it", "Ciao!")
        self.assertTrue(provider.supports(request, ref))
        self.assertFalse(provider.supports(request, None))
        self.assertTrue(provider.supports(
            VoiceRequest("pedagogical", SpeechKind.PEDAGOGICAL_SPEECH, "it", "ma"), None))

    def test_asr_does_not_download_during_doctor_when_absent(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict("os.environ", {"GREIA_PARAKEET_MODEL_DIR": temp}):
                transcriber = OnnxParakeetTranscriber()
                ok, msg = transcriber.probe()
                self.assertFalse(ok)
                self.assertIn("absent", msg)

    def test_onnx_parakeet_uses_local_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "encoder.onnx").write_bytes(b"placeholder")
            calls = []
            class FakeAsr:
                def recognize(self, wav): return "Trova la lettera."
            fake_module = SimpleNamespace(load_model=lambda *args: (calls.append(args), FakeAsr())[1])
            with patch.dict("os.environ", {"GREIA_PARAKEET_MODEL_DIR": temp}), \
                 patch.dict(sys.modules, {"onnx_asr": fake_module}):
                item = OnnxParakeetTranscriber().transcribe(Path("dummy.wav"))
            self.assertEqual(item["text"], "Trova la lettera.")
            self.assertEqual(calls, [("nemo-parakeet-tdt-0.6b-v3", temp)])


if __name__ == "__main__":
    unittest.main()
