"""Rules, persistence and app-loop tests for Magic Bakery (Pasticceria Magica)."""

from __future__ import annotations

import os
from pathlib import Path
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from activities.pasticceria_magica.pasticceria_content import (
    CUSTOMERS,
    FREE_LIMIT,
    LEVELS,
    LOOKALIKES,
    MAX_LEVEL,
    ORDERS_PER_ROUND,
    PATTERN,
    TOPPING_IDS,
)
from activities.pasticceria_magica.pasticceria_model import (
    BakeryRound,
    CountCake,
    CountItem,
    CountOrder,
    FreeCake,
    PatternOrder,
    adapt_level,
    make_count_order,
    make_pattern_order,
)
from activities.pasticceria_magica.pasticceria_services import (
    SCHEMA_VERSION,
    BakeryProgress,
    GreiaBakeryPictures,
    parse_progress,
    progress_payload,
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "activities" / "pasticceria_magica"


class CountOrderTests(unittest.TestCase):
    def test_exact_quantities_are_required(self) -> None:
        order = CountOrder((CountItem("strawberry", 3), CountItem("blueberry", 1)), ("strawberry", "blueberry", "banana"))
        cake = order.new_cake()
        self.assertFalse(order.ready(cake))
        for _ in range(3):
            cake.place("strawberry")
        self.assertTrue(order.ready(cake))
        verdict = order.check(cake)
        self.assertFalse(verdict.correct)
        self.assertEqual(verdict.missing, ("blueberry",))
        cake.place("blueberry")
        self.assertTrue(order.check(cake).correct)
        extra = cake.place("strawberry")
        verdict = order.check(cake)
        self.assertFalse(verdict.correct)
        self.assertEqual(verdict.wrong, (extra.index,))
        cake.undo()
        stray = cake.place("banana")
        self.assertEqual(order.check(cake).wrong, (stray.index,))

    def test_counting_ordinal_and_removal(self) -> None:
        cake = CountCake()
        self.assertEqual([cake.place("cherry").ordinal for _ in range(3)], [1, 2, 3])
        self.assertTrue(cake.remove(1))
        self.assertFalse(cake.remove(1))
        self.assertEqual(cake.count("cherry"), 2)
        self.assertEqual(cake.place("cherry").index, 1)  # the hole is filled first
        self.assertIsNone(cake.place("not_a_topping"))
        while cake.place("cherry") is not None:
            pass
        self.assertEqual(len(cake.placements()), cake.capacity)


class PatternOrderTests(unittest.TestCase):
    def test_pattern_needs_every_blank_and_reports_ghosts(self) -> None:
        order = PatternOrder("AB", ("strawberry", "blueberry") * 3, 4, ("strawberry", "blueberry", "banana"))
        cake = order.new_cake()
        self.assertEqual(cake.row()[:4], order.start)
        self.assertEqual(cake.placements(), ())  # the start belongs to the customer
        cake.place("blueberry")
        self.assertFalse(order.ready(cake))
        cake.place("blueberry")
        verdict = order.check(cake)
        self.assertFalse(verdict.correct)
        self.assertEqual(verdict.wrong, (4,))
        self.assertEqual(verdict.ghosts, ((4, "strawberry"),))
        self.assertFalse(cake.remove(0))  # the customer's start cannot be removed
        cake.undo()
        cake.undo()
        self.assertEqual(order.next_needed(cake), "strawberry")
        cake.place("strawberry")
        cake.place("blueberry")
        self.assertTrue(order.check(cake).correct)

    def test_pattern_demonstration_sounds_each_kind(self) -> None:
        order = PatternOrder("AB", ("strawberry", "blueberry") * 3, 4, ("strawberry", "blueberry", "banana"))
        cake = order.new_cake()
        cake.place("banana")
        steps = order.demonstration(cake)
        self.assertEqual([step.index for step in steps], list(range(6)))
        self.assertEqual([step.tone for step in steps[:4]], [1, 3, 1, 3])
        self.assertEqual(steps[4].tone, 2)  # a topping that is not in the pattern
        self.assertEqual(steps[5].tone, 0)  # still open

    def test_generated_patterns_follow_their_unit(self) -> None:
        rng = random.Random(4)
        for level, spec in enumerate(LEVELS):
            for _ in range(20):
                order = make_pattern_order(spec, rng)
                self.assertIn(order.unit, spec.units)
                letters = sorted(set(order.unit))
                mapping = {}
                for letter, topping in zip(order.unit * 6, order.answer):
                    mapping.setdefault(letter, topping)
                    self.assertEqual(mapping[letter], topping)
                self.assertEqual(len(set(mapping.values())), len(letters))
                self.assertEqual(order.blanks, spec.blanks)
                self.assertTrue(set(order.answer) <= set(order.pantry))
                self.assertEqual(len(order.pantry), spec.pantry)


class LadderTests(unittest.TestCase):
    def test_count_orders_stay_inside_each_rung(self) -> None:
        rng = random.Random(9)
        for spec in LEVELS:
            for _ in range(40):
                order = make_count_order(spec, rng)
                self.assertGreaterEqual(len(order.items), spec.kinds[0])
                self.assertLessEqual(len(order.items), spec.kinds[1])
                self.assertLessEqual(order.total, spec.max_total)
                for item in order.items:
                    self.assertGreaterEqual(item.amount, 1)
                    self.assertLessEqual(item.amount, spec.count_range[1])
                    self.assertIn(item.topping_id, order.pantry)
                self.assertEqual(order.pictures, spec.pictures)
                for pair in LOOKALIKES:
                    self.assertFalse(pair <= set(order.pantry), "look-alike toppings offered together")
                self.assertEqual(list(order.pantry), [t for t in TOPPING_IDS if t in order.pantry])

    def test_round_plan_and_adaptation(self) -> None:
        game = BakeryRound.planned(0, random.Random(1))
        self.assertEqual(game.total, ORDERS_PER_ROUND)
        self.assertEqual(sorted(game.customers), sorted(CUSTOMERS))
        self.assertEqual([o.kind for o in game.orders], list(LEVELS[0].orders))
        self.assertEqual(adapt_level(0, 0), 1)
        self.assertEqual(adapt_level(2, 3), 2)
        self.assertEqual(adapt_level(2, 6), 1)
        self.assertEqual(adapt_level(MAX_LEVEL, 0), MAX_LEVEL)
        self.assertEqual(adapt_level(0, 9), 0)

    def test_round_serve_and_advance(self) -> None:
        game = BakeryRound.planned(0, random.Random(3))
        self.assertIsNone(game.serve())  # nothing on the cake yet
        _solve(game)
        verdict = game.serve()
        self.assertTrue(verdict.correct)
        self.assertEqual(game.first_try, 1)
        self.assertTrue(game.next_customer())
        self.assertEqual(game.index, 1)
        self.assertTrue(game.cake.empty)


class FreeCakeAndSaveTests(unittest.TestCase):
    def test_free_cake_is_bounded_and_round_trips(self) -> None:
        cake = FreeCake()
        for index in range(FREE_LIMIT + 5):
            cake.place(TOPPING_IDS[index % len(TOPPING_IDS)], 0.1, 0.1)
        self.assertEqual(len(cake.toppings), FREE_LIMIT)
        far = FreeCake()
        placed = far.place("banana", 3.0, 0.0)
        self.assertLessEqual(placed.u, 0.86)
        again = FreeCake.from_json(cake.to_json())
        self.assertEqual(again.signature(), cake.signature())
        junk = FreeCake.from_json([["banana", 0, 0], ["lava", 0, 0], ["cherry", 9, 9], "x", ["cherry", True, 0]])
        self.assertEqual(len(junk.toppings), 1)

    def test_legacy_save_migrates_and_new_schema_round_trips(self) -> None:
        legacy = parse_progress({"score": 45, "stars": 3, "recipes_served": 3, "timestamp": 1.0})
        self.assertEqual(legacy.orders_served, 3)
        self.assertEqual(legacy.legacy, {"score": 45, "stars": 3})
        self.assertEqual(legacy.level, 0)
        progress = BakeryProgress(level=2, rounds=4, orders_served=20, legacy={"stars": 3})
        progress.free_cake.place("cherry", 0.2, -0.1)
        payload = progress_payload(progress)
        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        again = parse_progress(payload)
        self.assertEqual((again.level, again.rounds, again.orders_served), (2, 4, 20))
        self.assertEqual(again.free_cake.signature(), progress.free_cake.signature())
        self.assertEqual(again.legacy, {"stars": 3})
        blank = parse_progress("nonsense")
        self.assertEqual((blank.level, blank.rounds, blank.orders_served, blank.legacy), (0, 0, 0, {}))
        self.assertTrue(blank.free_cake.empty)
        self.assertEqual(parse_progress({"schema_version": SCHEMA_VERSION, "level": 99}).level, MAX_LEVEL)

    def test_picture_adapter_writes_privately_then_publishes(self) -> None:
        storage, creations = _FakeStorage(), _FakeCreations()
        pictures = GreiaBakeryPictures(storage, creations)
        self.assertTrue(pictures.publish(b"\x89PNG..."))
        self.assertEqual(storage.files, {"cakes/shared.png": b"\x89PNG..."})
        self.assertEqual(creations.published, [("cakes/shared.png", "image/png", "composition")])
        self.assertFalse(GreiaBakeryPictures(storage, None).publish(b"x"))
        self.assertFalse(pictures.publish(b""))


class SpokenWordsTests(unittest.TestCase):
    def test_numbers_are_spoken_only_when_the_shared_bank_exists(self) -> None:
        from unittest import mock

        from greia_platform import localization
        from activities.pasticceria_magica.pasticceria_audio import BakeryAudio

        # The shared numbers bank (assets/audio/numbers/v1) ships 0..25 in all
        # four released languages since 2026-10-17.
        self.assertTrue(BakeryAudio(locale="it").has_number(3))
        with mock.patch.object(localization, "shared_number_audio_path", lambda root, value, locale: None):
            audio = BakeryAudio(locale="it")
            self.assertFalse(audio.has_number(3))
            self.assertFalse(audio.say_number(3))


class LocaleAndManifestTests(unittest.TestCase):
    def test_four_locales_share_keys(self) -> None:
        import json

        bundles = {
            locale: json.loads((PACKAGE / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
            for locale in ("en", "it", "es", "fr")
        }
        keys = set(bundles["en"]["strings"])
        for locale, bundle in bundles.items():
            self.assertEqual(set(bundle["strings"]), keys, locale)
            for value in bundle["strings"].values():
                self.assertTrue(value.strip())

    def test_manifest_declares_creations_and_events_used(self) -> None:
        import tomllib

        manifest = tomllib.loads((PACKAGE / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["creations"]["produces"], ["image/png"])
        events = {event["id"] for event in manifest["education"]["events"]}
        self.assertEqual(events, {"recipe.completed", "pattern.solved", "round.completed", "creation.completed"})
        self.assertEqual(manifest["input"]["profile"], "hybrid")
        self.assertEqual(manifest["activity"]["languages"], ["it", "en", "es", "fr"])


# -- app loop ------------------------------------------------------------------------------


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class _FakeStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def file_write_atomic(self, name: str, payload: bytes) -> None:
        self.files[name] = bytes(payload)


class _FakeCreations:
    def __init__(self) -> None:
        self.published: list[tuple[str, str, str]] = []

    def publish_private_file(self, name: str, *, media_type: str, role: str, title: str = "") -> dict:
        self.published.append((name, media_type, role))
        return {}


class _MemoryProgress:
    def __init__(self, progress: BakeryProgress | None = None) -> None:
        self.saved: BakeryProgress | None = progress
        self.saves = 0

    def load(self) -> BakeryProgress:
        return parse_progress(progress_payload(self.saved)) if self.saved is not None else BakeryProgress()

    def save(self, progress: BakeryProgress) -> None:
        self.saved = parse_progress(progress_payload(progress))
        self.saves += 1


class _Events:
    def __init__(self) -> None:
        self.log: list[tuple[str, dict]] = []

    def order_served(self, event_id, session_id, payload) -> None:
        self.log.append((event_id, payload))

    def round_completed(self, session_id, payload) -> None:
        self.log.append(("round.completed", payload))

    def picture_shared(self, digest, payload) -> None:
        self.log.append(("creation.completed", payload))


class _Pictures:
    def __init__(self) -> None:
        self.payloads: list[bytes] = []

    @property
    def available(self) -> bool:
        return True

    def publish(self, payload: bytes) -> bool:
        self.payloads.append(payload)
        return True


class _NoPictures:
    available = False

    def publish(self, payload: bytes) -> bool:
        raise AssertionError("nothing may be published without My Creations")


def _solve(game: BakeryRound) -> None:
    order = game.order
    if order.kind == PATTERN:
        for index in range(order.given, len(order.answer)):
            game.place(order.answer[index])
    else:
        for item in order.items:
            for _ in range(item.amount):
                game.place(item.topping_id)


class BakeryAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600))

    def _app(self, *, size=(1024, 600), progress=None, seed: int = 5, locale: str = "en"):
        from greia_platform.localization import activity_resources
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from activities.pasticceria_magica.pasticceria_app import PasticceriaApp
        from activities.pasticceria_magica.pasticceria_audio import BakeryAudio

        screen = pygame.display.set_mode(size)
        clock = _Clock()
        self.progress = _MemoryProgress(progress)
        self.events = _Events()
        self.pictures = _Pictures()
        app = PasticceriaApp(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            typography=GreiaTypography(),
            resources=activity_resources(PACKAGE, requested_locale=locale),
            audio=BakeryAudio(locale=locale, rng=random.Random(seed)),
            progress=self.progress,
            events=self.events,
            pictures=self.pictures,
            rng=random.Random(seed),
            clock=clock,
            session_prefix="test",
        )
        self.clock = clock
        return app

    def _advance(self, app, seconds: float) -> None:
        steps = max(1, int(seconds / 0.05))
        for _ in range(steps):
            self.clock.now += 0.05
            app.step()

    def _tap_topping(self, app, topping_id: str) -> None:
        rect = app.controls.tile_rect(topping_id)
        self.assertIsNotNone(rect, f"{topping_id} not in the pantry")
        self.assertTrue(app.tap(rect.center))

    def _make(self, app) -> None:
        order = app.round.order
        if order.kind == PATTERN:
            for index in range(order.given, len(order.answer)):
                self._tap_topping(app, order.answer[index])
        else:
            for item in order.items:
                for _ in range(item.amount):
                    self._tap_topping(app, item.topping_id)

    def test_a_round_plays_to_the_completion_scene(self) -> None:
        app = self._app()
        self._advance(app, 1.0)
        app.render()
        self.assertTrue(app.show_card)
        for served in range(ORDERS_PER_ROUND):
            self._make(app)
            app.render()
            self.assertTrue(app.controls.serve.enabled)
            self.assertTrue(app.tap(app.controls.serve.rect.center))
            self.assertTrue(app.last_serve.verdict.correct)
            self.assertEqual(app.cast.pose.value, "cheer")
            self._advance(app, 4.0)
            app.render()
        self.assertIsNotNone(app.completion)
        self.assertEqual(app.screen_id.value, "end")
        kinds = [event for event, _ in self.events.log]
        self.assertEqual(kinds.count("round.completed"), 1)
        self.assertEqual(len(kinds), ORDERS_PER_ROUND + 1)
        self.assertEqual(self.progress.saved.level, 1)  # a clean round climbs
        self.assertEqual(self.progress.saved.orders_served, ORDERS_PER_ROUND)
        self.assertEqual(self.progress.saved.rounds, 1)
        # Primary on the completion scene starts the next round at the new rung.
        app.tap(app.completion.primary_rect.center)
        self.assertIsNone(app.completion)
        self.assertEqual(app.round.level, 1)

    def test_a_wrong_cake_gets_a_demonstration_then_ghosts(self) -> None:
        app = self._app(seed=2)
        self._advance(app, 1.0)
        order = app.round.order
        if order.kind == PATTERN:
            self.skipTest("seed starts with a pattern")
        wrong = next(t for t in order.pantry if t not in {i.topping_id for i in order.items})
        self._tap_topping(app, wrong)
        app.tap(app.controls.serve.rect.center)
        self.assertFalse(app.last_serve.verdict.correct)
        self.assertEqual(app.cast.pose.value, "think")
        self.assertFalse(app.controls.serve.visible)  # the shop counts together first
        self._advance(app, 4.0)
        app.render()
        self.assertTrue(app.controls.serve.visible)
        self.assertEqual(app.motion.ghosts, ())  # no ghosts after a first miss
        app.tap(app.controls.serve.rect.center)
        self._advance(app, 4.0)
        app.render()
        self.assertTrue(app.motion.ghosts)  # second miss: faint ghosts show where toppings belong
        # Take the stray topping off by tapping it, then make the order.
        index = app.round.cake.placements()[0][0]
        from activities.pasticceria_magica.pasticceria_layout import COUNT_POINTS, TOPPING_SIZE, sprite_rect

        app.tap(sprite_rect(COUNT_POINTS[index], TOPPING_SIZE).center)
        self.assertTrue(app.round.cake.empty)
        self._make(app)
        app.tap(app.controls.serve.rect.center)
        self.assertTrue(app.last_serve.verdict.correct)
        self.assertEqual(app.round.total_misses, 2)

    def test_keyboard_and_controller_reach_pantry_and_bell(self) -> None:
        app = self._app(seed=7)
        self._advance(app, 1.0)
        layer = app.controls.layer
        self.assertTrue(layer.focused_id.startswith("topping."))
        app.press(pygame.K_SPACE)
        self.assertFalse(app.round.cake.empty)
        for _ in range(8):
            app.press(pygame.K_RIGHT)
        app.press(pygame.K_UP)
        self.assertEqual(layer.focused_id, "serve")
        self.assertTrue(app.press(pygame.K_RETURN))
        self.assertIsNotNone(app.last_serve)

        from greia_platform import pygame_input

        if pygame_input.sdl_controller is None or pygame_input._CONTROLLER_BUTTON_DOWN < 0:
            return
        app = self._app(seed=7)
        self._advance(app, 1.0)
        down = pygame_input._CONTROLLER_BUTTON_DOWN
        app.handle_event(pygame.event.Event(down, button=pygame_input.CONTROLLER_BUTTON_A))
        self.assertFalse(app.round.cake.empty)

    def test_my_cake_ending_saves_one_picture(self) -> None:
        app = self._app()
        app.start_free()
        self._advance(app, 0.5)
        self.assertFalse(app.controls.save.enabled)  # no blank saves
        self._tap_topping(app, "cherry")
        from activities.pasticceria_magica.pasticceria_layout import FROSTING_CENTER

        app.tap((FROSTING_CENTER[0] + 100, FROSTING_CENTER[1] + 30))  # puts a cherry exactly there
        self.assertEqual(len(app.free_cake.toppings), 2)
        self.assertFalse(app.controls.new_cake.enabled)  # unsaved work cannot be thrown away
        app.render()
        app.tap(app.controls.save.rect.center)
        self.assertEqual(len(self.pictures.payloads), 1)
        self.assertTrue(self.pictures.payloads[0].startswith(b"\x89PNG"))
        app.tap(app.controls.save.rect.center)
        self.assertEqual(len(self.pictures.payloads), 1)  # same cake is not published twice
        self.assertEqual([e for e, _ in self.events.log].count("creation.completed"), 1)
        self.assertTrue(app.controls.new_cake.enabled)
        self.assertEqual(len(self.progress.saved.free_cake.toppings), 2)  # draft kept
        app.tap(app.controls.new_cake.rect.center)
        self.assertTrue(app.free_cake.empty)
        app.tap(app.controls.new_round.rect.center)
        self.assertEqual(app.screen_id.value, "round")

    def test_save_is_absent_without_my_creations(self) -> None:
        app = self._app()
        app.pictures = _NoPictures()
        app.start_free()
        self._tap_topping(app, "cookie")
        self.assertFalse(app.controls.save.visible)
        app._on_save()
        self.assertEqual([e for e, _ in self.events.log], [])

    def test_free_draft_survives_a_restart(self) -> None:
        app = self._app()
        app.start_free()
        self._tap_topping(app, "banana")
        self._advance(app, 2.5)  # throttled draft save
        restored = self._app(progress=self.progress.saved)
        self.assertEqual([t.topping_id for t in restored.free_cake.toppings], ["banana"])

    def test_controls_stay_clear_of_protected_chrome(self) -> None:
        from greia_platform.activity_controls import ControlLayout
        from activities.pasticceria_magica.pasticceria_layout import BUBBLE_RECT

        for size in ((1024, 600), (800, 480), (480, 320)):
            app = self._app(size=size)
            self._advance(app, 1.0)
            protected = ControlLayout.for_canvas(app.canvas, size).protected
            self.assertFalse(BUBBLE_RECT.colliderect(protected), size)
            for target in app.controls.layer.targets:
                self.assertFalse(target.rect.colliderect(protected), (size, target.control_id))
            app.start_free()
            for target in app.controls.layer.targets:
                self.assertFalse(target.rect.colliderect(protected), (size, target.control_id))
            app.render()


if __name__ == "__main__":
    unittest.main()
