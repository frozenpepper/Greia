"""Provider-free source and catalogue contract for staged Activity runtime text.

This complements (but cannot replace) live four-locale Pygame rendering.
No imports from the Activities are required: their imports pull in Pygame.
"""

from __future__ import annotations

import ast
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
    def test_labyrinth_visible_controls_and_completion_are_localized(self) -> None:
        difficulties = _items_from_module(MAZE / "maze_model.py", "DIFFICULTIES")
        biomes = _items_from_module(MAZE / "maze_model.py", "BIOMES")
        required = {
            "btn.new_maze_short", "btn.play_again", "victory.title", "victory.subtitle"
        }
        required.update(f"difficulty.{item['id']}" for item in difficulties)
        required.update(f"biome.{item['id']}" for item in biomes)
        for language in LANGUAGES:
            with self.subTest(language=language):
                translations = _strings(MAZE, language)
                self.assertFalse(required.difference(translations))
                self.assertTrue(all(translations[key].strip() for key in required))

    def test_labyrinth_renderer_consumes_ui_locale_not_italian_model_fields(self) -> None:
        app = (MAZE / "maze_app.py").read_text(encoding="utf-8")
        renderer = (MAZE / "maze_renderer.py").read_text(encoding="utf-8")
        compile(app, str(MAZE / "maze_app.py"), "exec")
        compile(renderer, str(MAZE / "maze_renderer.py"), "exec")
        self.assertIn('self.resources.text("victory.title")', app)
        self.assertIn('labels=self._hud_labels()', app)
        self.assertIn("class MazeHudLabels:", renderer)
        self.assertNotIn('diff["label_it"]', renderer)
        self.assertNotIn('biome["name_it"]', renderer)
        for old_copy in ("PORTALE RAGGIUNTO", "Tito ha trovato l'uscita magica",
                         "NUOVO LABIRINTO", 'self._render_text("NUOVO'):
            self.assertNotIn(old_copy, app + renderer)

    def test_memory_card_names_and_theme_labels_cover_all_four_languages(self) -> None:
        themes = _items_from_module(MEMORY / "memory_content.py", "THEMES")
        card_ids = [item["id"] for theme in themes for item in theme["items"]]
        self.assertEqual(64, len(card_ids))
        self.assertEqual(64, len(set(card_ids)))
        required = {f"item.{item_id}" for item_id in card_ids}
        required.update(f"theme.{theme['id']}" for theme in themes)
        for language in LANGUAGES:
            with self.subTest(language=language):
                strings = _strings(MEMORY, language)
                self.assertFalse(required.difference(strings))
                self.assertTrue(all(strings[key].strip() for key in required))

    def test_memory_live_card_and_theme_display_uses_semantic_keys(self) -> None:
        app = (MEMORY / "memory_app.py").read_text(encoding="utf-8")
        compile(app, str(MEMORY / "memory_app.py"), "exec")
        self.assertIn('self.resources.text(f"item.{item[\'id\']}")', app)
        self.assertIn('self.resources.text(f"theme.{theme_cfg[\'id\']}")', app)
        self.assertNotIn('item["label_it"]', app)
        self.assertNotIn('item["label_en"]', app)
        self.assertNotIn('theme_cfg["name_it"]', app)
        self.assertNotIn('theme_cfg["name_en"]', app)

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




    def test_magic_syllables_live_guidance_and_phonics_formula(self) -> None:
        from string import Template

        activity = ROOT / "activities/sillabe_magiche"
        required = {
            "ui.explorer.formula", "ui.explorer.instruction",
            "ui.catcher.listen", "ui.builder.first_syllable",
            "ui.builder.second_syllable",
        }
        for language in LANGUAGES:
            with self.subTest(language=language):
                strings = _strings(activity, language)
                self.assertFalse(required.difference(strings))
                self.assertTrue(all(strings[key].strip() for key in required))
                # The authored template must be compatible with Greia's
                # real string.Template substitution, NOT Python .format().
                result = Template(strings["ui.explorer.formula"]).substitute(
                    consonant="M", syllables="MA · MÉ · MI · MO · MU"
                )
                self.assertIn("MÉ", result)
                self.assertIn("M", result)

        app = (activity / "sillabe_app.py").read_text(encoding="utf-8")
        compile(app, str(activity / "sillabe_app.py"), "exec")
        self.assertIn("self._session.explorer_syllables()", app)
        self.assertIn("self._explorer_formula = self._make_explorer_formula()", app)
        for obsolete in (
            "Fabbrica delle Sillabe:", "Tocca ogni tessera per ascoltare",
            "Ascolta e tocca:", "1° Sillaba", "2° Sillaba",
        ):
            self.assertNotIn(obsolete, app)

    def test_greenhouse_toolbar_consumes_semantic_locale_keys(self) -> None:
        activity = ROOT / "activities/piccola_serra"
        tools = _items_from_module(activity / "serra_content.py", "TOOL_DEFS")
        keys = {row[2] for row in tools}
        self.assertEqual(
            {"tool.seeds", "tool.water", "tool.sun", "tool.harvest"}, keys
        )
        for language in LANGUAGES:
            with self.subTest(language=language):
                labels = _strings(activity, language)
                self.assertTrue(all(labels.get(key, "").strip() for key in keys))
                self.assertTrue(all(
                    labels.get(key, "").strip()
                    for key in ("victory.title", "victory.subtitle", "btn.play_again")
                ))
        renderer = (activity / "serra_renderer.py").read_text(encoding="utf-8")
        app = (activity / "serra_app.py").read_text(encoding="utf-8")
        compile(renderer, str(activity / "serra_renderer.py"), "exec")
        compile(app, str(activity / "serra_app.py"), "exec")
        self.assertIn("self._tool_labels.get(label_key", renderer)
        self.assertIn("tool_labels={", app)
        self.assertIn("for _, _, key, _ in TOOL_DEFS", app)
        for wrong_language in ("Che magnifico raccolto", "La tua serra è un vero paradiso",
                               "Coltiva Ancora!"):
            self.assertNotIn(wrong_language, app)

    def test_victory_localization_uses_actual_platform_text_api(self) -> None:
        api = (ROOT / "src/greia_platform/localization.py").read_text(encoding="utf-8")
        self.assertIn("    def text(", api)
        self.assertNotIn("    def string(", api)
        for relative_path in (
            "activities/memory_meraviglie/main.py",
            "activities/treno_numeri/treno_app.py",
            "activities/piccola_serra/serra_app.py",
        ):
            with self.subTest(path=relative_path):
                source = (ROOT / relative_path).read_text(encoding="utf-8")
                compile(source, str(ROOT / relative_path), "exec")
                self.assertNotIn("resources.string(", source)
                self.assertIn("resources.text(", source)


if __name__ == "__main__":
    unittest.main()
