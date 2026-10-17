"""Provider-free source and catalogue contract for staged Activity runtime text.

This complements (but cannot replace) live four-locale Pygame rendering.
No imports from the Activities are required: their imports pull in Pygame.
"""

from __future__ import annotations

import ast
import re
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAZE = ROOT / "activities" / "labirinto_magico"
MEMORY = ROOT / "activities" / "memory_meraviglie"
LANGUAGES = ("en", "it", "es", "fr")


def _items_from_module(path: Path, name: str) -> list[dict]:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for statement in module.body:
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            if statement.target.id == name:
                return ast.literal_eval(statement.value)
    raise AssertionError(f"{name} not declared in {path}")


def _strings(activity: Path, locale: str) -> dict[str, str]:
    data = json.loads(
        (activity / "locales" / f"{locale}.json").read_text(encoding="utf-8")
    )
    assert data["locale"] == locale
    return data["strings"]


class FourLanguageRuntimeTextContract(unittest.TestCase):
    def test_labyrinth_is_pictorial_and_its_completion_is_localized(self) -> None:
        # The 2026-10-15 rework removed the text setting chips (EASY / GALAXY /
        # NEW): maze size adapts automatically and the HUD is pictorial, so the
        # only child-visible text is the shared completion scene.
        required = {"activity.title", "victory.title", "btn.play_again"}
        for language in LANGUAGES:
            with self.subTest(language=language):
                translations = _strings(MAZE, language)
                self.assertFalse(required.difference(translations))
                self.assertTrue(all(translations[key].strip() for key in required))
        app = (MAZE / "maze_app.py").read_text(encoding="utf-8")
        compile(app, str(MAZE / "maze_app.py"), "exec")
        self.assertIn('self.resources.text("victory.title")', app)
        self.assertIn('self.resources.text("btn.play_again")', app)
        for old_copy in ("PORTALE RAGGIUNTO", "Tito ha trovato l'uscita magica",
                         "NUOVO LABIRINTO", "MazeHudLabels", 'diff["label_it"]',
                         'biome["name_it"]'):
            self.assertNotIn(old_copy, app)

    def test_memory_picture_names_and_completion_cover_all_four_languages(self) -> None:
        # The 2026-10-15 Wonder Match rework replaced the four text-chip themes
        # (64 items) with five picture-chosen sticker albums of 8 library
        # pictures; card faces carry no words, names are spoken.
        content = (MEMORY / "memory_content.py").read_text(encoding="utf-8")
        ids = re.findall(r'^\s+"([a-z_]+)": "(?:prop|creature)\.', content, re.MULTILINE)
        self.assertEqual(40, len(ids))
        self.assertEqual(40, len(set(ids)))
        required = {f"item.{item_id}" for item_id in ids}
        required.update({"victory.title", "victory.subtitle", "button.play_again", "button.albums"})
        for language in LANGUAGES:
            with self.subTest(language=language):
                strings = _strings(MEMORY, language)
                self.assertFalse(required.difference(strings))
                self.assertTrue(all(strings[key].strip() for key in required))

    def test_memory_completion_uses_semantic_keys(self) -> None:
        app = (MEMORY / "memory_app.py").read_text(encoding="utf-8")
        compile(app, str(MEMORY / "memory_app.py"), "exec")
        for key in ("victory.title", "victory.subtitle", "button.play_again", "button.albums"):
            self.assertIn(f'self._text("{key}"', app)
        for old_copy in ('item["label_it"]', 'theme_cfg["name_it"]', "label_en", "name_en"):
            self.assertNotIn(old_copy, app)

    def test_missing_resources_never_reintroduce_italian_completion_copy(self) -> None:
        """A resource failure must not produce Italian under another profile."""
        for relative_path, forbidden in (
            (
                "activities/memory_meraviglie/main.py",
                ("Ottimo lavoro! Coppie trovate", "Che memoria fantastica",
                 "Gioca Ancora!"),
            ),
            (
                "activities/treno_numeri/treno_app.py",
                ("Il treno è arrivato al capolinea", "Hai completato tutte le stazioni",
                 "Gioca Ancora!"),
            ),
        ):
            with self.subTest(path=relative_path):
                source = (ROOT / relative_path).read_text(encoding="utf-8")
                compile(source, str(ROOT / relative_path), "exec")
                for phrase in forbidden:
                    self.assertNotIn(phrase, source)




    def test_magic_syllables_train_text_is_localized_and_pictorial(self) -> None:
        # The free-play syllabary/catch/builder tabs (explorer formula, slot
        # labels) were retired by the 2026-10-15 rework into Leo's Syllable
        # Train: the game is spoken + pictorial; only the completion scene shows
        # localized text, and the taught syllables are the only letters drawn.
        activity = ROOT / "activities/sillabe_magiche"
        required = {"activity.title", "victory.title", "victory.subtitle", "button.play_again"}
        for language in LANGUAGES:
            with self.subTest(language=language):
                strings = _strings(activity, language)
                self.assertFalse(required.difference(strings))
                self.assertTrue(all(strings[key].strip() for key in required))

        app = (activity / "sillabe_app.py").read_text(encoding="utf-8")
        compile(app, str(activity / "sillabe_app.py"), "exec")
        self.assertIn('self.resources.text("victory.title")', app)
        for obsolete in (
            "Fabbrica delle Sillabe:", "Tocca ogni tessera per ascoltare",
            "Ascolta e tocca:", "1° Sillaba", "2° Sillaba", "Sillabario",
        ):
            self.assertNotIn(obsolete, app)

    def test_greenhouse_is_word_free_and_completion_text_is_localized(self) -> None:
        # The care tools, seed packets and stage cards are pictures only (pre-
        # readers read the plant); child-visible words are just the completion
        # title and replay label, resolved through the platform text API.
        activity = ROOT / "activities/piccola_serra"
        for language in LANGUAGES:
            with self.subTest(language=language):
                labels = _strings(activity, language)
                self.assertEqual(set(labels), {"activity.title", "victory.title", "btn.play_again"})
                self.assertTrue(all(value.strip() for value in labels.values()))
        app = (activity / "serra_app.py").read_text(encoding="utf-8")
        compile(app, str(activity / "serra_app.py"), "exec")
        self.assertIn('self._text("victory.title"', app)
        self.assertIn('self._text("btn.play_again"', app)
        for retired in ("tool.seeds", "tool.water", "tool.sun", "tool.harvest", "hud.harvest", "plant.sunflower"):
            self.assertNotIn(retired, app)
        for wrong_language in ("Che bel raccolto", "What a harvest", "Grow more"):
            self.assertNotIn(wrong_language, app)

    def test_victory_localization_uses_actual_platform_text_api(self) -> None:
        api = (ROOT / "src/greia_platform/localization.py").read_text(encoding="utf-8")
        self.assertIn("    def text(", api)
        self.assertNotIn("    def string(", api)
        for relative_path in (
            "activities/memory_meraviglie/memory_app.py",
            "activities/treno_numeri/treno_app.py",
            "activities/piccola_serra/serra_app.py",
        ):
            with self.subTest(path=relative_path):
                source = (ROOT / relative_path).read_text(encoding="utf-8")
                compile(source, str(ROOT / relative_path), "exec")
                self.assertNotIn("resources.string(", source)
                self.assertIn("resources.text(", source)


    def test_opposites_world_banners_and_toolbar_use_all_ten_locale_keys(self) -> None:
        import tomllib

        activity = ROOT / "activities/mondo_contrari"
        states = ("up", "down", "big", "small", "in", "out",
                  "open", "closed", "fast", "slow")
        manifest = tomllib.loads((activity / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest["activity"]["languages"]), {"it", "en", "es", "fr"})
        for language in LANGUAGES:
            with self.subTest(language=language):
                strings = _strings(activity, language)
                self.assertTrue(all(
                    strings.get(f"opposite.{state}", "").strip() for state in states
                ))
        # The tabbed toy became one guided loop: the concept word is spoken and
        # its localized caption ("opposite.<state>") appears after the child acts.
        source = (activity / "contrari_app.py").read_text(encoding="utf-8")
        model = (activity / "contrari_model.py").read_text(encoding="utf-8")
        main = (activity / "main.py").read_text(encoding="utf-8")
        compile(source, str(activity / "contrari_app.py"), "exec")
        compile(main, str(activity / "main.py"), "exec")
        self.assertIn("self.resources.text(pole.text_key)", source)
        self.assertIn('return f"opposite.{self.value}"', model)
        self.assertIn('self.resources.text("victory.title")', source)
        self.assertIn("resources=resources", main)
        self.assertIn('resources.text("activity.title")', main)
        for obsolete in ("SU!", "GIÙ!", "GRANDE!", "PICCOLO!",
                         "DENTRO!", "FUORI!", "APERTO!", "CHIUSO!",
                         "VELOCE!", "LENTO!", "CATEGORY_TITLES_EN"):
            self.assertNotIn(f'"{obsolete}"', source)


    def test_dolphin_journey_completion_has_locale_copy_and_neutral_failure_mode(self) -> None:
        from string import Template

        activity = ROOT / "activities/viaggio_delfino"
        for language in LANGUAGES:
            with self.subTest(language=language):
                strings = _strings(activity, language)
                for key in ("completion.title", "completion.replay", "completion.body"):
                    self.assertTrue(strings.get(key, "").strip())
                text = Template(strings["completion.body"]).substitute(count=7)
                self.assertIn("7", text)
        app = (activity / "delfino_app.py").read_text(encoding="utf-8")
        compile(app, str(activity / "delfino_app.py"), "exec")
        self.assertIn('self._text("completion.title")', app)
        self.assertIn('self._text("completion.replay")', app)
        self.assertNotIn('"BRAVO!"', app)
        self.assertNotIn('"ANCORA!"', app)


if __name__ == "__main__":
    unittest.main()
