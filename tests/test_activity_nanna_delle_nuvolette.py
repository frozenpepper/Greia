"""Cloud Bedtime (Nanna delle Nuvolette): content, rules, art, services, app loop.

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

from activities.nanna_delle_nuvolette.cloud_app import DRAG_THRESHOLD_PX, AppState, CloudActivity
from activities.nanna_delle_nuvolette.cloud_art import CloudArt, DIM_ALPHAS
from activities.nanna_delle_nuvolette.cloud_audio import CloudAudio, LULLABY
from activities.nanna_delle_nuvolette.cloud_content import (
    BASIC_COLOURS,
    CLOUDS_PER_NIGHT,
    COLOURS,
    LEGACY_STORAGE_KEY,
    LEVELS,
    MAX_LEVEL,
    MAX_TRAY,
    STORAGE_KEY,
    Quilt,
    dice_points,
    plan_night,
)
from activities.nanna_delle_nuvolette.cloud_layout import (
    CLOUD_SIZE,
    TRAY_PANEL,
    bubble_box,
    cloud_box,
    cloud_hit,
    tile_rects,
)
from activities.nanna_delle_nuvolette.cloud_model import BedtimeNight, CloudState, Offer, adapt_level
from activities.nanna_delle_nuvolette.cloud_services import (
    EVENT_REST_COMPLETED,
    SCHEMA_VERSION,
    BedtimeProgress,
    GreiaBedtimeProgress,
    GreiaCloudEvents,
    parse_progress,
    progress_payload,
)
from greia_platform.localization import activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.system_chrome import ActivitySystemChromeLayout
from greia_platform.typography import GreiaTypography

ACTIVITY_DIR = PROJECT_ROOT / "activities" / "nanna_delle_nuvolette"
LOCALES = ("en", "it", "es", "fr")


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class MemoryProgress:
    def __init__(self, progress: BedtimeProgress | None = None) -> None:
        self.saved = progress or BedtimeProgress()
        self.saves = 0

    def load(self) -> BedtimeProgress:
        return self.saved

    def save(self, progress: BedtimeProgress) -> None:
        self.saved = progress
        self.saves += 1


class RecordedEvents:
    def __init__(self) -> None:
        self.completed: list[tuple[str, dict]] = []

    def rest_completed(self, session_id: str, payload: dict) -> None:
        self.completed.append((session_id, payload))


class FakeStorage:
    def __init__(self, values: dict | None = None) -> None:
        self.values = dict(values or {})

    def kv_get(self, key):
        return self.values.get(key)

    def kv_set(self, key, value) -> None:
        self.values[key] = value


# -- content ------------------------------------------------------------------------


class NightPlanTests(unittest.TestCase):
    def plans(self, level: int, count: int = 60):
        return [plan_night(level, random.Random(seed)) for seed in range(count)]

    def test_every_night_has_three_distinct_dreams_each_exactly_once_in_the_tray(self) -> None:
        for level in range(len(LEVELS)):
            for plan in self.plans(level):
                with self.subTest(level=level, plan=plan):
                    self.assertEqual(len(plan.dreams), CLOUDS_PER_NIGHT)
                    self.assertEqual(len(set(plan.dreams)), CLOUDS_PER_NIGHT)
                    self.assertEqual(len(set(plan.tray)), len(plan.tray), "no two identical quilts")
                    for dream in plan.dreams:
                        self.assertEqual(plan.tray.count(dream), 1)
                    self.assertEqual(len(plan.tray), CLOUDS_PER_NIGHT + LEVELS[level].extras)
                    self.assertLessEqual(len(plan.tray), MAX_TRAY)

    def test_colour_rungs_have_plain_quilts_and_distinct_colours(self) -> None:
        for level in (0, 1):
            for plan in self.plans(level):
                self.assertTrue(all(quilt.stars == 0 for quilt in plan.tray))
                self.assertEqual(len({dream.colour_id for dream in plan.dreams}), CLOUDS_PER_NIGHT)
                if level == 0:
                    self.assertTrue(all(quilt.colour_id in BASIC_COLOURS for quilt in plan.tray))

    def test_stars_only_rung_has_one_colour_so_only_the_number_counts(self) -> None:
        for plan in self.plans(2):
            self.assertEqual(len({quilt.colour_id for quilt in plan.tray}), 1)
            self.assertEqual(sorted(dream.stars for dream in plan.dreams), [1, 2, 3])

    def test_colour_and_star_rungs_always_need_the_number(self) -> None:
        for level in (3, 4):
            shared_seen = False
            for plan in self.plans(level):
                stars = [dream.stars for dream in plan.dreams]
                self.assertTrue(all(1 <= count <= LEVELS[level].max_stars for count in stars))
                colours = [dream.colour_id for dream in plan.dreams]
                shared_seen = shared_seen or len(set(colours)) < CLOUDS_PER_NIGHT
                extras = [quilt for quilt in plan.tray if quilt not in plan.dreams]
                # At least one extra wears a dreamed colour with another number.
                self.assertTrue(
                    any(any(e.colour_id == d.colour_id and e.stars != d.stars for d in plan.dreams) for e in extras),
                    plan,
                )
            self.assertEqual(shared_seen, LEVELS[level].shared_colours)

    def test_dream_stars_use_a_dice_face_not_a_row(self) -> None:
        for count in range(1, 6):
            points = dice_points(count)
            self.assertEqual(len(points), count)
            self.assertEqual(len(set(points)), count)
        self.assertGreater(len({y for _, y in dice_points(3)}), 1)

    def test_quilt_validation(self) -> None:
        with self.assertRaises(ValueError):
            Quilt("teal")
        with self.assertRaises(ValueError):
            Quilt("pink", 6)


# -- rules --------------------------------------------------------------------------


class BedtimeNightTests(unittest.TestCase):
    def night(self, level: int = 3, seed: int = 4) -> BedtimeNight:
        return BedtimeNight(level, plan_night(level, random.Random(seed)))

    def test_dreamed_quilt_is_kept_and_the_cloud_yawns(self) -> None:
        night = self.night()
        answer = night.answer_for(0)
        outcome = night.offer(answer, 0)
        self.assertIs(outcome.offer, Offer.RIGHT)
        self.assertIs(night.clouds[0].state, CloudState.YAWNING)
        self.assertIsNone(night.tray[answer])
        self.assertIsNone(night.answer_for(0))
        self.assertIs(night.offer(answer, 1).offer, Offer.IGNORED, "an empty slot gives nothing")
        self.assertTrue(night.fall_asleep(0))
        self.assertFalse(night.fall_asleep(0))
        self.assertEqual(night.asleep_count, 1)

    def test_other_quilt_is_declined_and_stays_in_the_tray(self) -> None:
        night = self.night()
        wrong = next(i for i, q in enumerate(night.tray) if q != night.clouds[1].dream)
        outcome = night.offer(wrong, 1)
        self.assertIs(outcome.offer, Offer.WRONG)
        self.assertEqual(outcome.cloud_misses, 1)
        self.assertIsNotNone(night.tray[wrong])
        self.assertIs(night.clouds[1].state, CloudState.AWAKE)
        self.assertEqual(night.misses, 1)

    def test_full_night_completes(self) -> None:
        night = self.night(level=4)
        for cloud in range(CLOUDS_PER_NIGHT):
            self.assertIs(night.offer(night.answer_for(cloud), cloud).offer, Offer.RIGHT)
            night.fall_asleep(cloud)
        self.assertTrue(night.complete)
        self.assertEqual(night.first_try, CLOUDS_PER_NIGHT)
        self.assertEqual(night.stars_given, sum(dream.stars for dream in night.plan.dreams))
        self.assertIsNone(night.next_awake())

    def test_ladder_adapts(self) -> None:
        self.assertEqual(adapt_level(0, 0), 1)
        self.assertEqual(adapt_level(MAX_LEVEL, 0), MAX_LEVEL)
        self.assertEqual(adapt_level(2, 1), 2)
        self.assertEqual(adapt_level(2, 3), 1)
        self.assertEqual(adapt_level(0, 9), 0)


# -- services -----------------------------------------------------------------------


class ServicesTests(unittest.TestCase):
    def test_progress_round_trip_and_corrupt_payloads(self) -> None:
        progress = BedtimeProgress(level=3, nights=7)
        self.assertEqual(parse_progress(progress_payload(progress)), progress)
        for raw in (None, "x", [], {"schema_version": 99, "level": 2}, {"schema_version": SCHEMA_VERSION, "level": True}):
            self.assertEqual(parse_progress(raw).level, 0)
        clamped = parse_progress({"schema_version": SCHEMA_VERSION, "level": 99, "nights": -4})
        self.assertEqual((clamped.level, clamped.nights), (MAX_LEVEL, 0))

    def test_legacy_preferences_are_never_touched(self) -> None:
        legacy = json.dumps({"blanket_ids": ["rose", "amber", "mint"]})
        storage = FakeStorage({LEGACY_STORAGE_KEY: legacy})
        port = GreiaBedtimeProgress(storage)
        self.assertEqual(port.load(), BedtimeProgress())
        port.save(BedtimeProgress(level=1, nights=1))
        self.assertEqual(storage.values[LEGACY_STORAGE_KEY], legacy)
        self.assertEqual(storage.values[STORAGE_KEY]["level"], 1)

    def test_storage_failures_are_soft(self) -> None:
        broken = mock.Mock()
        broken.kv_get.side_effect = OSError("disk")
        broken.kv_set.side_effect = OSError("disk")
        port = GreiaBedtimeProgress(broken)
        self.assertEqual(port.load(), BedtimeProgress())
        port.save(BedtimeProgress(level=2))

    def test_completion_event_uses_the_declared_id(self) -> None:
        with mock.patch("activities.nanna_delle_nuvolette.cloud_services.emit_activity_event") as emit:
            GreiaCloudEvents().rest_completed("night-1", {"cloud_count": 3})
        emit.assert_called_once_with(EVENT_REST_COMPLETED, {"cloud_count": 3}, idempotency_key="cloud-rest:night-1")
        manifest = tomllib.loads((ACTIVITY_DIR / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual([event["id"] for event in manifest["education"]["events"]], [EVENT_REST_COMPLETED])


# -- manifest, locales, art ----------------------------------------------------------


class PackageTests(unittest.TestCase):
    def test_manifest_claims_match_the_game(self) -> None:
        manifest = tomllib.loads((ACTIVITY_DIR / "activity.toml").read_text(encoding="utf-8"))
        education = manifest["education"]
        self.assertEqual(manifest["activity"]["id"], "org.greia.nanna-delle-nuvolette")
        self.assertEqual(set(manifest["activity"]["languages"]), {"en", "it", "es", "fr"})
        self.assertEqual(manifest["input"]["profile"], "hybrid")
        self.assertIn("color_shape_matching", education["categories"])
        skills = {skill["id"] for skill in education["skills"]}
        self.assertTrue({"cognition.matching.color", "math.small_sets"} <= skills)
        self.assertEqual(education["recommended_age_min"], 3)
        self.assertEqual((education["difficulty_min"], education["difficulty_max"]), (1, len(LEVELS)))
        self.assertTrue(education["adaptive_difficulty"])

    def test_locales_have_key_parity_and_the_child_strings(self) -> None:
        bundles = {locale: json.loads((ACTIVITY_DIR / "locales" / f"{locale}.json").read_text(encoding="utf-8")) for locale in LOCALES}
        keys = set(bundles["en"]["strings"])
        for locale, bundle in bundles.items():
            self.assertEqual(set(bundle["strings"]), keys, locale)
            self.assertTrue(all(value.strip() for value in bundle["strings"].values()))
        for key in ("victory.title", "victory.body", "btn.another_night"):
            self.assertIn(key, keys)

    def test_private_art_sources_have_runtime_renditions(self) -> None:
        sources = sorted(path.stem for path in (ACTIVITY_DIR / "assets" / "source").glob("*.svg") if path.stem != "icon")
        self.assertEqual(
            set(sources),
            {
                "blanket_body", "blanket_line", "blanket_tucked_body", "blanket_tucked_line",
                "cloud_body", "cloud_line", "cloud_face_asleep", "cloud_face_awake", "cloud_face_yawn",
                "dream_bubble",
            },
        )
        pygame.init()
        for name in sources:
            image = pygame.image.load(str(ACTIVITY_DIR / "assets" / "runtime" / f"{name}.png"))
            self.assertEqual(image.get_size(), (256, 256), name)
            svg = (ACTIVITY_DIR / "assets" / "source" / f"{name}.svg").read_text(encoding="utf-8")
            for forbidden in ("<image", "<text", "<filter", "<mask", "<style", "<script"):
                self.assertNotIn(forbidden, svg, name)
        self.assertEqual(pygame.image.load(str(ACTIVITY_DIR / "assets" / "icon.png")).get_size(), (256, 256))

    def test_art_builds_bounded_surfaces(self) -> None:
        pygame.init()
        art = CloudArt()
        quilt = Quilt("blue", 4)
        self.assertEqual(art.cloud(COLOURS["blue"].cloud, "awake").get_size(), (CLOUD_SIZE, CLOUD_SIZE))
        self.assertEqual(art.tucked_quilt(quilt).get_size(), (CLOUD_SIZE, CLOUD_SIZE))
        self.assertIs(art.tile_quilt(quilt), art.tile_quilt(quilt), "cached once per content")
        self.assertIsNotNone(art.star(30))
        self.assertEqual(art.bubble(quilt).get_size(), bubble_box(0).size)
        self.assertEqual(art.backdrop(0).get_size(), (1024, 600))
        for step in range(len(DIM_ALPHAS)):
            art.backdrop(step)
        self.assertLessEqual(len(art._backdrops), 2)
        self.assertTrue(art.fx_frames("sparkle"))
        self.assertIsNotNone(art.momo("pose_point", 120, mirrored=True))

    def test_layout_keeps_play_out_of_the_protected_chrome(self) -> None:
        for size in ((1024, 600), (800, 480), (480, 320)):
            screen = pygame.display.set_mode(size)
            canvas = PygameReferenceCanvas(screen)
            from greia_platform.activity_controls import ControlLayout

            protected = ControlLayout.for_canvas(canvas, size).protected
            for index in range(CLOUDS_PER_NIGHT):
                self.assertFalse(cloud_hit(index).colliderect(protected), (size, index))
                inner = bubble_box(index).inflate(-24, -24)
                self.assertFalse(inner.colliderect(protected), (size, index))
            for rect in tile_rects(MAX_TRAY):
                self.assertTrue(TRAY_PANEL.contains(rect))
                self.assertFalse(rect.colliderect(protected))


# -- app loop -----------------------------------------------------------------------


class AppLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((1024, 600))
        self.clock = FakeClock()
        self.progress = MemoryProgress()
        self.events = RecordedEvents()

    def make(self, *, level: int = 0, locale: str = "en", seed: int = 5) -> CloudActivity:
        self.progress.saved = BedtimeProgress(level=level)
        resources = activity_resources(ACTIVITY_DIR, requested_locale=locale)
        app = CloudActivity(
            screen=self.screen,
            canvas=PygameReferenceCanvas(self.screen),
            typography=GreiaTypography(),
            resources=resources,
            audio=CloudAudio(locale=locale),
            progress=self.progress,
            events=self.events,
            rng=random.Random(seed),
            clock=self.clock,
        )
        self.advance(app, 1.5)
        self.assertIs(app.state, AppState.PLAYING)
        return app

    def advance(self, app: CloudActivity, seconds: float, dt: float = 0.05) -> None:
        elapsed = 0.0
        while elapsed < seconds:
            self.clock.now += dt
            elapsed += dt
            app.step()
            app.render()

    def mouse(self, app: CloudActivity, kind: int, pos: tuple[int, int]) -> None:
        app.handle_event(pygame.event.Event(kind, {"button": 1, "pos": pos}))

    def tile_of(self, app: CloudActivity, cloud: int, *, right: bool = True) -> int:
        night = app.night
        assert night is not None
        if right:
            return night.answer_for(cloud)
        return next(i for i, t in enumerate(app.tiles) if t.quilt is not None and t.quilt != night.clouds[cloud].dream)

    def test_tap_quilt_then_tap_cloud_tucks_it_in(self) -> None:
        """Regression (cf0df9ec): releasing in place keeps the quilt in hand."""

        app = self.make()
        tile = self.tile_of(app, 0)
        center = app.tiles[tile].rect.center
        self.mouse(app, pygame.MOUSEBUTTONDOWN, center)
        self.mouse(app, pygame.MOUSEBUTTONUP, (center[0] + DRAG_THRESHOLD_PX - 4, center[1]))
        self.assertEqual(app.held, tile)
        target = cloud_box(0).center
        self.mouse(app, pygame.MOUSEBUTTONDOWN, target)
        self.mouse(app, pygame.MOUSEBUTTONUP, target)
        self.assertIsNone(app.held)
        self.advance(app, 0.6)
        self.assertIs(app.night.clouds[0].state, CloudState.YAWNING)
        self.assertIsNone(app.tiles[tile].quilt)
        self.advance(app, 1.6)
        self.assertIs(app.night.clouds[0].state, CloudState.ASLEEP)
        self.assertEqual(app.dim_step, 1)

    def test_drag_to_cloud_and_drag_into_empty_sky(self) -> None:
        app = self.make()
        tile = self.tile_of(app, 2)
        app.drag(app.tiles[tile].rect.center, (500, 30))
        self.assertIsNone(app.held)
        self.assertIsNotNone(app.tiles[tile].quilt, "a drop on nothing puts the quilt back")
        self.advance(app, 0.6)
        app.drag(app.tiles[tile].rect.center, cloud_box(2).center)
        self.advance(app, 0.6)
        self.assertIsNotNone(app.night.clouds[2].quilt)

    def test_wrong_quilt_is_declined_with_think_and_demonstration(self) -> None:
        app = self.make()
        wrong = self.tile_of(app, 1, right=False)
        app.tap(app.tiles[wrong].rect.center)
        app.tap(cloud_box(1).center)
        self.advance(app, 0.5)
        self.assertEqual(app.cast.pose.value, "think")
        self.assertIs(app.night.clouds[1].state, CloudState.AWAKE)
        self.advance(app, 1.1)
        answer = self.tile_of(app, 1)
        self.assertIn(answer, app.motion.tile_hops)
        self.assertEqual(app.motion.bubble_glow[0], 1)
        self.assertIsNotNone(app.tiles[wrong].quilt, "the declined quilt is back in the tray")
        self.assertEqual(app.night.misses, 1)

    def test_keyboard_and_controller_play(self) -> None:
        from greia_platform.pygame_input import CONTROLLER_BUTTON_A

        app = self.make()
        # Focus the right quilt for cloud 0 (D-pad/arrows walk the tray).
        answer = self.tile_of(app, 0)
        app.press(pygame.K_LEFT)
        for _ in range(8):
            app.press(pygame.K_LEFT)
        for _ in range(answer):
            app.press(pygame.K_RIGHT)
        self.assertEqual(app.controls.layer.focused_id, f"quilt.{answer}")
        app.press(pygame.K_SPACE)
        self.assertEqual(app.held, answer)
        self.assertEqual(app.controls.layer.focused_id, "cloud.0", "focus moves on to the clouds")
        app.handle_event(pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=CONTROLLER_BUTTON_A))
        self.advance(app, 0.6)
        self.assertIsNotNone(app.night.clouds[0].quilt)
        # After a tuck the focus returns to the tray; Escape puts a held quilt
        # back instead of leaving the Activity.
        self.assertTrue(app.controls.layer.focused_id.startswith("quilt."))
        app.press(pygame.K_SPACE)
        self.assertIsNotNone(app.held)
        app.press(pygame.K_ESCAPE)
        self.assertIsNone(app.held)
        self.assertTrue(app._running)

    def test_protected_chrome_and_focus_loss(self) -> None:
        app = self.make()
        protected = ActivitySystemChromeLayout.for_surface(1024, 600).protected_region
        inside = (int(protected.x) + 2, int(protected.y) + 2)
        self.mouse(app, pygame.MOUSEBUTTONDOWN, inside)
        self.mouse(app, pygame.MOUSEBUTTONUP, inside)
        self.assertTrue(app._running)
        tile = self.tile_of(app, 0)
        center = app.tiles[tile].rect.center
        self.mouse(app, pygame.MOUSEBUTTONDOWN, center)
        app.handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": (center[0], center[1] - 80), "rel": (0, -80), "buttons": (1, 0, 0)}))
        self.assertIsNotNone(app.dragging)
        self.mouse(app, pygame.MOUSEBUTTONUP, inside)
        self.assertIsNone(app.held)
        self.assertIsNone(app.dragging)
        app.tap(center)
        self.assertEqual(app.held, tile)
        app.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertIsNone(app.held)
        self.assertEqual(app.night.tucked_count, 0)

    def test_idle_hints_grow(self) -> None:
        app = self.make()
        self.advance(app, 6.2)
        self.assertTrue(app.cast.pointing)
        self.assertEqual(app.motion.bubble_glow[0], 0)
        self.advance(app, 12.2)  # back-off: 6 s, then a further 12 s
        self.assertEqual(app._hints.count, 2)

    def test_full_night_reaches_the_completion_scene_then_another_night(self) -> None:
        app = self.make(level=2, locale="it")
        for cloud in range(CLOUDS_PER_NIGHT):
            tile = self.tile_of(app, cloud)
            if cloud == 1:
                app.drag(app.tiles[tile].rect.center, cloud_box(cloud).center)
            else:
                app.tap(app.tiles[tile].rect.center)
                app.tap(cloud_box(cloud).center)
            self.advance(app, 2.3)
        self.assertTrue(app.night.complete)
        self.advance(app, 1.4)
        self.assertIs(app.state, AppState.FINALE)
        self.assertIsNotNone(app.motion.shooting)
        self.assertEqual(app.dim_step, CLOUDS_PER_NIGHT)
        self.advance(app, 4.6)
        self.assertIs(app.state, AppState.TERMINAL)
        self.assertIsNotNone(app.completion)
        self.assertEqual(len(self.events.completed), 1)
        payload = self.events.completed[0][1]
        self.assertEqual(payload["cloud_count"], 3)
        self.assertEqual(payload["misses"], 0)
        self.assertEqual(payload["star_count"], 6)
        self.assertEqual(self.progress.saved, BedtimeProgress(level=3, nights=1))
        # "Another night": the replay button of the shared scene starts over.
        app.tap(app.completion.primary_rect.center)
        self.assertIs(app.state, AppState.INTRO)
        self.assertIsNone(app.completion)
        self.advance(app, 1.5)
        self.assertEqual(app.night.level, 3)
        self.assertEqual(len(app.tiles), CLOUDS_PER_NIGHT + LEVELS[3].extras)

    def test_lullaby_uses_only_synthesized_notes(self) -> None:
        self.assertTrue(all(name.startswith("sleep_") for _, name in LULLABY))

    def test_home_stop_ends_the_real_loop_promptly_and_saves(self) -> None:
        """Greia's graceful stop (Home) ends ``run`` on the next pass, in time.

        Acer sweep at 4d6e9c5e saw one 2.9 s forced stop; 19 later in-Shell
        Home stops measured 0.75-1.3 s. The loop must never wait on anything
        but one bounded frame wait before honouring the stop marker.
        """

        import time as real_time

        app = self.make()
        app.clock = real_time.monotonic
        calls = {"n": 0}

        def stop_requested() -> bool:
            calls["n"] += 1
            return calls["n"] > 3

        saves_before = self.progress.saves
        with mock.patch("activities.nanna_delle_nuvolette.cloud_app.activity_stop_requested", stop_requested), \
                mock.patch("activities.nanna_delle_nuvolette.cloud_app.mark_activity_ready"):
            started = real_time.monotonic()
            self.assertEqual(app.run(), 0)
            elapsed = real_time.monotonic() - started
        self.assertEqual(calls["n"], 4)  # left on the first check that saw the stop
        self.assertEqual(self.progress.saves, saves_before + 1)
        self.assertLess(elapsed, 2.0)  # the supervisor's graceful deadline

    def test_renders_at_supported_sizes(self) -> None:
        for size in ((1024, 600), (800, 480), (480, 320)):
            self.screen = pygame.display.set_mode(size)
            app = self.make(level=4)
            app.tap(app.tiles[0].rect.center)
            self.advance(app, 0.2)
            app.canvas.present()
            self.assertEqual(app.screen.get_size(), size)


if __name__ == "__main__":
    unittest.main()
