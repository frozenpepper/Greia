"""Provider wiring and host command construction; no real speech synthesis is run."""
from pathlib import Path
import base64
import sys
import unittest
from unittest.mock import Mock, patch

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
