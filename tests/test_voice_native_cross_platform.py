"""Provider wiring and host command construction; no real speech synthesis is run."""
from pathlib import Path
import base64
import sys
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from greia_voice_core.composition import build_providers
from greia_voice_core.models import SpeechKind, VoiceRequest
from greia_voice_core.providers import LinuxEspeakSpeechProvider, WindowsSapiSpeechProvider


class NativeCrossPlatformTests(unittest.TestCase):
    def test_registry_preserves_character_and_macos_waiver_route(self):
        ids = [provider.provider_id for provider in build_providers()]
        self.assertEqual(ids[1:], [
            "macos-native-say", "windows-native-sapi", "linux-espeak-ng",
            "native-system-unavailable",
        ])

    def test_doctor_accepts_native_only_host_even_without_asr(self):
        import greia_voice
        from greia_voice_core.models import ProviderStatus

        class FakeProvider:
            def __init__(self, provider_id, ready):
                self.status = ProviderStatus(provider_id, ready, "fixture")

            def probe(self):
                return self.status

        fake_registry = SimpleNamespace(registry_version="fixture", profiles={})
        fake_verifier = SimpleNamespace(
            verifier_id="parakeet-fixture", model_id="fixture", model_revision="fixture",
            probe=lambda: (False, "not installed"),
        )
        with patch.object(greia_voice.VoiceRegistry, "load", return_value=fake_registry), \
                patch.object(greia_voice, "build_providers", return_value=(
                    FakeProvider("voxstage-voxcpm2", False),
                    FakeProvider("linux-espeak-ng", True),
                )), \
                patch.object(greia_voice, "ChatterboxMLXProvider", return_value=FakeProvider("chatterbox", False)), \
                patch.object(greia_voice, "ParakeetVerifier", return_value=fake_verifier), \
                patch.object(greia_voice.AudioPipeline, "ffmpeg_available", return_value=True), \
                patch.object(greia_voice, "_print") as output:
            result = greia_voice.cmd_doctor(SimpleNamespace(character_provider=None))
        self.assertEqual(result, 0)
        report = output.call_args.args[0]
        self.assertFalse(report["character_production_ready"])
        self.assertTrue(report["native_pedagogical_production_ready"])
        self.assertTrue(report["production_ready"])
        self.assertFalse(report["verifier"]["available"])

    def test_linux_pedagogical_uses_espeak_stdin_not_shell(self):
        provider = LinuxEspeakSpeechProvider()
        request = VoiceRequest("pedagogical", SpeechKind.PEDAGOGICAL_SPEECH, "it", "ma")
        with patch("greia_voice_core.providers.sys.platform", "linux"), \
                patch("greia_voice_core.providers.shutil.which", return_value="/usr/bin/espeak-ng"), \
                patch("greia_voice_core.providers.subprocess.run") as run, \
                patch("greia_voice_core.providers.shutil.copy2") as copy:
            take = provider.generate(request, None)
            argv = run.call_args.args[0]
            self.assertEqual(argv[0], "espeak-ng")
            self.assertEqual(argv[-1], "--stdin")
            self.assertNotIn("ma", argv)
            self.assertEqual(run.call_args.kwargs["input"], "ma")
            self.assertEqual(take.provider_id, "linux-espeak-ng")
            copy.assert_called_once()
            Path(take.temporary_wav).unlink(missing_ok=True)

    def test_windows_powershell_encodes_text_as_data(self):
        provider = WindowsSapiSpeechProvider()
        request = VoiceRequest("pedagogical", SpeechKind.PEDAGOGICAL_SPEECH, "fr", "Bonjour';Exit")
        with patch("greia_voice_core.providers.sys.platform", "win32"), \
                patch("greia_voice_core.providers.shutil.which", return_value="powershell.exe"), \
                patch("greia_voice_core.providers.subprocess.run") as run, \
                patch("greia_voice_core.providers.shutil.copy2") as copy:
            run.return_value = Mock(stdout="Microsoft Hortense\n")
            take = provider.generate(request, None)
            argv = run.call_args.args[0]
            self.assertEqual(argv[1:4], ["-NoProfile", "-NonInteractive", "-EncodedCommand"])
            script = base64.b64decode(argv[-1]).decode("utf-16-le")
            self.assertNotIn(request.text, script)
            self.assertIn("FromBase64String", script)
            self.assertIn("fr-FR", script)
            self.assertEqual(take.generation_parameters["voice"], "Microsoft Hortense")
            copy.assert_called_once()
            Path(take.temporary_wav).unlink(missing_ok=True)

    def test_native_does_not_silently_replace_canonical_character_clone(self):
        request = VoiceRequest("leo", SpeechKind.CHARACTER_DIALOGUE, "en", "Hello!")
        for provider in (WindowsSapiSpeechProvider(), LinuxEspeakSpeechProvider()):
            self.assertFalse(provider.supports(request, None))


if __name__ == "__main__":
    unittest.main()
