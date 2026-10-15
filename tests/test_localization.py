from __future__ import annotations

import contextlib
import json
import tempfile
import unittest
from pathlib import Path

from greia_platform.child_text import ChildTextCase, set_child_text_case
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocaleTag,
    LocalizationBundle,
    LocalizationError,
    LocalizedResources,
    TextDirection,
    resolve_activity_locale,
)


@contextlib.contextmanager
def _child_text_case(case: ChildTextCase):
    """Pin the process child-text policy for one test scope."""

    set_child_text_case(case)
    try:
        yield
    finally:
        set_child_text_case(None)


class LocaleTagTests(unittest.TestCase):
    def test_locale_tag_canonicalizes_language_script_region(self) -> None:
        self.assertEqual(LocaleTag.parse("it-it").value, "it-IT")
        self.assertEqual(LocaleTag.parse("zh-hant-tw").value, "zh-Hant-TW")
        self.assertEqual(LocaleTag.parse("en").value, "en")

    def test_locale_tag_fallback_chain_is_specific_to_general(self) -> None:
        locale = LocaleTag.parse("zh-Hant-TW")
        self.assertEqual(
            tuple(item.value for item in locale.fallback_chain()),
            ("zh-Hant-TW", "zh-Hant", "zh"),
        )

    def test_malformed_or_underscore_locale_is_rejected(self) -> None:
        for value in ("", "i", "it_IT", "it--IT", "123", "en-a"):
            with self.subTest(value=value):
                with self.assertRaises(LocalizationError):
                    LocaleTag.parse(value)


class ActivityLocaleResolutionTests(unittest.TestCase):
    def test_profile_locale_prefers_exact_then_language_fallback(self) -> None:
        support = ActivityLocaleSupport.localized(
            ("en", "it", "it-IT"),
            default_ui_locale="en",
        )
        exact = resolve_activity_locale("it-IT", support)
        assert exact is not None
        self.assertEqual(exact.selected.value, "it-IT")

        generic = resolve_activity_locale("it-CH", support)
        assert generic is not None
        self.assertEqual(generic.selected.value, "it")

    def test_activity_default_is_used_when_profile_locale_is_unsupported(self) -> None:
        support = ActivityLocaleSupport.localized(
            ("en", "it"),
            default_ui_locale="en",
        )
        context = resolve_activity_locale("fr-FR", support)
        assert context is not None
        self.assertEqual(context.requested.value, "fr-FR")
        self.assertEqual(context.selected.value, "en")
        self.assertEqual(tuple(item.value for item in context.fallback_chain), ("en",))

    def test_language_neutral_activity_has_no_package_locale_context(self) -> None:
        self.assertIsNone(
            resolve_activity_locale("it-IT", ActivityLocaleSupport.neutral())
        )

    def test_direction_is_platform_supplied_by_language(self) -> None:
        support = ActivityLocaleSupport.localized(("ar", "en"), default_ui_locale="en")
        context = resolve_activity_locale(
            "ar",
            support,
            direction_by_language={"ar": TextDirection.RTL},
        )
        assert context is not None
        self.assertEqual(context.direction, TextDirection.RTL)

    def test_invalid_support_contract_is_rejected(self) -> None:
        with self.assertRaises(LocalizationError):
            ActivityLocaleSupport.localized(("en",), default_ui_locale="it")
        with self.assertRaises(LocalizationError):
            ActivityLocaleSupport(
                ui_locales=(LocaleTag.parse("en"),),
                default_ui_locale=LocaleTag.parse("en"),
                language_neutral=True,
            )


class LocalizationBundleTests(unittest.TestCase):
    def _write_bundle(
        self,
        root: Path,
        locale: str,
        *,
        strings: dict[str, str],
        audio: dict[str, object] | None = None,
        direction: str = "ltr",
    ) -> None:
        directory = root / "locales"
        directory.mkdir(exist_ok=True)
        payload = {
            "schema_version": 1,
            "locale": locale,
            "direction": direction,
            "strings": strings,
            "audio": audio or {},
        }
        (directory / f"{LocaleTag.parse(locale).value}.json").write_text(
            json.dumps(payload),
            encoding="utf-8",
        )

    def test_string_and_audio_lookup_falls_back_per_resource_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "audio").mkdir()
            (root / "audio" / "hello.ogg").write_bytes(b"OggS")
            self._write_bundle(
                root,
                "it",
                strings={"hello": "Ciao ${name}"},
            )
            self._write_bundle(
                root,
                "en",
                strings={
                    "hello": "Hello ${name}",
                    "only.default": "Default fallback",
                    "caption.hello": "Hello!",
                },
                audio={
                    "hello.voice": {
                        "path": "audio/hello.ogg",
                        "caption_key": "caption.hello",
                    }
                },
            )
            support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="en")
            context = resolve_activity_locale("it-IT", support)
            assert context is not None
            resources = LocalizedResources(root, context)

            # Greia's default child text policy presents display strings in
            # CAPITAL letters; the semantic lookup/fallback order is unchanged.
            with _child_text_case(ChildTextCase.NORMAL):
                self.assertEqual(resources.text("hello", {"name": "Gaia"}), "Ciao Gaia")
                self.assertEqual(resources.text("only.default"), "Default fallback")
            self.assertEqual(resources.text("hello", {"name": "Gaia"}), "CIAO GAIA")
            cue = resources.audio_cue("hello.voice")
            self.assertEqual(cue.path, root / "audio" / "hello.ogg")
            self.assertEqual(cue.caption_key, "caption.hello")

    def test_selected_only_audio_blocks_fallback_without_assuming_file_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "audio").mkdir()
            (root / "audio" / "italian.wav").write_bytes(b"RIFF")
            (root / "audio" / "english.wav").write_bytes(b"RIFF")
            self._write_bundle(
                root, "it", strings={"instruction": "Tocca qui"},
                audio={"voice.instruction": {
                    "path": "audio/italian.wav", "caption_key": "instruction",
                }},
            )
            self._write_bundle(root, "en", strings={"instruction": "Touch here"})
            support = ActivityLocaleSupport.localized(
                ("it", "en"), default_ui_locale="it",
            )
            context = resolve_activity_locale("en", support)
            assert context is not None
            resources = LocalizedResources(root, context)

            # English no longer falls back to Italian audio just because IT
            # is the package default. Every spoken cue uses English as its
            # compatibility language, not another unrelated language.
            self.assertIsNone(resources.audio_path("voice.instruction"))
            with self.assertRaisesRegex(LocalizationError, "missing localized audio cue"):
                resources.audio_cue("voice.instruction")
            with self.assertRaisesRegex(LocalizationError, "missing localized audio cue"):
                resources.audio_cue("voice.instruction", allow_fallback=False)

            # An explicit English audio mapping remains compatible even when
            # its canonical file is outside the new locale-folder layout.
            self._write_bundle(
                root, "en", strings={"instruction": "Touch here"},
                audio={"voice.instruction": {
                    "path": "audio/english.wav", "caption_key": "instruction",
                }},
            )
            resources = LocalizedResources(root, context)
            self.assertEqual(
                resources.audio_cue("voice.instruction", allow_fallback=False).path,
                root / "audio" / "english.wav",
            )
            self.assertEqual(
                resources.audio_cue("voice.instruction").path,
                root / "audio" / "english.wav",
            )

    def test_missing_placeholder_is_not_silently_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._write_bundle(root, "en", strings={"score": "Score: ${score}"})
            context = resolve_activity_locale(
                "en",
                ActivityLocaleSupport.localized(("en",), default_ui_locale="en"),
            )
            assert context is not None
            resources = LocalizedResources(root, context)
            with self.assertRaises(LocalizationError):
                resources.text("score")

    def test_audio_paths_are_bounded_to_portable_package_resources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            for value in ("../escape.ogg", "/absolute.ogg", "audio/voice.mp3"):
                with self.subTest(value=value):
                    self._write_bundle(
                        root,
                        "en",
                        strings={},
                        audio={"voice": {"path": value}},
                    )
                    with self.assertRaises(LocalizationError):
                        LocalizationBundle.load(root, LocaleTag.parse("en"))

    def test_bundle_locale_must_match_filename_and_direction_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            locales = root / "locales"
            locales.mkdir()
            (locales / "en.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "locale": "it",
                        "direction": "sideways",
                        "strings": {},
                        "audio": {},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(LocalizationError):
                LocalizationBundle.load(root, LocaleTag.parse("en"))


if __name__ == "__main__":
    unittest.main()
