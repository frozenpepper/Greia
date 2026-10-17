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
    shared_character_audio_path,
    shared_vocab_audio_path,
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
            root = Path(tmp).resolve()
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
            root = Path(tmp).resolve()
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
            root = Path(tmp).resolve()
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
            root = Path(tmp).resolve()
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

    def test_my_time_underscore_activity_title_uses_selected_locale_or_english(self) -> None:
        root = Path(__file__).resolve().parents[1] / "activity_incubator" / "tempo_di_greia"
        english = root / "locales" / "en" / "audio" / "activity_title.wav"
        italian = root / "locales" / "it" / "audio" / "activity_title.wav"
        self.assertTrue(english.is_file())
        self.assertTrue(italian.is_file())
        self.assertEqual(
            activity_resources(root, requested_locale="it").audio_path("activity.title"),
            italian,
        )
        self.assertEqual(
            activity_resources(root, requested_locale="en").audio_path("activity.title"),
            english,
        )

    def test_legacy_underscore_title_falls_back_to_english_without_italian_substitution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            for language in ("en", "it", "fr"):
                _bundle(root, language)
            en = _put(root, "locales/en/audio/activity_title.wav")
            _put(root, "locales/it/audio/activity_title.wav")
            self.assertEqual(_context(root, "fr").audio_path("activity.title"), en)

    def test_italian_only_legacy_alias_projects_alarm_to_fr_and_en(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
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
            root = Path(tmp).resolve()
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
            root = Path(tmp).resolve()
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
            root = Path(tmp).resolve()
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

    def test_real_owner_approved_translated_activity_clips_are_reachable(self) -> None:
        root = Path(__file__).resolve().parents[1]
        examples = (
            ("faccine_momo", "es", "happy", "assets/audio/es/happy.wav"),
            ("mondo_contrari", "es", "big", "assets/audio/es/big.wav"),
            ("quattro_stagioni", "es", "autumn", "assets/audio/es/autumn.wav"),
            ("festa_delle_rime", "es", "gato", "assets/audio/es/gato.wav"),
            ("officina_dei_suoni", "es", "barco", "assets/audio/es/barco.wav"),
            ("luci_di_momo", "fr", "correct_1", "assets/audio/fr/correct_1.wav"),
            ("il_giardino_dei_numeri", "fr", "count_1", "assets/audio/fr/count_1.wav"),
            ("bosco_numeri", "es", "ask_1", "assets/audio/es/ask_1.wav"),
            ("specchi_magici", "es", "correct_1", "assets/audio/es/correct_1.wav"),
            ("baia_delle_orche", "es", "tito_fact_breach", "assets/audio/es/tito_fact_breach.wav"),
        )
        for package, locale, stem, relative in examples:
            with self.subTest(package=package, locale=locale, stem=stem):
                package_root = root / "activities" / package
                expected = package_root / relative
                self.assertTrue(expected.is_file(), str(expected))
                resources = activity_resources(
                    package_root, requested_locale=locale,
                    supported_locales=("it", "en", "es", "fr"),
                )
                self.assertEqual(
                    resources.audio_path(stem, filename=f"{stem}.wav"),
                    expected,
                )

    def test_approved_shared_character_library_resolves_without_copies(self) -> None:
        root = Path(__file__).resolve().parents[1]
        expected = (
            root / "assets/audio/characters/shared/v0.2/flash/en/"
            "flash__en__celebrate.success__01.wav"
        )
        self.assertTrue(expected.is_file())
        self.assertEqual(
            shared_character_audio_path(root, "flash", "celebrate.success", "en-GB"),
            expected,
        )
        french = (
            root / "assets/audio/characters/shared/v0.2/flash/fr/"
            "flash__fr__celebrate.success__01.wav"
        )
        self.assertEqual(
            shared_character_audio_path(root, "flash", "celebrate.success", "fr"),
            french,
        )
        italian = (
            root / "assets/audio/characters/shared/v0.2/flash/it/"
            "flash__it__celebrate.success__01.wav"
        )
        self.assertTrue(italian.is_file())
        self.assertEqual(
            shared_character_audio_path(root, "flash", "celebrate.success", "it"),
            italian,
        )

    def test_shared_vocab_bank_resolves_with_locale_base_english_fallback(self) -> None:
        root = Path(__file__).resolve().parents[1]
        bank = root / "assets/audio/vocab/v1"
        self.assertEqual(shared_vocab_audio_path(root, "apple", "it"), bank / "it/apple.wav")
        self.assertEqual(shared_vocab_audio_path(root, "apple", "it-IT"), bank / "it/apple.wav")
        # Regional tags resolve to the base-language clip of the released bank.
        self.assertEqual(shared_vocab_audio_path(root, "lion", "it"), bank / "it/lion.wav")
        self.assertEqual(shared_vocab_audio_path(root, "apple", "es-ES"), bank / "es/apple.wav")
        self.assertEqual(shared_vocab_audio_path(root, "apple", "fr-CA"), bank / "fr/apple.wav")
        self.assertIsNone(shared_vocab_audio_path(root, "not_a_noun", "en"))
        for noun in ("apple", "pizza"):
            for locale in ("en", "it"):
                receipt = bank / locale / f"{noun}.wav.receipt.json"
                self.assertTrue(receipt.is_file(), receipt)

    def test_shared_vocab_bank_prefers_exact_locale_and_rejects_path_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            base = _put(root, "assets/audio/vocab/v1/pt/cat.wav")
            _put(root, "assets/audio/vocab/v1/en/cat.wav")
            exact = _put(root, "assets/audio/vocab/v1/pt-BR/cat.wav")
            self.assertEqual(shared_vocab_audio_path(root, "cat", "pt-BR"), exact)
            self.assertEqual(shared_vocab_audio_path(root, "cat", "pt-PT"), base)
            for bad in ("../cat", "a/b", "Cat", "cat.wav", "", "1cat", "x" * 49, "a-b"):
                with self.subTest(noun=bad), self.assertRaises(LocalizationError):
                    shared_vocab_audio_path(root, bad, "en")

    def test_shared_character_fallback_is_english_and_missing_is_optional(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            clip = _put(
                root,
                "assets/audio/characters/shared/v0.2/leo/en/"
                "leo__en__celebrate.success__01.wav",
            )
            _put(
                root,
                "assets/audio/characters/shared/v0.2/leo/it/"
                "leo__it__celebrate.success__01.wav",
            )
            self.assertEqual(
                shared_character_audio_path(root, "leo", "celebrate.success", "es-ES"),
                clip,
            )
            self.assertIsNone(
                shared_character_audio_path(root, "momo", "not.recorded", "fr")
            )

    def test_invalid_alias_filename_does_not_escape_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            for loc in ("it", "en", "es"):
                _bundle(root, loc)
            res = _context(root, "es")
            for name in ("../escape.wav", "/abs.wav", "other\\file.wav", "sound.mp3"):
                with self.subTest(name=name), self.assertRaises(LocalizationError):
                    res.audio_path("cue", filename=name)

    def test_english_text_fallback_precedes_default_italian(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _bundle(root, "en", strings={"intro": "Hello"})
            _bundle(root, "it", strings={"intro": "Ciao"})
            _bundle(root, "es", strings={})
            self.assertEqual(_context(root, "es").text("intro"), "HELLO")

    def test_manifest_factory_keeps_release_locale_separate_from_staging(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
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

    def test_regional_locale_uses_base_language_before_english(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _bundle(root, "es-MX", strings={"welcome": "Regional"})
            _bundle(root, "es", strings={"lesson": "Español"})
            _bundle(root, "en", strings={"lesson": "English"})
            _bundle(root, "it", strings={"lesson": "Italiano"})
            english = _put(root, "assets/audio/en/lesson.wav")
            spanish = _put(root, "assets/audio/es/lesson.wav")
            context = resolve_activity_locale(
                "es-MX",
                ActivityLocaleSupport.localized(
                    ("it", "en", "es", "es-MX"),
                    default_ui_locale="it",
                ),
            )
            assert context is not None
            resources = LocalizedResources(root, context)
            self.assertEqual(resources.text("lesson"), "ESPAÑOL")
            self.assertEqual(resources.audio_path("lesson"), spanish)
            self.assertEqual(resources.speech_paths()["lesson"], spanish)
            self.assertEqual(
                resources.audio_path("lesson", allow_fallback=False), spanish
            )
            spanish.unlink()
            self.assertEqual(resources.audio_path("lesson"), english)
            self.assertIsNone(
                resources.audio_path("lesson", allow_fallback=False)
            )

    def test_unmapped_audio_variant_prefers_variant_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _bundle(root, "en")
            _bundle(root, "it")
            default = _put(root, "assets/audio/en/welcome.wav")
            female = _put(root, "assets/audio/en/welcome.feminine.wav")
            resources = _context(root, "it")
            self.assertEqual(resources.audio_path("welcome"), default)
            self.assertEqual(
                resources.audio_path("welcome", variant="feminine"), female
            )

    def test_migrated_activity_factories_respect_real_manifest_languages(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        for name in (
            "foresta_parole", "sillabe_magiche",
            "festa_delle_rime", "officina_dei_suoni",
            "luci_di_momo", "il_giardino_dei_numeri",
            "specchi_magici", "mondo_contrari",
            "baia_delle_orche", "bosco_numeri",
            "quattro_amici", "faccine_momo", "quattro_stagioni",
        ):
            root = repo / "activities" / name
            with self.subTest(activity=name):
                english = activity_resources(root, requested_locale="en")
                self.assertEqual(english.context.selected.value, "en")
                french = activity_resources(root, requested_locale="fr")
                self.assertEqual(french.context.selected.value, "fr")
                spanish = activity_resources(root, requested_locale="es-MX")
                self.assertEqual(spanish.context.selected.value, "es")


if __name__ == "__main__":
    unittest.main()
