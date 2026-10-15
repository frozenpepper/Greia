"""Filename-first, English-fallback prerecorded localization without pygame."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizationError,
    LocalizedResources,
    activity_resources,
    resolve_activity_locale,
)


def _bundle(root: Path, language: str, audio: dict | None = None,
            strings: dict | None = None) -> None:
    d = root / "locales"
    d.mkdir(exist_ok=True)
    (d / f"{language}.json").write_text(json.dumps({
        "schema_version": 1, "locale": language, "direction": "ltr",
        "strings": strings or {}, "audio": audio or {},
    }), encoding="utf-8")


def _context(root: Path, locale: str, default: str = "it") -> LocalizedResources:
    support = ActivityLocaleSupport.localized(
        ("en", "it", "es", "fr"), default_ui_locale=default,
    )
    context = resolve_activity_locale(locale, support)
    assert context is not None
    return LocalizedResources(root, context)


def _put(root: Path, relative: str) -> Path:
    p = root / relative
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"RIFF")
    return p


class SharedLocalizedAudioPathTests(unittest.TestCase):
    def test_english_mapping_projects_to_existing_es_and_fr_filenames(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = _put(root, "assets/audio/en/animals/intro.ogg")
            spanish = _put(root, "assets/audio/es/animals/intro.ogg")
            french = _put(root, "assets/audio/fr/animals/intro.ogg")
            _bundle(root, "en", audio={
                "encyclopedia.animals.intro": {"path": "assets/audio/en/animals/intro.ogg"}
            })
            for loc in ("it", "es", "fr"):
                _bundle(root, loc)
            for loc, target in (("es", spanish), ("fr", french), ("en", original)):
                self.assertEqual(
                    _context(root, loc).audio_cue("encyclopedia.animals.intro").path,
                    target,
                )

    def test_existing_es_mapping_wins_before_english_projection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _put(root, "assets/audio/en/animals/intro.ogg")
            preferred = _put(root, "assets/audio/es/special.ogg")
            _put(root, "assets/audio/es/animals/intro.ogg")
            _bundle(root, "en", audio={
                "intro": {"path": "assets/audio/en/animals/intro.ogg"}
            })
            _bundle(root, "es", audio={
                "intro": {"path": "assets/audio/es/special.ogg"}
            })
            _bundle(root, "it")
            self.assertEqual(_context(root, "es").audio_path("intro"), preferred)

    def test_missing_es_uses_english_not_italian_and_can_opt_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            english = _put(root, "assets/audio/en/animals/intro.ogg")
            _put(root, "assets/audio/it/animals/intro.ogg")
            _bundle(root, "en", audio={
                "intro": {"path": "assets/audio/en/animals/intro.ogg"}
            })
            _bundle(root, "es")
            _bundle(root, "it")
            res = _context(root, "es", default="it")
            self.assertEqual(res.audio_path("intro"), english)
            self.assertIsNone(res.audio_path("intro", allow_fallback=False))
            self.assertIsNone(res.audio_path("not.recorded"))

    def test_dolphin_submarine_and_activity_title_legacy_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _put(root, "audio/en/sub_fact_whale_1.wav")
            submarine_fr = _put(root, "audio/fr/sub_fact_whale_1.wav")
            _put(root, "assets/audio/en/presenter-welcome.ogg")
            dolphin_es = _put(root, "assets/audio/es/presenter-welcome.ogg")
            _put(root, "locales/en/audio/activity-title.wav")
            title_fr = _put(root, "locales/fr/audio/activity-title.wav")
            _bundle(root, "en", audio={
                "voice.fact.whale.1": {"path": "audio/en/sub_fact_whale_1.wav"},
                "presenter.welcome.voice": {"path": "assets/audio/en/presenter-welcome.ogg"},
                "activity.title": {"path": "locales/en/audio/activity-title.wav"},
            })
            for loc in ("it", "es", "fr"):
                _bundle(root, loc)
            self.assertEqual(
                _context(root, "fr").audio_path("voice.fact.whale.1"), submarine_fr
            )
            self.assertEqual(
                _context(root, "es").audio_path("presenter.welcome.voice"), dolphin_es
            )
            self.assertEqual(_context(root, "fr").audio_path("activity.title"), title_fr)

    def test_italian_only_legacy_alias_projects_alarm_to_fr_and_en(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _bundle(root, "en")
            _bundle(root, "es")
            _bundle(root, "fr")
            _bundle(root, "it", audio={
                "voice.btn.alarm": {"path": "audio/it/sub_btn_alarm.wav"}
            })
            _put(root, "audio/it/sub_btn_alarm.wav")
            french = _put(root, "audio/fr/sub_btn_alarm.wav")
            english = _put(root, "audio/en/sub_btn_alarm.wav")
            self.assertEqual(
                _context(root, "fr").audio_path("voice.btn.alarm"), french
            )
            self.assertEqual(
                _context(root, "es").audio_path("voice.btn.alarm"), english
            )
            self.assertEqual(
                _context(root, "en").audio_path("voice.btn.alarm"), english
            )

    def test_conventional_names_work_without_json_audio_maps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _bundle(root, "en")
            _bundle(root, "it")
            _bundle(root, "es")
            phrase = _put(root, "assets/audio/es/presenter.welcome.wav")
            letter = _put(root, "assets/audio/en/letter_A.wav")
            title = _put(root, "locales/es/audio/activity-title.wav")
            res = _context(root, "es")
            self.assertEqual(res.audio_path("presenter.welcome"), phrase)
            self.assertEqual(res.audio_path("phonics.letter_a", filename="letter_A.wav"), letter)
            self.assertEqual(res.audio_path("activity.title"), title)
            self.assertIsNone(res.audio_path("missing"))

    def test_eager_speech_discovery_handles_two_legacy_directories_and_english(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for locale in ("en", "it", "es", "fr"):
                _bundle(root, locale)
            spanish = _put(root, "assets/audio/es/intro.wav")
            _put(root, "assets/audio/en/intro.wav")
            english = _put(root, "locales/en/audio/well_done.wav")
            uppercase = _put(root, "assets/audio/en/letter_A.wav")
            _put(root, "locales/es/audio/activity-title.wav")

            resolved = _context(root, "es").speech_paths()
            self.assertEqual(resolved["intro"], spanish)
            self.assertEqual(resolved["well_done"], english)
            self.assertEqual(resolved["letter_A"], uppercase)
            self.assertNotIn("missing.wav", resolved)

            # A missing ES title recording correctly uses English if present;
            # this fixture has only ES title, so no unrelated language wins.
            self.assertEqual(
                resolved["activity-title"],
                root / "locales" / "es" / "audio" / "activity-title.wav",
            )

    def test_legacy_locale_audio_directory_uses_english_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for loc in ("it", "en", "fr"):
                _bundle(root, loc)
            english = _put(root, "locales/en/audio/shape_circle.wav")
            _put(root, "locales/it/audio/shape_circle.wav")
            resources = _context(root, "fr")
            self.assertEqual(
                resources.audio_path("shape.circle", filename="shape_circle.wav"),
                english,
            )
            french = _put(root, "locales/fr/audio/shape_circle.wav")
            self.assertEqual(
                resources.audio_path("shape.circle", filename="shape_circle.wav"),
                french,
            )

    def test_invalid_alias_filename_does_not_escape_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for loc in ("it", "en", "es"):
                _bundle(root, loc)
            res = _context(root, "es")
            for name in ("../escape.wav", "/abs.wav", "other\\file.wav", "sound.mp3"):
                with self.subTest(name=name), self.assertRaises(LocalizationError):
                    res.audio_path("cue", filename=name)

    def test_english_text_fallback_precedes_default_italian(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _bundle(root, "en", strings={"intro": "Hello"})
            _bundle(root, "it", strings={"intro": "Ciao"})
            _bundle(root, "es", strings={})
            self.assertEqual(_context(root, "es").text("intro"), "HELLO")

    def test_manifest_factory_keeps_release_locale_separate_from_staging(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "activity.toml").write_text(
                '[activity]\nlanguages = ["it", "en"]\n', encoding="utf-8"
            )
            _bundle(root, "en", strings={"title": "English"})
            _bundle(root, "it", strings={"title": "Italiano"})
            _bundle(root, "fr", strings={"title": "Français"})
            installed = activity_resources(root, requested_locale="fr")
            self.assertEqual(installed.context.selected.value, "it")
            staged = activity_resources(
                root, requested_locale="fr",
                supported_locales=("it", "en", "fr"),
            )
            self.assertEqual(staged.context.selected.value, "fr")

    def test_real_committed_multilingual_narration_resolves_without_es_fr_audio_maps(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        cases = (
            ("enciclopedia_greia", "es", "encyclopedia.animals.intro",
             "assets/audio/es/animals/intro.ogg"),
            ("enciclopedia_greia", "fr", "encyclopedia.animals.intro",
             "assets/audio/fr/animals/intro.ogg"),
            ("viaggio_delfino", "es", "presenter.welcome.voice",
             "assets/audio/es/presenter-welcome.ogg"),
            ("viaggio_delfino", "fr", "presenter.welcome.voice",
             "assets/audio/fr/presenter-welcome.ogg"),
            ("sottomarino_giramondo", "es", "voice.fact.whale.1",
             "audio/es/sub_fact_whale_1.wav"),
            ("sottomarino_giramondo", "fr", "voice.fact.whale.1",
             "audio/fr/sub_fact_whale_1.wav"),
        )
        for activity, locale, key, relative in cases:
            with self.subTest(activity=activity, locale=locale, key=key):
                root = repository / "activities" / activity
                res = activity_resources(
                    root, requested_locale=locale,
                    supported_locales=("it", "en", "es", "fr"),
                )
                self.assertEqual(res.audio_path(key), root / relative)
                self.assertTrue((root / relative).is_file())


if __name__ == "__main__":
    unittest.main()
