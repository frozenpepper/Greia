"""Woodland Hide & Seek (Nascondino nel Bosco): rules, content, art, app loop.

Runs headlessly (SDL dummy drivers) against the real shared art catalogue,
with an injected clock, in-memory progress and recorded events, so no child
profile data, voices or windows are touched.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import random
import sys
import tomllib
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for entry in (PROJECT_ROOT, PROJECT_ROOT / "src"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import pygame

from activities.nascondino_bosco.woodland_app import AppState, WoodlandApp
from activities.nascondino_bosco.woodland_art import WoodlandArt
from activities.nascondino_bosco.woodland_audio import WoodlandAudio
from activities.nascondino_bosco.woodland_content import (
    FINDS_PER_ROUND,
    FRIEND_IDS,
    LEVELS,
    MAX_LEVEL,
    PROPS,
    REFERENCE_HEIGHT,
    REFERENCE_WIDTH,
    SEASONS,
    STORAGE_KEY,
    Relation,
)
from activities.nascondino_bosco.woodland_layout import (
    FRIEND_SLOT_SIZE,
    FRIEND_SLOTS,
    LILLI_HEIGHT,
    LILLI_MIDBOTTOM,
    MIN_TARGET,
    SpotGeometry,
)
from activities.nascondino_bosco.woodland_model import HideRound, Pick, adapt_level
from activities.nascondino_bosco.woodland_services import (
    SCHEMA_VERSION,
    GreiaWoodlandProgress,
    WoodlandProgress,
    parse_progress,
    progress_payload,
)
from greia_platform.activity_api import get_shared_visual_path
from greia_platform.localization import activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.system_chrome import ActivitySystemChromeLayout
from greia_platform.typography import GreiaTypography

ACTIVITY_DIR = PROJECT_ROOT / "activities" / "nascondino_bosco"
LOCALES = ("en", "it", "es", "fr")


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class MemoryProgress:
    def __init__(self, progress: WoodlandProgress | None = None) -> None:
        self.saved = progress or WoodlandProgress()

    def load(self) -> WoodlandProgress:
        return self.saved

    def save(self, progress: WoodlandProgress) -> None:
        self.saved = progress


class RecordedEvents:
    def __init__(self) -> None:
        self.found: list[dict] = []
        self.completed: list[dict] = []

    def friend_found(self, session_id: str, payload: dict) -> None:
        self.found.append(payload)

    def round_completed(self, session_id: str, payload: dict) -> None:
        self.completed.append(payload)


class FakeStorage:
    def __init__(self, value=None) -> None:
        self.values = {STORAGE_KEY: value} if value is not None else {}

    def kv_get(self, key):
        return self.values.get(key)

    def kv_set(self, key, value) -> None:
        self.values[key] = value


def _strings(locale: str) -> dict[str, str]:
    return json.loads((ACTIVITY_DIR / "locales" / f"{locale}.json").read_text(encoding="utf-8"))["strings"]


class ManifestAndLocaleTests(unittest.TestCase):
    def test_manifest_matches_the_gameplay(self) -> None:
        with (ACTIVITY_DIR / "activity.toml").open("rb") as handle:
            data = tomllib.load(handle)
        self.assertEqual(data["activity"]["id"], "org.greia.nascondino-bosco")
        self.assertEqual(data["activity"]["title_key"], "activity.nascondino_bosco.title")
        self.assertEqual(sorted(data["activity"]["languages"]), ["en", "it"])  # ES/FR stay staged
        self.assertEqual(data["input"]["profile"], "hybrid")
        education = data["education"]
        self.assertEqual((education["recommended_age_min"], education["recommended_age_max"]), (3, 5))
        self.assertTrue(education["adaptive_difficulty"])
        self.assertEqual(education["difficulty_max"], len(LEVELS))
        skills = {skill["id"] for skill in education["skills"]}
        self.assertIn("cognition.observation.visual_search", skills)
        self.assertIn("language.vocabulary.position_words", skills)
        events = {event["id"]: event["kind"] for event in education["events"]}
        self.assertEqual(events, {"woodland.animal_found": "milestone", "woodland.round_completed": "completion"})

    def test_four_locales_have_key_parity_and_every_content_key(self) -> None:
        english = _strings("en")
        required = {"activity.title", "victory.title", "victory.subtitle", "btn.play_again"}
        required |= {f"animal.{friend}" for friend in FRIEND_IDS}
        required |= {kind.place_key for kind in PROPS.values()}
        self.assertTrue(required <= set(english), required - set(english))
        for locale in LOCALES:
            with self.subTest(locale=locale):
                strings = _strings(locale)
                self.assertEqual(set(strings), set(english))
                self.assertTrue(all(value.strip() for value in strings.values()))

    def test_position_phrases_name_the_relation_they_teach(self) -> None:
        words = {Relation.BEHIND: "behind", Relation.UNDER: "under", Relation.IN: "in "}
        english = _strings("en")
        for kind in PROPS.values():
            with self.subTest(kind=kind.kind_id):
                self.assertIn(words[kind.relation], english[kind.place_key].lower())

    def test_text_is_capitalised_by_the_platform_case_policy(self) -> None:
        resources = activity_resources(ACTIVITY_DIR, requested_locale="it")
        self.assertEqual(resources.text("place.bush"), "DIETRO IL CESPUGLIO")


class ContentAndArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT))

    def test_every_art_reference_resolves(self) -> None:
        for friend in FRIEND_IDS:
            self.assertTrue(get_shared_visual_path(f"creature.woodland.{friend}").is_file(), friend)
        for kind in PROPS.values():
            if kind.asset_id is not None:
                self.assertTrue(get_shared_visual_path(kind.asset_id).is_file(), kind.asset_id)
            if kind.art_file is not None:
                self.assertTrue((ACTIVITY_DIR / "assets" / "runtime" / kind.art_file).is_file())
                source = ACTIVITY_DIR / "assets" / "source" / kind.art_file.replace(".png", ".svg")
                self.assertTrue(source.is_file(), source)
        for season in SEASONS:
            for layer in season.layers:
                self.assertTrue(get_shared_visual_path(layer).is_file(), layer)

    def test_private_svgs_follow_the_authoring_lint(self) -> None:
        forbidden = ("<image", "data:", "<text", "<filter", "<mask", "<pattern", "<style", "<script", "skew")
        for source in (ACTIVITY_DIR / "assets" / "source").glob("*.svg"):
            text = source.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, text, f"{source.name}: {token}")

    def test_hiding_places_are_grounded_big_and_clear_of_chrome_and_lilli(self) -> None:
        protected = ActivitySystemChromeLayout.for_surface(REFERENCE_WIDTH, REFERENCE_HEIGHT).protected_region
        chrome = pygame.Rect(protected.x, protected.y, protected.width, protected.height)
        # Lilli herself and the corner where found friends gather.
        lilli = pygame.Rect(0, 0, int(LILLI_HEIGHT * 0.9), LILLI_HEIGHT)
        lilli.midbottom = LILLI_MIDBOTTOM
        slots = [pygame.Rect(x - FRIEND_SLOT_SIZE // 2, y - FRIEND_SLOT_SIZE, FRIEND_SLOT_SIZE, FRIEND_SLOT_SIZE) for x, y in FRIEND_SLOTS]
        friends = slots[0].unionall(slots[1:])
        for season in SEASONS:
            self.assertEqual(len(season.anchors), max(level.spots for level in LEVELS))
            for anchor in season.anchors:
                with self.subTest(season=season.season_id, anchor=anchor):
                    geom = SpotGeometry.build(anchor)
                    self.assertGreaterEqual(geom.hit_rect.width, MIN_TARGET)
                    self.assertGreaterEqual(geom.hit_rect.height, MIN_TARGET)
                    self.assertGreaterEqual(anchor.y, 400)  # on the ground, not in the sky
                    self.assertGreater(geom.hit_rect.top, 90)  # below the request bar
                    self.assertFalse(geom.hit_rect.colliderect(chrome))
                    self.assertFalse(geom.hit_rect.colliderect(lilli))
                    self.assertFalse(geom.hit_rect.colliderect(friends))
                    self.assertLess(geom.top_y, geom.cut_y + 1)

    def test_peek_geometry_hides_and_shows(self) -> None:
        geom = SpotGeometry.build(SEASONS[0].anchors[0])
        hidden = geom.peek_rect(0.2, 0.8, 0.0)
        shown = geom.peek_rect(0.2, 0.8, 1.0)
        self.assertGreater(hidden.top + int(0.2 * geom.friend_size), geom.cut_y)  # head below the clip line
        self.assertLess(shown.top + int(0.2 * geom.friend_size), geom.top_y)  # head above the place

    def test_backdrops_compose_through_the_scene_runtime_and_are_cached(self) -> None:
        art = WoodlandArt()
        for season in SEASONS:
            scene = season.scene()
            self.assertEqual([node.asset_id for node in scene.nodes], list(season.layers))
            backdrop = art.backdrop(season)
            self.assertEqual(backdrop.get_size(), (REFERENCE_WIDTH, REFERENCE_HEIGHT))
            self.assertIs(art.backdrop(season), backdrop)
            # Not the flat fallback: the sky and the ground differ.
            self.assertNotEqual(backdrop.get_at((512, 40))[:3], backdrop.get_at((512, 560))[:3])

    def test_props_and_friends_load_once_per_size(self) -> None:
        art = WoodlandArt()
        for kind in PROPS.values():
            image = art.prop(kind, (200, 100))
            if kind.asset_id is None and kind.art_file is None:
                self.assertIsNone(image)
            else:
                self.assertIsNotNone(image, kind.kind_id)
                self.assertIs(art.prop(kind, (200, 100)), image)
        for friend in FRIEND_IDS:
            self.assertIsNotNone(art.full(friend, 120))
            self.assertTrue(0.0 <= art.peek_top(friend) < 0.5)


class RulesTests(unittest.TestCase):
    def test_every_request_is_a_choice_and_found_friends_never_hide_again(self) -> None:
        for level in range(len(LEVELS)):
            for season in SEASONS:
                rng = random.Random(level * 11 + len(season.season_id))
                game = HideRound(season, level, rng)
                self.assertEqual(len(game.spots), LEVELS[level].spots)
                self.assertEqual(len(set(game.spots)), len(game.spots))
                while not game.complete:
                    hiders = [friend for friend in game.hiding if friend is not None]
                    self.assertEqual(len(hiders), len(game.spots))  # every place is a real option
                    self.assertIn(game.target, hiders)
                    self.assertFalse(set(hiders) & set(game.found))
                    outcome = game.choose(game.target_spot)
                    self.assertIs(outcome.pick, Pick.FOUND)
                    game.hide_again()
                self.assertEqual(len(game.found), FINDS_PER_ROUND)
                self.assertEqual(len(set(game.found)), FINDS_PER_ROUND)

    def test_wrong_place_is_a_kind_miss_and_a_found_place_cannot_count_twice(self) -> None:
        game = HideRound(SEASONS[0], 2, random.Random(4))
        wrong = next(i for i, friend in enumerate(game.hiding) if friend != game.target)
        outcome = game.choose(wrong)
        self.assertIs(outcome.pick, Pick.WRONG)
        self.assertEqual((game.misses, game.task_misses), (1, 1))
        spot = game.target_spot
        self.assertIs(game.choose(spot).pick, Pick.FOUND)
        self.assertIs(game.choose(spot).pick, Pick.IGNORED)
        self.assertEqual(len(game.found), 1)
        self.assertEqual(game.first_try_finds, 0)

    def test_requests_change_and_places_reshuffle(self) -> None:
        game = HideRound(SEASONS[1], 4, random.Random(9))
        layouts = set()
        previous = game.target
        for _ in range(3):
            game.choose(game.target_spot)
            game.hide_again()
            self.assertNotEqual(game.target, previous)
            previous = game.target
            layouts.add(tuple(game.hiding))
        self.assertGreater(len(layouts), 1)

    def test_ladder_adapts_from_misses(self) -> None:
        self.assertEqual(adapt_level(0, 0), 1)
        self.assertEqual(adapt_level(MAX_LEVEL, 1), MAX_LEVEL)
        self.assertEqual(adapt_level(2, 3), 2)
        self.assertEqual(adapt_level(2, 6), 1)
        self.assertEqual(adapt_level(0, 9), 0)
        spots = [level.spots for level in LEVELS]
        rises = [level.rise for level in LEVELS]
        self.assertEqual(spots, sorted(spots))
        self.assertEqual(rises, sorted(rises, reverse=True))


class ProgressTests(unittest.TestCase):
    def test_legacy_star_save_keeps_its_stars(self) -> None:
        progress = GreiaWoodlandProgress(FakeStorage({"stars": 1116})).load()
        self.assertEqual(progress, WoodlandProgress(stars=1116))

    def test_round_trip_and_corrupt_payloads(self) -> None:
        storage = FakeStorage()
        service = GreiaWoodlandProgress(storage)
        service.save(WoodlandProgress(level=3, season=2, stars=7, friends=("frog", "bear")))
        self.assertEqual(storage.values[STORAGE_KEY]["schema_version"], SCHEMA_VERSION)
        self.assertEqual(service.load(), WoodlandProgress(3, 2, 7, ("frog", "bear")))
        for raw in (None, [], "x", {"schema_version": SCHEMA_VERSION, "level": "9", "season": 99, "friends": "frog"}):
            parsed = parse_progress(raw)
            self.assertTrue(0 <= parsed.level <= MAX_LEVEL)
            self.assertTrue(0 <= parsed.season < len(SEASONS))
            self.assertEqual(parsed.friends, ())
        payload = progress_payload(WoodlandProgress(level=99, season=-3, stars=-1, friends=("frog", "dragon")))
        self.assertEqual((payload["level"], payload["season"], payload["stars"], payload["friends"]), (MAX_LEVEL, 0, 0, ["frog"]))


class AppLoopTests(unittest.TestCase):
    """Play real rounds through the shared kit input with an injected clock."""

    def setUp(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        self.clock = FakeClock()
        self.progress = MemoryProgress()
        self.events = RecordedEvents()
        resources = activity_resources(ACTIVITY_DIR, requested_locale="en")
        self.app = WoodlandApp(
            screen=self.screen,
            canvas=PygameReferenceCanvas(self.screen),
            typography=GreiaTypography(),
            resources=resources,
            audio=WoodlandAudio(locale="en"),
            progress=self.progress,
            events=self.events,
            rng=random.Random(21),
            clock=self.clock,
            session_prefix="test",
        )

    def advance(self, seconds: float, step: float = 0.05) -> None:
        end = self.clock.now + seconds
        while self.clock.now < end:
            self.clock.now += step
            self.app.step()

    def target_point(self) -> tuple[int, int]:
        return self.app.geometry[self.app.round.target_spot].hit_rect.center

    def test_round_plays_to_completion_with_feedback_and_restart(self) -> None:
        app = self.app
        self.advance(1.0)
        app.render()
        self.assertEqual(app.state, AppState.PLAYING)
        self.assertTrue(app.controls.banner_plain.visible or app.controls.banner_voiced.visible)
        # A miss: the friend there shows itself, Lilli thinks, the right place rustles.
        wrong = next(i for i, friend in enumerate(app.round.hiding) if friend != app.round.target)
        self.assertTrue(app.tap(app.geometry[wrong].hit_rect.center))
        self.assertEqual(app.cast.pose.value, "think")
        self.advance(0.7)
        self.assertGreater(app.motion.spots[app.round.target_spot].shake_start, self.clock.now - 0.2)
        self.assertEqual(app.round.misses, 1)
        for found in range(1, FINDS_PER_ROUND + 1):
            self.assertTrue(app.tap(self.target_point()))
            self.assertEqual(app.cast.pose.value, "cheer")
            self.assertEqual(app.controls.progress.current, found)
            app.render()
            self.advance(3.2)
        self.assertEqual(app.state, AppState.TERMINAL)
        self.assertEqual(len(self.events.found), FINDS_PER_ROUND)
        self.assertEqual(len(self.events.completed), 1)
        self.assertEqual(self.events.completed[0]["misses"], 1)
        self.assertEqual(self.progress.saved.stars, FINDS_PER_ROUND)
        self.assertEqual(self.progress.saved.level, 1)  # one miss -> climbs
        self.assertEqual(self.progress.saved.season, 1)  # next season
        self.assertEqual(len(self.progress.saved.friends), FINDS_PER_ROUND)
        app.render()
        # Replay from the shared completion scene starts the next season.
        self.assertTrue(app.tap(app.completion.primary_rect.center))
        self.assertEqual(app.state, AppState.PLAYING)
        self.assertEqual(app.round.season.season_id, SEASONS[1].season_id)
        self.assertEqual(app.controls.progress.current, 0)

    def test_keyboard_only_round(self) -> None:
        app = self.app
        self.advance(1.0)
        for _ in range(FINDS_PER_ROUND):
            target = f"spot.{app.round.target_spot}"
            for _ in range(12):
                if app.controls.layer.focused_id == target:
                    break
                for key in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_LEFT, pygame.K_UP):
                    app.press(key)
                    if app.controls.layer.focused_id == target:
                        break
            self.assertEqual(app.controls.layer.focused_id, target)
            self.assertTrue(app.press(pygame.K_RETURN))
            self.advance(3.2)
        self.assertEqual(app.state, AppState.TERMINAL)
        self.assertTrue(app.press(pygame.K_RETURN))
        self.assertEqual(app.state, AppState.PLAYING)

    def test_focus_never_jumps_to_the_answer_after_hiding_again(self) -> None:
        app = self.app
        self.advance(1.0)
        app.press(pygame.K_RIGHT)
        before = app.controls.layer.focused_id
        self.assertTrue(app.tap(self.target_point()))
        focused_after_find = app.controls.layer.focused_id
        self.advance(3.2)
        self.assertEqual(app.controls.layer.focused_id, focused_after_find)
        self.assertIsNotNone(before)

    def test_taps_in_the_protected_chrome_are_ignored(self) -> None:
        protected = ActivitySystemChromeLayout.for_surface(REFERENCE_WIDTH, REFERENCE_HEIGHT).protected_region
        self.advance(1.0)
        found = len(self.app.round.found)
        self.assertFalse(self.app.tap((protected.x + 4, protected.y + 4)))
        self.assertEqual(len(self.app.round.found), found)

    def test_idle_hint_points_and_glows(self) -> None:
        app = self.app
        self.advance(1.0)
        target = app.round.target_spot
        self.advance(6.3)
        self.assertTrue(app.cast.pointing)
        self.assertFalse(app.motion.glowing(target, self.clock.now))
        self.advance(12.3)  # back-off: 6 s, then a further 12 s
        self.assertTrue(app.motion.glowing(target, self.clock.now))

    def test_second_miss_demonstrates_with_a_glow(self) -> None:
        app = self.app
        self.advance(1.0)
        wrong = next(i for i, friend in enumerate(app.round.hiding) if friend != app.round.target)
        app.tap(app.geometry[wrong].hit_rect.center)
        self.advance(0.7)
        self.assertFalse(app.motion.glowing(app.round.target_spot, self.clock.now))
        app.tap(app.geometry[wrong].hit_rect.center)
        self.advance(0.7)
        self.assertTrue(app.motion.glowing(app.round.target_spot, self.clock.now))

    def test_frames_render_at_every_supported_size_without_per_frame_scaling(self) -> None:
        for size in ((1024, 600), (800, 480), (480, 320)):
            with self.subTest(size=size):
                screen = pygame.display.set_mode(size)
                self.app.screen = screen
                self.app._resize()
                self.advance(0.5)
                self.app.render()
                self.app.canvas.present()
                with mock.patch("pygame.transform.smoothscale", side_effect=AssertionError("per-frame scale")):
                    for _ in range(5):
                        self.clock.now += 0.04
                        self.app.step()
                        self.app.render()

    def test_found_friends_gather_by_lilli(self) -> None:
        self.assertEqual(len(FRIEND_SLOTS), FINDS_PER_ROUND)
        for slot in FRIEND_SLOTS:
            self.assertLess(slot[0], 300)


if __name__ == "__main__":
    unittest.main()
