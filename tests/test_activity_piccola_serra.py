"""Tests for Piccola Serra (manifest, art, grow/order rules, saves, app loop)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import random
import re
import sys
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "piccola_serra"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

import tomllib  # noqa: E402

from serra_content import (  # noqa: E402
    CURE,
    MAX_LEVEL,
    PLANTS,
    PLANTS_BY_ID,
    PLANTS_PER_VISIT,
    RUNGS,
    STORAGE_KEY,
    SYMPTOM_STAGES,
    Care,
    Need,
    Stage,
    rung_for,
    sequence_stages,
)
from serra_model import (  # noqa: E402
    GrowCycle,
    Phase,
    Place,
    SequenceTask,
    SerraProgress,
    Verdict,
    Visit,
    plan_needs,
)
from serra_services import (  # noqa: E402
    SCHEMA_VERSION,
    GreiaSerraEvents,
    GreiaSerraProgress,
    progress_from_payload,
    progress_payload,
)

LOCALES = ("en", "it", "es", "fr")
FORBIDDEN_SVG = re.compile(
    r'<image|data:|<text|<tspan|<filter|fe[A-Z]|<mask|<pattern|<style|<script|foreignObject|<animate|'
    r'blend-mode|skew|href="[^#]|xlink:href="[^#]|sodipodi|inkscape:'
)


class _Storage:
    def __init__(self, value=None) -> None:
        self.values = {} if value is None else {STORAGE_KEY: value}

    def kv_get(self, key, default=None):
        return self.values.get(key, default)

    def kv_set(self, key, value) -> None:
        self.values[key] = json.loads(json.dumps(value))


class _Audio:
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.sounds: list[str] = []

    def say(self, cue: str) -> None:
        self.spoken.append(cue)

    def say_if_quiet(self, cue: str) -> None:
        self.spoken.append(cue)

    def then(self, cue: str) -> None:
        self.spoken.append(cue)

    def play(self, name: str) -> None:
        self.sounds.append(name)


class _Events:
    def __init__(self) -> None:
        self.seeds: list[tuple] = []
        self.plants: list[tuple] = []
        self.visits: list[tuple] = []

    def seed_planted(self, *args) -> None:
        self.seeds.append(args)

    def plant_finished(self, *args) -> None:
        self.plants.append(args)

    def visit_completed(self, *args) -> None:
        self.visits.append(args)


class ManifestLocaleAndArtTests(unittest.TestCase):
    def test_manifest_matches_the_greenhouse_science_loop(self) -> None:
        data = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(data["activity"]["id"], "org.greia.piccola-serra")
        self.assertEqual(data["activity"]["version"], "0.2.0")
        self.assertEqual(set(data["activity"]["languages"]), {"it", "en", "es", "fr"})  # four released languages (owner 2026-10-17)
        self.assertEqual(data["input"]["profile"], "hybrid")
        education = data["education"]
        self.assertEqual((education["recommended_age_min"], education["recommended_age_max"]), (4, 6))
        self.assertEqual((education["difficulty_min"], education["difficulty_max"]), (1, MAX_LEVEL))
        self.assertTrue(education["adaptive_difficulty"])
        self.assertIn("science", education["categories"])
        self.assertIn("sequencing", education["categories"])
        events = {event["id"]: event["kind"] for event in education["events"]}
        self.assertEqual(
            events,
            {
                "greenhouse.seed_planted": "milestone",
                "greenhouse.plant_grown": "milestone",
                "greenhouse.harvest_completed": "completion",
            },
        )
        self.assertEqual(data["storage"]["schema_version"], SCHEMA_VERSION)

    def test_four_locale_parity_without_emoji_or_tool_words(self) -> None:
        bundles = {
            locale: json.loads((ACTIVITY_ROOT / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
            for locale in LOCALES
        }
        keys = set(bundles["en"]["strings"])
        self.assertEqual(keys, {"activity.title", "victory.title", "btn.play_again"})
        for locale, bundle in bundles.items():
            with self.subTest(locale=locale):
                self.assertEqual(set(bundle["strings"]), keys)
                for value in bundle["strings"].values():
                    self.assertTrue(value.strip())
                    self.assertNotEqual(value, value.upper())  # ADR 0034 cases at render time
                    self.assertTrue(all(ord(ch) < 0x2000 for ch in value), value)
        self.assertEqual(bundles["es"]["audio"], {})
        self.assertEqual(bundles["fr"]["audio"], {})
        self.assertIn("activity.title", bundles["en"]["audio"])

    def test_every_stage_picture_symptom_variant_and_overlay_exists(self) -> None:
        runtime = ACTIVITY_ROOT / "assets" / "runtime"
        source = ACTIVITY_ROOT / "assets" / "source"
        for plant in PLANTS:
            for stage in plant.stages:
                variants = ["", "_droopy", "_leaning"] if stage in SYMPTOM_STAGES else [""]
                for suffix in variants:
                    name = f"plant_{plant.plant_id}_{stage.value}{suffix}"
                    with self.subTest(name=name):
                        self.assertTrue((runtime / f"{name}.png").is_file())
                        self.assertTrue((source / f"{name}.svg").is_file())
        for name in (
            "state_droopy", "state_puddle", "greenhouse", "sunbeam", "shade_cloth", "shade_roll",
            "pot_back", "pot_front", "watering_can", "seed_packet", "bean_pod",
        ):
            with self.subTest(name=name):
                self.assertTrue((runtime / f"{name}.png").is_file())
                self.assertTrue((source / f"{name}.svg").is_file())
        # Carrots are pulled before they flower: no carrot flower stage at all.
        self.assertNotIn(Stage.FLOWER, PLANTS_BY_ID["carrot"].stages)
        self.assertFalse((runtime / "plant_carrot_flower.png").exists())

    def test_svg_sources_follow_the_recipe_lint_and_budgets(self) -> None:
        for svg in sorted((ACTIVITY_ROOT / "assets" / "source").glob("*.svg")):
            text = svg.read_text(encoding="utf-8")
            with self.subTest(svg=svg.name):
                self.assertIsNone(FORBIDDEN_SVG.search(text))
                self.assertNotIn("#000000", text.upper())
                self.assertTrue(text.startswith('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 '))
                limit = 24_000 if svg.name == "greenhouse.svg" else 6_200
                self.assertLessEqual(len(text.encode("utf-8")), limit)

    def test_no_hidden_pointer_tool_bubble_emoji_or_private_cast(self) -> None:
        source = "\n".join(path.read_text(encoding="utf-8") for path in ACTIVITY_ROOT.glob("*.py"))
        self.assertNotIn("set_visible(False)", source)
        self.assertIn("pygame.mouse.set_visible(True)", (ACTIVITY_ROOT / "main.py").read_text(encoding="utf-8"))
        for retired in ("_draw_thought_bubble", "needed_tool", "🌱", "💧", "☀", "🧺", "TOOL_DEFS", "_synth_wav"):
            self.assertNotIn(retired, source)
        self.assertIn("CastFeedback(TITO", source)
        self.assertIn("CompletionScene(self.kit, character=TITO", source)
        self.assertIn("ControlTheme.for_accent(\"leaf\")", source)


class ContentAndRuleTests(unittest.TestCase):
    def test_every_need_has_one_care_and_rungs_offer_the_needed_cares(self) -> None:
        self.assertEqual(set(CURE), set(Need))
        self.assertEqual(len(set(CURE.values())), len(CURE))
        for rung in RUNGS:
            with self.subTest(level=rung.level):
                for need in (*rung.needs, Need.RIPE):
                    self.assertIn(CURE[need], rung.cares)
        self.assertNotIn(Need.SOGGY, rung_for(1).needs)
        self.assertNotIn(Care.WAIT, rung_for(1).cares)
        self.assertEqual([rung.cards for rung in RUNGS], [3, 4, 5])

    def test_sequences_start_with_the_seed_end_with_the_fruit_and_keep_cycle_order(self) -> None:
        for plant in PLANTS:
            for cards in (3, 4, 5):
                stages = sequence_stages(plant, cards)
                with self.subTest(plant=plant.plant_id, cards=cards):
                    self.assertEqual(stages[0], Stage.SEED)
                    self.assertEqual(stages[-1], Stage.FRUIT)
                    self.assertEqual(len(stages), min(cards, len(plant.stages)))
                    order = [plant.stages.index(stage) for stage in stages]
                    self.assertEqual(order, sorted(order))
        self.assertEqual(sequence_stages(PLANTS_BY_ID["carrot"], 5), PLANTS_BY_ID["carrot"].stages)

    def test_need_plans_are_honest_and_varied(self) -> None:
        for seed in range(40):
            for plant in PLANTS:
                for rung in RUNGS:
                    needs = plan_needs(plant, rung.needs, random.Random(seed))
                    with self.subTest(seed=seed, plant=plant.plant_id, level=rung.level):
                        self.assertEqual(len(needs), len(plant.stages))
                        self.assertIs(needs[0], Need.THIRSTY)  # a seed needs water to sprout
                        self.assertIs(needs[-1], Need.RIPE)
                        middle = needs[1:-1]
                        self.assertTrue(all(need in rung.needs for need in middle))
                        for left, right in zip(needs[:-1], needs[1:]):
                            self.assertIsNot(left, right)
                        if len(middle) >= len(rung.needs):
                            self.assertEqual(set(middle), set(rung.needs))

    def test_wrong_care_changes_nothing_and_the_right_one_grows_the_plant(self) -> None:
        cycle = GrowCycle(PLANTS_BY_ID["sunflower"], rung_for(2).needs, random.Random(1))
        grown = [cycle.stage]
        while cycle.need is not None:
            need = cycle.need
            stage = cycle.stage
            wrong = next(care for care in Care if care is not CURE[need])
            result = cycle.apply(wrong)
            self.assertIs(result.verdict, Verdict.NOT_YET)
            self.assertIs(cycle.stage, stage)
            self.assertIs(cycle.need, need)
            self.assertEqual(result.misses, 1)
            result = cycle.apply(CURE[need])
            if need is Need.RIPE:
                self.assertIs(result.verdict, Verdict.HARVESTED)
            else:
                self.assertIs(result.verdict, Verdict.GREW)
                self.assertIs(result.previous, stage)
                grown.append(cycle.stage)
        self.assertEqual(tuple(grown), PLANTS_BY_ID["sunflower"].stages)
        self.assertTrue(cycle.harvested)
        self.assertIs(cycle.apply(Care.WATER).verdict, Verdict.IGNORED)
        self.assertEqual(cycle.misses, len(PLANTS_BY_ID["sunflower"].stages))

    def test_cards_are_never_dealt_in_order_and_only_the_next_one_fits(self) -> None:
        stages = PLANTS_BY_ID["bean"].stages
        for seed in range(30):
            task = SequenceTask(stages, random.Random(seed))
            self.assertNotEqual(task.deck, stages)
            self.assertEqual(sorted(task.deck), sorted(stages))
        task = SequenceTask(stages[:3], random.Random(0))
        self.assertIs(task.place(Stage.YOUNG), Place.NOT_NEXT)
        self.assertEqual(task.slot_misses, 1)
        self.assertIs(task.place(Stage.SEED), Place.PLACED)
        self.assertIs(task.place(Stage.SEED), Place.IGNORED)
        self.assertIs(task.place(Stage.FRUIT), Place.IGNORED)  # not in this 3-card set
        self.assertIs(task.place(Stage.SPROUT), Place.PLACED)
        self.assertIs(task.place(Stage.YOUNG), Place.PLACED)
        self.assertTrue(task.complete)
        self.assertEqual(task.misses, 1)

    def test_a_visit_is_three_plants_and_the_rung_adapts(self) -> None:
        def play(progress: SerraProgress, misses: int) -> Visit:
            visit = Visit(progress, random.Random(5))
            for index in range(PLANTS_PER_VISIT):
                self.assertIs(visit.phase, Phase.CHOOSE)
                self.assertIsNone(visit.care(Care.WATER))
                visit.choose(PLANTS[index].plant_id)
                while visit.phase is Phase.GROW:
                    need = visit.cycle.need
                    if misses > visit.misses + visit.cycle.misses and need is not Need.RIPE:
                        wrong = next(care for care in visit.rung.cares if care is not CURE[need])
                        visit.care(wrong)
                    visit.care(CURE[need])
                self.assertIs(visit.phase, Phase.SEQUENCE)
                for stage in visit.sequence.order:
                    self.assertIs(visit.place(stage), Place.PLACED)
                summary = visit.finish_plant()
                self.assertEqual(summary.plant_id, PLANTS[index].plant_id)
            self.assertTrue(visit.complete)
            return visit

        progress = SerraProgress()
        visit = play(progress, 0)
        self.assertEqual(progress.level, 2)
        self.assertEqual(progress.harvests, PLANTS_PER_VISIT)
        self.assertEqual(progress.visits, 1)
        self.assertEqual(visit.harvested, [plant.plant_id for plant in PLANTS[:PLANTS_PER_VISIT]])
        play(progress, 0)
        play(progress, 0)
        self.assertEqual(progress.level, MAX_LEVEL)
        play(progress, 9)
        self.assertEqual(progress.level, MAX_LEVEL - 1)
        visit.restart()
        self.assertIs(visit.phase, Phase.CHOOSE)
        self.assertEqual(visit.rung.level, progress.level)

    def test_cares_outside_the_rung_are_not_offered(self) -> None:
        visit = Visit(SerraProgress(level=1), random.Random(2))
        visit.choose("carrot")
        self.assertIsNone(visit.care(Care.WAIT))
        self.assertEqual(visit.cycle.misses, 0)


class SaveTests(unittest.TestCase):
    def test_first_release_save_migrates_and_schema_two_round_trips(self) -> None:
        legacy = {"harvest_count": 4, "timestamp": 1_760_000_000.0}
        progress = GreiaSerraProgress(_Storage(legacy)).load()
        self.assertEqual((progress.level, progress.harvests, progress.visits), (1, 4, 0))
        progress.level = 3
        progress.plants = {"bean": 2, "unknown": 9}
        storage = _Storage()
        GreiaSerraProgress(storage).save(progress)
        saved = storage.values[STORAGE_KEY]
        self.assertEqual(saved["schema_version"], SCHEMA_VERSION)
        self.assertEqual(saved["plants"], {"bean": 2})
        again = progress_from_payload(saved)
        self.assertEqual((again.level, again.harvests, again.plants), (3, 4, {"bean": 2}))
        for junk in (None, [], "x", {"schema_version": 99, "level": 3}, {"schema_version": 2, "level": True}):
            with self.subTest(junk=junk):
                fresh = progress_from_payload(junk)
                self.assertEqual(fresh.level, 1)
        self.assertEqual(progress_payload(SerraProgress(level=9))["level"], MAX_LEVEL)

    def test_event_keys_are_scoped_per_visit_and_plant(self) -> None:
        from serra_model import PlantSummary

        with mock.patch("serra_services.emit_activity_event") as publish:
            events = GreiaSerraEvents()
            events.seed_planted("v1", 1, "bean")
            events.plant_finished("v1", 1, PlantSummary("bean", 2, 1, 0, 4))
            events.visit_completed("v1", 3, 2)
        ids = [call.args[0] for call in publish.call_args_list]
        keys = [call.kwargs["idempotency_key"] for call in publish.call_args_list]
        self.assertEqual(ids, ["greenhouse.seed_planted", "greenhouse.plant_grown", "greenhouse.harvest_completed"])
        self.assertEqual(len(set(keys)), 3)
        self.assertTrue(all(key.startswith("piccola-serra:v1") for key in keys))


class AppLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1024, 600))

    def _app(self, level: int = 1, size: tuple[int, int] = (1024, 600), seed: int = 3, storage=None, locale: str = "en"):
        from greia_platform.localization import activity_resources
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from serra_app import SerraActivity

        screen = pygame.display.set_mode(size)
        now = [500.0]
        storage = storage if storage is not None else _Storage()
        progress = GreiaSerraProgress(storage)
        loaded = progress.load()
        loaded.level = level
        app = SerraActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            visit=Visit(loaded, random.Random(seed)),
            typography=GreiaTypography(),
            resources=activity_resources(ACTIVITY_ROOT, requested_locale=locale),
            audio=_Audio(),
            progress=progress,
            events=_Events(),
            clock=lambda: now[0],
        )
        return app, now, storage

    @staticmethod
    def _advance(app, now, seconds: float, step: float = 1 / 20) -> None:
        for _ in range(max(1, int(seconds / step))):
            now[0] += step
            app.step()

    def _settle(self, app, now) -> None:
        for _ in range(200):
            if not app.busy and not app.timeline.busy and not app.motion.flights:
                return
            self._advance(app, now, 0.05)
        self.fail("the greenhouse never settled")

    def _tap(self, app, now, control_id: str) -> bool:
        self._settle(app, now)
        position = app.physical_center(control_id)
        self.assertIsNotNone(position, control_id)
        return app.tap(position)

    def _press_tile(self, app, now, control_id: str) -> bool:
        """Keyboard only: arrow focus to the tile, then Enter."""

        self._settle(app, now)
        layer = app.controls.layer
        if layer.focused_id != control_id:
            ids = list(app.controls.row_ids())
            for _ in range(len(ids) + 2):
                app.press(pygame.K_LEFT)
            for _ in range(len(ids) + 2):
                if layer.focused_id == control_id:
                    break
                app.press(pygame.K_RIGHT)
        self.assertEqual(layer.focused_id, control_id)
        return app.press(pygame.K_RETURN)

    def _play_plant(self, app, now, plant_id: str, act) -> None:
        self.assertIs(app.visit.phase, Phase.CHOOSE)
        self.assertTrue(act(app, now, f"seed.{plant_id}"))
        self._settle(app, now)
        while app.visit.phase is Phase.GROW:
            need = app.visit.cycle.need
            self.assertTrue(act(app, now, f"care.{CURE[need].value}"), need)
            self._settle(app, now)
            app.render()
        self.assertIs(app.visit.phase, Phase.SEQUENCE)
        sequence = app.visit.sequence
        while not sequence.complete:
            self.assertTrue(act(app, now, f"card.{sequence.expected.value}"))
            self._settle(app, now)
            app.render()
        self._advance(app, now, 2.5)

    def test_pointer_plays_a_whole_visit_to_the_completion_scene_and_replays(self) -> None:
        from serra_app import AppState

        for level in (1, 3):
            app, now, storage = self._app(level=level)
            first_visit = app._visit_id
            for index, plant in enumerate(PLANTS[:PLANTS_PER_VISIT]):
                self.assertEqual(app.controls.progress.current, index)
                self._play_plant(app, now, plant.plant_id, self._tap)
            self.assertIs(app.state, AppState.TERMINAL)
            self.assertEqual(len(app.events.seeds), PLANTS_PER_VISIT)
            self.assertEqual(len(app.events.plants), PLANTS_PER_VISIT)
            self.assertEqual(len(app.events.visits), 1)
            self.assertIn("complete", app.audio.spoken)
            self.assertIn("praise", app.audio.spoken)
            saved = storage.values[STORAGE_KEY]
            self.assertEqual((saved["harvests"], saved["visits"]), (PLANTS_PER_VISIT, 1))
            self.assertEqual(saved["level"], min(MAX_LEVEL, level + 1))
            app.render()
            self.assertTrue(app.tap(app.canvas.mapper.point(*app.completion.primary_rect.center)))
            self.assertIs(app.state, AppState.PLAYING)
            self.assertIs(app.visit.phase, Phase.CHOOSE)
            self.assertNotEqual(app._visit_id, first_visit)  # fresh idempotency scope
            self.assertEqual(app.view.basket, [])

    def test_keyboard_alone_plays_a_visit_and_enter_replays(self) -> None:
        from serra_app import AppState

        app, now, _ = self._app(level=2, seed=8)
        for plant in ("carrot", "strawberry", "bean"):
            self._play_plant(app, now, plant, self._press_tile)
        self.assertIs(app.state, AppState.TERMINAL)
        app.render()
        app.press(pygame.K_RETURN)
        self.assertIs(app.state, AppState.PLAYING)

    def test_no_tile_marks_the_right_care_and_the_plant_shows_its_need(self) -> None:
        from serra_art import overlay_for, variant_for

        app, now, _ = self._app(level=2, seed=4)
        self.assertEqual(app.audio.spoken[:2], ["start", "pick_seed"])
        self._tap(app, now, "seed.sunflower")
        self.assertEqual(app.audio.spoken[-1], "name.sunflower")  # the chosen plant's name
        self._settle(app, now)
        seen = set()
        lines = {Need.THIRSTY: "thirsty", Need.DARK: "needs_light", Need.SOGGY: "too_much_water", Need.RIPE: "ripe_pick"}
        while app.visit.phase is Phase.GROW:
            need = app.visit.cycle.need
            self.assertEqual(app.audio.spoken[-1], lines[need])  # Tito says what the plant needs
            seen.add(need)
            tiles = [app.controls.cares[care] for care in app.visit.rung.cares]
            states = {(tile.role, tile.selected, tile.enabled, tile.visible) for tile in tiles}
            self.assertEqual(len(states), 1, "every care tile looks the same")
            self.assertIsNone(app.motion.tool)
            plant = app.view.plant
            self.assertEqual(plant.variant, variant_for(plant.stage, need))
            self.assertEqual(overlay_for(plant.overlay), overlay_for(need))
            self.assertEqual(app.view.cloth.end, 1.0 if need is Need.DARK else 0.0)
            self._tap(app, now, f"care.{CURE[need].value}")
            self._settle(app, now)
        self.assertIn(Need.RIPE, seen)
        self.assertTrue({Need.THIRSTY, Need.DARK} <= seen)
        self._settle(app, now)
        self.assertIs(app.visit.phase, Phase.SEQUENCE)
        self.assertEqual(app.audio.spoken[-1], "what_comes_first")

    def test_a_care_that_does_not_help_thinks_then_demonstrates_then_shows_the_tool(self) -> None:
        app, now, _ = self._app(level=1, seed=2)
        self._tap(app, now, "seed.bean")
        self._settle(app, now)
        need = app.visit.cycle.need
        self.assertIs(need, Need.THIRSTY)
        stage = app.visit.cycle.stage
        self.assertTrue(self._tap(app, now, "care.sun"))
        self.assertIn("sun", app.audio.sounds)  # the sun is shown, honestly, already shining
        self._settle(app, now)
        self.assertEqual(app.cast.pose, "think")
        self.assertIn("retry", app.audio.spoken)
        self.assertEqual(app.motion.symptom[0], Need.THIRSTY)
        self.assertIsNone(app.motion.tool)
        self.assertIs(app.visit.cycle.stage, stage)
        self.assertTrue(self._tap(app, now, "care.harvest"))
        self._settle(app, now)
        self.assertEqual(app.motion.tool[0], "care.water")
        app.render()
        self.assertTrue(self._tap(app, now, "care.water"))
        self._settle(app, now)
        self.assertIsNot(app.visit.cycle.stage, stage)

    def test_a_card_out_of_order_thinks_and_later_the_next_card_glows(self) -> None:
        app, now, _ = self._app(level=1, seed=6)
        self._tap(app, now, "seed.carrot")
        self._settle(app, now)
        while app.visit.phase is Phase.GROW:
            self._tap(app, now, f"care.{CURE[app.visit.cycle.need].value}")
            self._settle(app, now)
        sequence = app.visit.sequence
        wrong = next(stage for stage in sequence.deck if stage is not sequence.expected)
        self.assertTrue(self._tap(app, now, f"card.{wrong.value}"))
        self.assertEqual(app.cast.pose, "think")
        self.assertEqual(sequence.placed, [])
        self.assertIsNone(app.motion.tool)
        self._tap(app, now, f"card.{wrong.value}")
        self.assertEqual(app.motion.tool[0], f"card.{sequence.expected.value}")
        self.assertTrue(self._tap(app, now, f"card.{sequence.expected.value}"))
        self._settle(app, now)
        self.assertEqual(app.view.placed, 1)
        self.assertFalse(app.controls.cards[Stage.SEED].visible)

    def test_idle_hints_are_graduated(self) -> None:
        app, now, _ = self._app(level=1, seed=1)
        self._tap(app, now, "seed.strawberry")
        self._settle(app, now)
        self._advance(app, now, 6.3)
        self.assertEqual(app.cast.pose, "point")
        self.assertIn("nudge", app.audio.spoken)
        self.assertIsNotNone(app.motion.symptom)
        self.assertIsNone(app.motion.tool)
        self._advance(app, now, 12.3)  # back-off: 6 s, then a further 12 s
        self.assertEqual(app.motion.tool[0], f"care.{CURE[app.visit.cycle.need].value}")

    def test_hint_button_points_first_then_shows_the_tool(self) -> None:
        app, now, _ = self._app(level=1, seed=1)
        self._tap(app, now, "seed.bean")
        self._settle(app, now)
        self.assertTrue(self._tap(app, now, "hint"))
        self.assertEqual(app.cast.pose, "point")
        self.assertIsNotNone(app.motion.symptom)
        self.assertIsNone(app.motion.tool)
        self.assertTrue(self._tap(app, now, "hint"))
        self.assertEqual(app.motion.tool[0], "care.water")

    def test_taps_in_the_protected_region_never_reach_the_greenhouse(self) -> None:
        from greia_platform.system_chrome import ActivitySystemChromeLayout

        app, now, _ = self._app()
        self._settle(app, now)
        protected = ActivitySystemChromeLayout.for_surface(1024, 600).protected_region
        self.assertFalse(app.tap((protected.x + 4, protected.y + 4)))
        self.assertIs(app.visit.phase, Phase.CHOOSE)

    def test_controls_stay_clear_of_protected_chrome_and_touchable_at_every_size(self) -> None:
        from greia_platform.activity_controls import ControlLayout

        for size in ((1024, 600), (800, 480), (480, 320), (1280, 800)):
            for phase in ("seeds", "cares", "cards"):
                app, now, _ = self._app(level=3, size=size)
                if phase == "cares":
                    self._tap(app, now, "seed.bean")
                elif phase == "cards":
                    app.controls.show_cards("bean", PLANTS_BY_ID["bean"].stages)
                with self.subTest(size=size, phase=phase):
                    layout = ControlLayout.for_canvas(app.canvas, size)
                    scale = app.canvas.mapper.transform.scale
                    for target in app.controls.layer.targets:
                        rect = target.rect
                        self.assertFalse(rect.colliderect(layout.protected), target.control_id)
                        self.assertTrue(pygame.Rect(0, 0, 1024, 600).contains(rect), target.control_id)
                        if target.focusable:
                            self.assertGreaterEqual(rect.height * scale, 40, target.control_id)
                    row = [app.controls.tile(cid).rect for cid in app.controls.row_ids()]
                    for left, right in zip(row, row[1:]):
                        self.assertLessEqual(left.right, right.left)
                    self.assertFalse(app.controls.board.colliderect(layout.protected))
                    app.render()

    def test_pointer_is_drawn_while_playing_and_on_completion(self) -> None:
        def drawn(target, position) -> bool:
            # draw_activity_pointer's default body colour, 8 px right of the hot spot.
            return tuple(target.get_at((position[0] + 8, position[1])))[:3] == (254, 202, 87)

        app, now, _ = self._app()
        with mock.patch("pygame.mouse.get_focused", return_value=True), mock.patch(
            "pygame.mouse.get_pos", return_value=(300, 200)
        ):
            app.render()
            app.canvas.present()
            self.assertTrue(drawn(app.canvas.target, (300, 200)))
        for plant in PLANTS[:PLANTS_PER_VISIT]:
            self._play_plant(app, now, plant.plant_id, self._tap)
        with mock.patch("pygame.mouse.get_focused", return_value=True), mock.patch(
            "pygame.mouse.get_pos", return_value=(640, 340)
        ):
            app.render()
            app.canvas.present()
            self.assertTrue(drawn(app.canvas.target, (640, 340)))

    def test_frames_are_blits_only_after_warm_up(self) -> None:
        app, now, _ = self._app(level=2, seed=5)
        self._tap(app, now, "seed.sunflower")
        self._settle(app, now)
        app._show_hint(2)  # pulsing cue + tool glows during the measured frames
        self._advance(app, now, 0.6)  # the tool glow starts half a second later
        app.render()
        built = app.kit.painter.build_count
        backdrop = app.art.backdrop(app.view.cloth.end == 0.0)
        prepared = len(app.art._scaled)
        for _ in range(40):
            self._advance(app, now, 1 / 20)
            app.render()
        self.assertEqual(app.kit.painter.build_count, built)
        self.assertIs(app.art.backdrop(app.view.cloth.end == 0.0), backdrop)
        self.assertEqual(len(app.art._scaled), prepared)
        self.assertLessEqual(len(app.motion.fx), 8)

    def test_resize_relayouts_without_losing_the_plant(self) -> None:
        app, now, _ = self._app()
        self._tap(app, now, "seed.carrot")
        self._settle(app, now)
        pygame.display.set_mode((800, 480))
        app.handle_event(pygame.event.Event(pygame.VIDEORESIZE, w=800, h=480, size=(800, 480)))
        self.assertEqual(app.view.plant.plant_id, "carrot")
        self.assertTrue(self._tap(app, now, f"care.{CURE[app.visit.cycle.need].value}"))

    def test_italian_completion_uses_localized_capitals(self) -> None:
        app, now, _ = self._app(level=1, locale="it")
        self.assertEqual(app._text("victory.title", "?"), "CHE BEL RACCOLTO!")
        self.assertEqual(app._text("btn.play_again", "?"), "ANCORA")


if __name__ == "__main__":
    unittest.main()
