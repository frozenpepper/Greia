from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizationError,
    LocalizedResources,
    resolve_activity_locale,
)


class LocalizationVariantTests(unittest.TestCase):
    @staticmethod
    def _bundle(
        root: Path,
        locale: str,
        *,
        strings: dict[str, str],
        audio: dict[str, object] | None = None,
    ) -> None:
        directory = root / "locales"
        directory.mkdir(exist_ok=True)
        (directory / f"{locale}.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "locale": locale,
                    "direction": "ltr",
                    "strings": strings,
                    "audio": audio or {},
                }
            ),
            encoding="utf-8",
        )

    def test_text_variant_prefers_gendered_key_then_same_locale_neutral_base(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self._bundle(
                root,
                "it",
                strings={
                    "feedback.correct": "Ottimo lavoro!",
                    "feedback.correct.masculine": "Bravo!",
                    "feedback.correct.feminine": "Brava!",
                },
            )
            context = resolve_activity_locale(
                "it",
                ActivityLocaleSupport.localized(("it",), default_ui_locale="it"),
            )
            assert context is not None
            resources = LocalizedResources(root, context)
            self.assertEqual(
                resources.text("feedback.correct", variant="masculine"),
                "Bravo!",
            )
            self.assertEqual(
                resources.text("feedback.correct", variant="feminine"),
                "Brava!",
            )
            self.assertEqual(
                resources.text("feedback.correct", variant="neutral"),
                "Ottimo lavoro!",
            )

    def test_locale_priority_beats_variant_priority_across_languages(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self._bundle(
                root,
                "it",
                strings={"feedback.correct": "Ottimo lavoro!"},
            )
            self._bundle(
                root,
                "en",
                strings={
                    "feedback.correct": "Great job!",
                    "feedback.correct.feminine": "English feminine variant",
                },
            )
            context = resolve_activity_locale(
                "it",
                ActivityLocaleSupport.localized(
                    ("it", "en"), default_ui_locale="en"
                ),
            )
            assert context is not None
            resources = LocalizedResources(root, context)
            self.assertEqual(
                resources.text("feedback.correct", variant="feminine"),
                "Ottimo lavoro!",
            )

    def test_audio_uses_same_semantic_variant_rule_as_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            audio_dir = root / "audio"
            audio_dir.mkdir()
            for name in ("neutral.ogg", "boy.ogg", "girl.ogg"):
                (audio_dir / name).write_bytes(b"OggS")
            self._bundle(
                root,
                "it",
                strings={},
                audio={
                    "feedback.correct": {"path": "audio/neutral.ogg"},
                    "feedback.correct.masculine": {"path": "audio/boy.ogg"},
                    "feedback.correct.feminine": {"path": "audio/girl.ogg"},
                },
            )
            context = resolve_activity_locale(
                "it",
                ActivityLocaleSupport.localized(("it",), default_ui_locale="it"),
            )
            assert context is not None
            resources = LocalizedResources(root, context)
            self.assertEqual(
                resources.audio_cue(
                    "feedback.correct", variant="feminine"
                ).path.name,
                "girl.ogg",
            )
            self.assertEqual(
                resources.audio_cue(
                    "feedback.correct", variant="neutral"
                ).path.name,
                "neutral.ogg",
            )

    def test_variant_id_is_bounded_and_semantic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self._bundle(root, "en", strings={"hello": "Hello"})
            context = resolve_activity_locale(
                "en",
                ActivityLocaleSupport.localized(("en",), default_ui_locale="en"),
            )
            assert context is not None
            resources = LocalizedResources(root, context)
            for value in ("Feminine", "bad.value", "", "../girl"):
                with self.subTest(value=value):
                    with self.assertRaises(LocalizationError):
                        resources.text("hello", variant=value)


if __name__ == "__main__":
    unittest.main()
