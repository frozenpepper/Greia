"""Offline integration tests for My Time's semantic locale audio boundary."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from greia_platform.localization import (
    ActivityLocaleSupport, LocalizedResources, resolve_activity_locale,
)
from activity_incubator.tempo_di_greia.time_audio import LocalTimeSpeechTransport


def _resources(root: Path, *, english_clip: bool) -> LocalizedResources:
    """Use real Greia bundles and fallback order, never a fake API contract."""
    (root / "locales").mkdir()
    voices = root / "assets" / "voices"
    voices.mkdir(parents=True)
    (voices / "italian.wav").write_bytes(b"RIFF Italian fixture")
    (voices / "english.wav").write_bytes(b"RIFF English fixture")
    for locale in ("it", "en"):
        audio = (
            {"instruction.clock": {
                "path": "assets/voices/italian.wav",
            }} if locale == "it" else
            {"instruction.clock": {
                "path": "assets/voices/english.wav",
            }} if english_clip else {}
        )
        (root / "locales" / f"{locale}.json").write_text(
            json.dumps({
                "schema_version": 1, "locale": locale,
                "strings": {}, "audio": audio,
            }),
            encoding="utf-8",
        )
    # A selected-English package may have Italian as its default fallback.
    support = ActivityLocaleSupport.localized(("en", "it"), default_ui_locale="it")
    context = resolve_activity_locale("en", support)
    assert context is not None
    return LocalizedResources(root, context)


class TimeAudioBoundaryTests(unittest.TestCase):
    def test_missing_english_cue_never_loads_italian_even_if_default_fallback(self) -> None:
        with TemporaryDirectory() as tmp:
            resources = _resources(Path(tmp).resolve(), english_clip=False)
            # English-only UI must not silently route speech to Italian.
            self.assertIsNone(resources.audio_path("instruction.clock"))
            with (
                patch("pygame.mixer.get_init", return_value=(22050, -16, 2)),
                patch("pygame.mixer.Channel"),
                patch("pygame.mixer.Sound") as sound,
            ):
                transport = LocalTimeSpeechTransport(resources)
                self.assertFalse(transport.has_clip("instruction.clock"))
                self.assertFalse(transport.play("instruction.clock"))
                sound.assert_not_called()

    def test_real_approved_my_time_wavs_resolve_from_semantic_cues(self) -> None:
        from activity_incubator.tempo_di_greia.time_speech import SPEECH_CUES

        root = Path(__file__).resolve().parents[1] / "activity_incubator" / "tempo_di_greia"
        for locale in ("en", "it"):
            with self.subTest(locale=locale):
                context = resolve_activity_locale(
                    locale,
                    ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it"),
                )
                assert context is not None
                resources = LocalizedResources(root, context)
                with (
                    patch("pygame.mixer.get_init", return_value=(22050, -16, 2)),
                    patch("pygame.mixer.Channel"),
                    patch("pygame.mixer.Sound") as sound,
                ):
                    transport = LocalTimeSpeechTransport(resources)
                    for cue in SPEECH_CUES:
                        self.assertTrue(
                            transport.has_clip(cue),
                            f"{locale} must resolve the approved file for {cue}",
                        )
                    sound.assert_not_called()

    def test_semantic_filename_falls_back_to_english_if_selected_locale_absent(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "locales").mkdir()
            for locale in ("it", "en", "fr"):
                (root / "locales" / f"{locale}.json").write_text(
                    json.dumps({
                        "schema_version": 1, "locale": locale,
                        "strings": {}, "audio": {},
                    }),
                    encoding="utf-8",
                )
            french_dir = root / "locales" / "fr" / "audio"
            french_dir.mkdir(parents=True)
            english_dir = root / "locales" / "en" / "audio"
            english_dir.mkdir(parents=True)
            (french_dir / "presenter_welcome.wav").write_bytes(b"FR")
            (english_dir / "instruction_clock.wav").write_bytes(b"EN")

            context = resolve_activity_locale(
                "fr",
                ActivityLocaleSupport.localized(
                    ("it", "en", "fr"), default_ui_locale="it"
                ),
            )
            assert context is not None
            with (
                patch("pygame.mixer.get_init", return_value=(22050, -16, 2)),
                patch("pygame.mixer.Channel"),
                patch("pygame.mixer.Sound") as sound,
            ):
                transport = LocalTimeSpeechTransport(LocalizedResources(root, context))
                self.assertTrue(transport.has_clip("presenter.welcome"))
                self.assertTrue(transport.has_clip("instruction.clock"))
                self.assertFalse(transport.has_clip("instruction.timer"))
                self.assertTrue(transport.play("instruction.clock"))
                sound.assert_called_once_with(str(english_dir / "instruction_clock.wav"))

    def test_selected_english_clip_can_live_in_any_safe_package_directory(self) -> None:
        with TemporaryDirectory() as tmp:
            resources = _resources(Path(tmp).resolve(), english_clip=True)
            with (
                patch("pygame.mixer.get_init", return_value=(22050, -16, 2)),
                patch("pygame.mixer.Channel") as channel,
                patch("pygame.mixer.Sound") as sound,
            ):
                sound.side_effect = lambda source: source
                transport = LocalTimeSpeechTransport(resources)
                # Indexing the locale bundle must not decode 7 possible clips
                # on the child's low-resource machine before the first frame.
                sound.assert_not_called()
                self.assertTrue(transport.has_clip("instruction.clock"))
                self.assertTrue(transport.play("instruction.clock"))
                self.assertTrue(transport.play("instruction.clock"))
                sound.assert_called_once_with(
                    str(resources.package_root / "assets" / "voices" / "english.wav")
                )
                self.assertEqual(channel.return_value.play.call_count, 2)

    def test_invalid_clip_fails_closed_without_redecoding(self) -> None:
        with TemporaryDirectory() as tmp:
            resources = _resources(Path(tmp).resolve(), english_clip=True)
            import pygame
            with (
                patch("pygame.mixer.get_init", return_value=(22050, -16, 2)),
                patch("pygame.mixer.Channel"),
                patch("pygame.mixer.Sound", side_effect=pygame.error("bad audio")) as sound,
            ):
                transport = LocalTimeSpeechTransport(resources)
                sound.assert_not_called()
                self.assertTrue(transport.has_clip("instruction.clock"))
                self.assertFalse(transport.play("instruction.clock"))
                self.assertFalse(transport.has_clip("instruction.clock"))
                self.assertFalse(transport.play("instruction.clock"))
                self.assertEqual(sound.call_count, 1)

    def test_audio_device_unavailable_is_silent_and_decodes_nothing(self) -> None:
        with TemporaryDirectory() as tmp:
            resources = _resources(Path(tmp).resolve(), english_clip=True)
            with (
                patch("pygame.mixer.get_init", return_value=None),
                patch("pygame.mixer.Sound") as sound,
            ):
                transport = LocalTimeSpeechTransport(resources)
                self.assertFalse(transport.has_clip("instruction.clock"))
                self.assertFalse(transport.play("instruction.clock"))
                self.assertFalse(transport.busy())
                transport.stop()
                sound.assert_not_called()


if __name__ == "__main__":
    unittest.main()
