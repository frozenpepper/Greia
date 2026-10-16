"""My Cute Pet (Cucciolo Mio): rules, content, art, persistence and app loop.

Runs headlessly (SDL dummy drivers) against the real shared art catalogue,
with an injected clock, in-memory pet profile and recorded events, so no
child profile data, voices or windows are touched.
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

from activities.cucciolo_mio.cucciolo_app import CuccioloApp
from activities.cucciolo_mio.cucciolo_art import PRIVATE_FILES, CuccioloArt
from activities.cucciolo_mio.cucciolo_audio import CuccioloAudio
from activities.cucciolo_mio.cucciolo_content import (
    CARE_FOR_NEED,
    CARES,
    LEVELS,
    MAX_LEVEL,
    NAMES,
    REFERENCE_HEIGHT,
    REFERENCE_WIDTH,
    ROOMS,
    SPECIES,
    STORAGE_KEY,
    TRAY_ORDER,
    Care,
    Need,
    Room,
)
from activities.cucciolo_mio.cucciolo_controls import care_id
from activities.cucciolo_mio.cucciolo_layout import (
    CONFIRM_RECT,
    LILLI_HEIGHT,
    LILLI_MIDBOTTOM,
    STAGES,
    adopt_rects,
    name_rects,
    tray_rects,
)
from activities.cucciolo_mio.cucciolo_model import CareDay, Offer, Phase, adapt_level, plan_day
from activities.cucciolo_mio.cucciolo_renderer import Screen
from activities.cucciolo_mio.cucciolo_services import (
    SCHEMA_VERSION,
    GreiaPetProgress,
    PetProfile,
    parse_profile,
    profile_payload,
)
from greia_platform.activity_api import get_shared_visual_path
from greia_platform.localization import activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.system_chrome import ActivitySystemChromeLayout
from greia_platform.typography import GreiaTypography

ACTIVITY_DIR = PROJECT_ROOT / "activities" / "cucciolo_mio"
LOCALES = ("en", "it", "es", "fr")
NEED_VARIANTS = ("default", "happy", *(need.value for need in Need))


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class MemoryProgress:
    def __init__(self, profile: PetProfile | None = None) -> None:
        self.saved = profile or PetProfile()
        self.saves = 0

    def load(self) -> PetProfile:
        return self.saved

    def save(self, profile: PetProfile) -> None:
        self.saved = profile
        self.saves += 1


class RecordedEvents:
    def __init__(self) -> None:
        self.cares: list[tuple[str, dict]] = []
        self.days: list[dict] = []

    def cared(self, event_id: str, session_id: str, payload: dict) -> None:
        self.cares.append((event_id, payload))

    def day_completed(self, session_id: str, payload: dict) -> None:
        self.days.append(payload)


class FakeStorage:
    def __init__(self, value=None) -> None:
        self.values = {STORAGE_KEY: value} if value is not None else {}

    def kv_get(self, key):
        return self.values.get(key)

    def kv_set(self, key, value) -> None:
        self.values[key] = value


def _strings(locale: str) -> dict[str, str]:
    return json.loads((ACTIVITY_DIR / "locales" / f"{locale}.json").read_text(encoding="utf-8"))["strings"]


def _chrome() -> pygame.Rect:
    protected = ActivitySystemChromeLayout.for_surface(REFERENCE_WIDTH, REFERENCE_HEIGHT).protected_region
    return pygame.Rect(protected.x, protected.y, protected.width, protected.height)


def _lilli() -> pygame.Rect:
    rect = pygame.Rect(0, 0, int(LILLI_HEIGHT * 0.9), LILLI_HEIGHT)
    rect.midbottom = LILLI_MIDBOTTOM
    return rect


class ManifestAndLocaleTests(unittest.TestCase):
    def test_manifest_matches_the_gameplay(self) -> None:
        with (ACTIVITY_DIR / "activity.toml").open("rb") as handle:
            data = tomllib.load(handle)
        self.assertEqual(data["activity"]["id"], "org.greia.cucciolo-mio")
        self.assertEqual(sorted(data["activity"]["languages"]), ["en", "it"])  # ES/FR stay staged
        self.assertEqual(data["input"]["profile"], "hybrid")
        education = data["education"]
        self.assertEqual((education["recommended_age_min"], education["recommended_age_max"]), (3, 5))
        self.assertTrue(education["adaptive_difficulty"])
        self.assertEqual(education["difficulty_max"], len(LEVELS))
        skills = {skill["id"] for skill in education["skills"]}
        self.assertIn("emotional.empathy_caregiving", skills)
        self.assertIn("emotional.recognition.body_language", skills)
        self.assertNotIn("motor.pointer.drag_and_drop", skills)  # no dragging in the new loop
        events = {event["id"]: event["kind"] for event in education["events"]}
        expected = {kind.event_id: "milestone" for kind in CARES.values() if kind.care is not Care.BED}
        expected["pet.tucked_in"] = "completion"
        self.assertEqual(events, expected)

    def test_four_locales_have_key_parity_and_every_content_key(self) -> None:
        english = _strings("en")
        required = {"activity.title", "adopt.prompt", "name.prompt", "victory.title", "victory.subtitle", "btn.new_day"}
        required |= {species.name_key for species in SPECIES}
        required |= {name.text_key for name in NAMES}
        self.assertEqual(set(english), required)
        for locale in LOCALES:
            with self.subTest(locale=locale):
                strings = _strings(locale)
                self.assertEqual(set(strings), set(english))
                self.assertTrue(all(value.strip() for value in strings.values()))
                self.assertIn("$name", strings["victory.title"])
                self.assertFalse(any(ord(ch) > 0x2600 for value in strings.values() for ch in value))  # no emoji

    def test_title_audio_is_kept_and_text_follows_the_case_policy(self) -> None:
        for locale in ("en", "it"):
            bundle = json.loads((ACTIVITY_DIR / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
            self.assertTrue((ACTIVITY_DIR / bundle["audio"]["activity.title"]["path"]).is_file())
        resources = activity_resources(ACTIVITY_DIR, requested_locale="it")
        self.assertEqual(resources.text("victory.title", {"name": resources.text("name.moon")}), "SOGNI D'ORO, LUNA!")


class ContentAndArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT))

    def test_every_shared_art_reference_resolves(self) -> None:
        for species in SPECIES:
            for variant in NEED_VARIANTS:
                self.assertTrue(get_shared_visual_path(species.asset_id, variant=variant).is_file(), (species, variant))
            self.assertTrue(get_shared_visual_path(species.food_asset).is_file(), species.food_asset)
        for name in NAMES:
            self.assertTrue(get_shared_visual_path(name.asset_id).is_file(), name.asset_id)
        for kit in ROOMS.values():
            for layer in kit.layers:
                self.assertTrue(get_shared_visual_path(layer).is_file(), layer)
        for asset in ("prop.everyday.sponge", "prop.everyday.ball", "prop.vocab.moon", "prop.nature.sun", "icon.hud.heart"):
            self.assertTrue(get_shared_visual_path(asset).is_file(), asset)
        for variant in ("happy", "pose_cheer", "pose_think", "pose_point"):
            self.assertTrue(get_shared_visual_path("character.lilli", variant=variant).is_file(), variant)

    def test_private_art_has_sources_and_follows_the_authoring_lint(self) -> None:
        forbidden = ("<image", "data:", "<text", "<filter", "<mask", "<pattern", "<style", "<script", "skew")
        for name in PRIVATE_FILES:
            self.assertTrue((ACTIVITY_DIR / "assets" / "runtime" / name).is_file(), name)
            self.assertTrue((ACTIVITY_DIR / "assets" / "source" / name.replace(".png", ".svg")).is_file(), name)
        for source in (ACTIVITY_DIR / "assets" / "source").glob("*.svg"):
            text = source.read_text(encoding="utf-8")
            self.assertLessEqual(len(text.encode("utf-8")), 6 * 1024, source.name)
            for token in forbidden:
                self.assertNotIn(token, text, f"{source.name}: {token}")

    def test_every_need_has_exactly_one_care_and_the_tray_covers_the_level(self) -> None:
        self.assertEqual(set(CARE_FOR_NEED), set(Need))
        self.assertEqual(set(CARE_FOR_NEED.values()), set(Care))
        for level in LEVELS:
            for need in level.pool:
                self.assertIn(CARE_FOR_NEED[need], level.tray)
            self.assertIn(Care.BED, level.tray)
            self.assertEqual(tuple(care for care in TRAY_ORDER if care in level.tray), level.tray)

    def test_targets_are_big_and_clear_of_chrome_and_lilli(self) -> None:
        chrome, lilli = _chrome(), _lilli()
        rects = [*tray_rects(len(TRAY_ORDER)), *adopt_rects(len(SPECIES)), *name_rects(len(NAMES)), CONFIRM_RECT]
        rects += [stage.target for stage in STAGES.values()]
        screen = pygame.Rect(0, 0, REFERENCE_WIDTH, REFERENCE_HEIGHT)
        for rect in rects:
            with self.subTest(rect=rect):
                self.assertGreaterEqual(min(rect.size), 96)
                self.assertTrue(screen.contains(rect))
                self.assertFalse(rect.colliderect(chrome))
                self.assertFalse(rect.colliderect(lilli))

    def test_rooms_compose_once_and_art_is_cached(self) -> None:
        art = CuccioloArt()
        for room in Room:
            surface = art.room(room)
            self.assertEqual(surface.get_size(), (REFERENCE_WIDTH, REFERENCE_HEIGHT))
            self.assertNotEqual(surface.get_at((512, 60))[:3], surface.get_at((512, 560))[:3])  # wall vs floor
        self.assertIs(art.room(Room.BEDROOM), art.room(Room.BEDROOM))
        for species in SPECIES:
            for care in Care:
                icon = art.care_icon(care, species.species_id, 88)
                self.assertIsNotNone(icon, (species.species_id, care))
                self.assertIs(art.care_icon(care, species.species_id, 88), icon)
        faded = art.pet_fading("puppy", "dirty", 300, 85)
        self.assertIs(art.pet_fading("puppy", "dirty", 300, 85), faded)


class RulesTests(unittest.TestCase):
    def test_days_end_at_bedtime_vary_and_stay_in_the_level_pool(self) -> None:
        for index, level in enumerate(LEVELS):
            for seed in range(40):
                needs = plan_day(index, random.Random(seed))
                self.assertEqual(len(needs), level.daytime_needs + 1)
                self.assertIs(needs[-1], Need.SLEEPY)
                daytime = needs[:-1]
                self.assertTrue(set(daytime) <= set(level.pool))
                self.assertTrue(all(a is not b for a, b in zip(daytime, daytime[1:])))
                self.assertGreaterEqual(len(set(daytime)), 2)
        seen = {need for seed in range(40) for need in plan_day(MAX_LEVEL, random.Random(seed))}
        self.assertEqual(seen, set(Need))

    def test_a_wrong_care_is_a_kind_not_now_that_changes_nothing(self) -> None:
        day = CareDay((Need.HUNGRY, Need.SLEEPY), 0)
        self.assertIs(day.offer(Care.FOOD).offer, Offer.IGNORED)  # nothing showing yet
        self.assertIs(day.emerge(), Need.HUNGRY)
        outcome = day.offer(Care.BATH)
        self.assertEqual((outcome.offer, outcome.need, outcome.misses), (Offer.NOT_NOW, Need.HUNGRY, 1))
        self.assertIs(day.phase, Phase.NEED)
        self.assertIs(day.current_need, Need.HUNGRY)  # nothing got worse
        self.assertIs(day.offer(Care.FOOD).offer, Offer.RIGHT)
        self.assertEqual(day.first_try, 0)
        self.assertIs(day.offer(Care.FOOD).offer, Offer.IGNORED)  # no double feeding

    def test_care_takes_its_steps_and_bedtime_finishes_the_day(self) -> None:
        day = CareDay((Need.DIRTY, Need.SLEEPY), 1)
        day.emerge()
        day.offer(Care.BATH)
        self.assertIsNone(day.settle())  # not before the care is done
        for _ in range(CARES[Care.BATH].steps):
            self.assertTrue(day.act())
        self.assertFalse(day.act())
        self.assertIs(day.settle(), Need.DIRTY)
        self.assertIs(day.phase, Phase.CALM)
        self.assertIs(day.emerge(), Need.SLEEPY)
        self.assertTrue(day.is_bedtime)
        day.offer(Care.BED)
        while day.act():
            pass
        self.assertIs(day.settle(), Need.SLEEPY)
        self.assertTrue(day.done)
        self.assertEqual(day.cared, [Need.DIRTY, Need.SLEEPY])
        self.assertEqual(day.first_try, 2)
        with self.assertRaises(ValueError):
            CareDay((Need.HUNGRY,), 0)

    def test_ladder_adapts_from_misses(self) -> None:
        self.assertEqual(adapt_level(0, 0), 1)
        self.assertEqual(adapt_level(MAX_LEVEL, 1), MAX_LEVEL)
        self.assertEqual(adapt_level(1, 3), 1)
        self.assertEqual(adapt_level(2, 6), 1)
        self.assertEqual(adapt_level(0, 9), 0)
        counts = [level.daytime_needs for level in LEVELS]
        self.assertEqual(counts, sorted(counts))
        self.assertLess(len(LEVELS[0].tray), len(LEVELS[-1].tray))


class ProgressTests(unittest.TestCase):
    def test_legacy_save_migrates_species_and_keeps_the_accessory(self) -> None:
        legacy = {"species": "bunny", "accessory": "crown", "happiness": 5, "hunger": 2, "cleanliness": 4, "timestamp": 1.0}
        profile = GreiaPetProgress(FakeStorage(legacy)).load()
        self.assertEqual(profile, PetProfile(species="guinea_pig", accessory="crown"))
        self.assertFalse(profile.adopted)  # the child still names it
        self.assertEqual(parse_profile({"species": "cat"}).species, "kitten")
        self.assertEqual(parse_profile({"species": "dragon"}).species, None)

    def test_round_trip_and_corrupt_payloads(self) -> None:
        storage = FakeStorage()
        service = GreiaPetProgress(storage)
        profile = PetProfile(species="puppy", name="sun", level=2, days=3, cares=17, accessory="bow")
        service.save(profile)
        self.assertEqual(storage.values[STORAGE_KEY]["schema_version"], SCHEMA_VERSION)
        self.assertEqual(service.load(), profile)
        for raw in (None, [], "x", {"schema_version": SCHEMA_VERSION, "level": "9", "name": "rex", "days": -4}):
            parsed = parse_profile(raw)
            self.assertTrue(0 <= parsed.level <= MAX_LEVEL)
            self.assertIsNone(parsed.name)
            self.assertGreaterEqual(parsed.days, 0)
        payload = profile_payload(PetProfile(species="dragon", name="moon", level=99, days=-1, cares=-5))
        self.assertEqual(
            (payload["species"], payload["name"], payload["level"], payload["days"], payload["cares"]),
            (None, "moon", MAX_LEVEL, 0, 0),
        )
        self.assertNotIn("accessory", payload)

    def test_storage_failures_are_soft(self) -> None:
        broken = mock.Mock()
        broken.kv_get.side_effect = OSError("disk full")
        broken.kv_set.side_effect = OSError("disk full")
        service = GreiaPetProgress(broken)
        self.assertEqual(service.load(), PetProfile())
        service.save(PetProfile(species="puppy", name="moon"))  # does not raise


class AppLoopTests(unittest.TestCase):
    """Play real days through the shared kit input with an injected clock."""

    def setUp(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        self.clock = FakeClock()
        self.events = RecordedEvents()

    def make_app(self, profile: PetProfile | None = None, seed: int = 7, locale: str = "en") -> CuccioloApp:
        self.progress = MemoryProgress(profile)
        self.app = CuccioloApp(
            screen=self.screen,
            canvas=PygameReferenceCanvas(self.screen),
            typography=GreiaTypography(),
            resources=activity_resources(ACTIVITY_DIR, requested_locale=locale),
            audio=CuccioloAudio(locale=locale),
            progress=self.progress,
            events=self.events,
            rng=random.Random(seed),
            clock=self.clock,
            session_prefix="test",
        )
        return self.app

    def advance(self, seconds: float, step: float = 0.05) -> None:
        end = self.clock.now + seconds
        while self.clock.now < end:
            self.clock.now += step
            self.app.step()

    def wait_for_need(self, limit: float = 12.0) -> None:
        waited = 0.0
        while self.app.day.phase is not Phase.NEED and waited < limit:
            self.advance(0.25)
            waited += 0.25
        self.assertIs(self.app.day.phase, Phase.NEED)

    def care_until_done(self, *, by_key: bool = False) -> None:
        app = self.app
        guard = 0
        while app.day.phase is Phase.CARE and not app.day.care_finished and guard < 10:
            if by_key:
                self.assertEqual(app.controls.layer.focused_id, "pet")
                self.assertTrue(app.press(pygame.K_RETURN))
            else:
                self.assertTrue(app.tap(app.controls.pet.rect.center))
            app.render()
            self.advance(1.1)
            guard += 1
        waited = 0.0
        while app.day.phase is Phase.CARE and waited < 3.0:
            self.advance(0.1)
            waited += 0.1
        self.assertIsNot(app.day.phase, Phase.CARE)

    def focus(self, control_id: str) -> None:
        app = self.app
        for _ in range(16):
            if app.controls.layer.focused_id == control_id:
                return
            for key in (pygame.K_LEFT, pygame.K_UP, pygame.K_RIGHT, pygame.K_DOWN):
                app.press(key)
                if app.controls.layer.focused_id == control_id:
                    return
        target = app.controls.layer.target(control_id).rect
        current = app.controls.layer.target(app.controls.layer.focused_id).rect
        key = pygame.K_RIGHT if target.centerx > current.centerx else pygame.K_LEFT
        for _ in range(8):
            if app.controls.layer.focused_id == control_id:
                return
            app.press(key)
        self.assertEqual(app.controls.layer.focused_id, control_id)

    def test_first_visit_adopts_names_and_plays_a_whole_day(self) -> None:
        app = self.make_app()
        self.advance(0.5)
        app.render()
        self.assertIs(app.screen_id, Screen.ADOPT)
        self.assertFalse(app.tap(app.controls.confirm.rect.center))  # nothing chosen yet
        self.assertTrue(app.tap(app.controls.species_cards[0].rect.center))
        self.assertTrue(app.tap(app.controls.confirm.rect.center))
        self.assertIs(app.screen_id, Screen.NAME)
        self.assertTrue(app.tap(app.controls.name_tags[1].rect.center))
        app.render()
        self.assertTrue(app.tap(app.controls.confirm.rect.center))
        self.assertIs(app.screen_id, Screen.DAY)
        self.assertEqual((self.progress.saved.species, self.progress.saved.name), ("puppy", "sun"))
        day = app.day
        self.assertEqual(app.controls.progress.total, day.total)
        first = True
        while not day.done:
            self.wait_for_need()
            need = day.current_need
            self.assertEqual(app.variant, need.value)  # the need shows only as body language
            right = CARE_FOR_NEED[need]
            if first:
                # A wrong care: the pet shakes its head, Lilli thinks, nothing changes.
                wrong = next(care for care in app.controls.visible_tray if care is not right)
                self.assertTrue(app.tap(app.controls.tray_rect(wrong).center))
                self.assertEqual(app.cast.pose.value, "think")
                self.assertIs(day.current_need, need)
                app.render()
                self.advance(0.8)
                first = False
            self.assertTrue(app.tap(app.controls.tray_rect(right).center))
            self.assertEqual(app.cast.pose.value, "cheer")
            app.render()
            self.advance(1.4)  # the room slides in
            self.assertIs(app.room, CARES[right].room)
            self.care_until_done()
            self.advance(0.2)
        self.assertTrue(app.dim)  # lights off at bedtime
        self.advance(2.5)
        self.assertIs(app.screen_id, Screen.END)
        self.assertEqual(len(self.events.days), 1)
        self.assertEqual(self.events.days[0]["misses"], 1)
        self.assertEqual(len(self.events.cares), day.total - 1)
        self.assertEqual({event for event, _ in self.events.cares} - {k.event_id for k in CARES.values()}, set())
        saved = self.progress.saved
        self.assertEqual((saved.level, saved.days, saved.cares), (1, 1, day.total))
        app.render()
        self.assertEqual(app.controls.progress.current, day.total)
        # "New day" on the shared completion scene starts the next, harder day.
        self.assertTrue(app.tap(app.completion.primary_rect.center))
        self.assertIs(app.screen_id, Screen.DAY)
        self.assertEqual(app.day.level, 1)
        self.assertEqual(app.controls.progress.current, 0)

    def test_returning_pet_starts_the_day_and_keyboard_plays_it(self) -> None:
        app = self.make_app(PetProfile(species="kitten", name="moon"), seed=3)
        self.assertIs(app.screen_id, Screen.DAY)
        day = app.day
        while not day.done:
            self.wait_for_need()
            self.focus(care_id(CARE_FOR_NEED[day.current_need]))
            self.assertTrue(app.press(pygame.K_RETURN))
            self.advance(1.4)
            self.care_until_done(by_key=True)
            self.advance(0.2)
        self.advance(2.5)
        self.assertIs(app.screen_id, Screen.END)
        self.assertTrue(app.press(pygame.K_RETURN))
        self.assertIs(app.screen_id, Screen.DAY)

    def test_adoption_by_keyboard(self) -> None:
        app = self.make_app()
        self.focus("species.guinea_pig")
        self.assertTrue(app.press(pygame.K_RETURN))
        self.focus("confirm")
        self.assertTrue(app.press(pygame.K_RETURN))
        self.focus("name.apple")
        self.assertTrue(app.press(pygame.K_SPACE))
        self.focus("confirm")
        self.assertTrue(app.press(pygame.K_RETURN))
        self.assertEqual((self.progress.saved.species, self.progress.saved.name), ("guinea_pig", "apple"))

    def test_legacy_pet_is_preselected_but_must_be_named(self) -> None:
        app = self.make_app(PetProfile(species="kitten", accessory="crown"))
        self.assertIs(app.screen_id, Screen.ADOPT)
        self.assertTrue(app.controls.confirm.enabled)
        self.assertTrue(app.tap(app.controls.confirm.rect.center))
        self.assertIs(app.screen_id, Screen.NAME)
        self.assertFalse(app.controls.confirm.enabled)
        app.tap(app.controls.name_tags[0].rect.center)
        app.tap(app.controls.confirm.rect.center)
        self.assertEqual(self.progress.saved, PetProfile(species="kitten", name="moon", accessory="crown"))

    def test_waiting_never_makes_things_worse_and_hints_are_graduated(self) -> None:
        app = self.make_app(PetProfile(species="puppy", name="moon"))
        self.wait_for_need()
        need = app.day.current_need
        right = CARE_FOR_NEED[need]
        self.advance(6.3)
        self.assertTrue(app.cast.pointing)
        self.assertFalse(app.motion.glowing(right, self.clock.now))
        self.advance(6.3)
        self.assertFalse(app.motion.glowing(right, self.clock.now))
        self.advance(6.3)
        self.assertTrue(app.motion.glowing(right, self.clock.now))
        self.advance(60.0)
        self.assertIs(app.day.current_need, need)
        self.assertEqual(app.day.misses, 0)
        self.assertEqual(app.variant, need.value)

    def test_touching_the_pet_replays_its_body_language_without_a_choice(self) -> None:
        app = self.make_app(PetProfile(species="kitten", name="sun"))
        self.wait_for_need()
        self.advance(1.5)
        before = app.motion.tell_start
        self.assertTrue(app.tap(app.controls.pet.rect.center))
        self.assertGreater(app.motion.tell_start, before)
        self.assertIs(app.day.phase, Phase.NEED)
        self.assertEqual(app.day.misses, 0)

    def test_second_miss_makes_the_right_care_glow(self) -> None:
        app = self.make_app(PetProfile(species="puppy", name="moon"))
        self.wait_for_need()
        right = CARE_FOR_NEED[app.day.current_need]
        wrong = next(care for care in app.controls.visible_tray if care is not right)
        app.tap(app.controls.tray_rect(wrong).center)
        self.advance(0.8)
        self.assertFalse(app.motion.glowing(right, self.clock.now))
        app.tap(app.controls.tray_rect(wrong).center)
        self.advance(0.8)
        self.assertTrue(app.motion.glowing(right, self.clock.now))

    def test_taps_in_the_protected_chrome_and_while_calm_are_ignored(self) -> None:
        app = self.make_app(PetProfile(species="puppy", name="moon"))
        chrome = _chrome()
        self.assertIs(app.day.phase, Phase.CALM)
        self.assertFalse(app.tap(app.controls.tray_rect(Care.FOOD).center))
        self.wait_for_need()
        self.assertFalse(app.tap((chrome.x + 4, chrome.y + 4)))
        self.assertIs(app.day.phase, Phase.NEED)

    def test_frames_render_at_every_supported_size_without_per_frame_scaling(self) -> None:
        app = self.make_app(PetProfile(species="guinea_pig", name="flower"))
        self.wait_for_need()
        for size in ((1024, 600), (800, 480), (480, 320)):
            with self.subTest(size=size):
                screen = pygame.display.set_mode(size)
                app.screen = screen
                app._resize()
                self.advance(0.5)
                app.render()
                app.canvas.present()
                with mock.patch("pygame.transform.smoothscale", side_effect=AssertionError("per-frame scale")):
                    for _ in range(5):
                        self.clock.now += 0.04
                        app.step()
                        app.render()


if __name__ == "__main__":
    unittest.main()
