"""Offline checks for My Time's package-local prerecorded audio boundary."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from activity_incubator.tempo_di_greia.time_audio import LocalTimeSpeechTransport


class FakeResources:
    def __init__(self, root: Path, locale: str, source: Path) -> None:
        self.package_root = root
        self.context = SimpleNamespace(selected=SimpleNamespace(value=locale))
        self.source = source

    def audio_cue(self, cue: str):
        return SimpleNamespace(path=self.source)


class TimeAudioBoundaryTests(unittest.TestCase):
    def test_required_english_speech_must_not_use_italian_fallback(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            it_dir = root / "locales" / "it" / "audio"
            en_dir = root / "locales" / "en" / "audio"
            it_dir.mkdir(parents=True)
            en_dir.mkdir(parents=True)
            italian = it_dir / "instruction-clock.wav"
            english = en_dir / "instruction-clock.wav"
            italian.write_bytes(b"mock WAV loaded only through patched mixer")
            english.write_bytes(b"mock English WAV")
            with (
                patch("pygame.mixer.get_init", return_value=(22050, -16, 2)),
                patch("pygame.mixer.Channel") as channel,
                patch("pygame.mixer.Sound") as sound,
            ):
                sound.side_effect = lambda source: source
                wrong = LocalTimeSpeechTransport(FakeResources(root, "en", italian))
                self.assertFalse(wrong.has_clip("instruction.clock"))
                self.assertFalse(wrong.play("instruction.clock"))
                self.assertEqual(sound.call_count, 0)
                correct = LocalTimeSpeechTransport(FakeResources(root, "en", english))
                self.assertTrue(correct.has_clip("instruction.clock"))
                self.assertTrue(correct.play("instruction.clock"))
                self.assertGreaterEqual(channel.return_value.play.call_count, 1)

    def test_audio_device_unavailable_is_silent_and_does_not_decode(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch("pygame.mixer.get_init", return_value=None),
                patch("pygame.mixer.Sound") as sound,
            ):
                source = root / "locales" / "en" / "audio" / "instruction.wav"
                transport = LocalTimeSpeechTransport(FakeResources(root, "en", source))
                self.assertFalse(transport.has_clip("instruction.timer"))
                self.assertFalse(transport.play("instruction.timer"))
                self.assertFalse(transport.busy())
                transport.stop()
                sound.assert_not_called()


if __name__ == "__main__":
    unittest.main()
