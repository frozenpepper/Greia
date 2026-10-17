"""The Big Seasons Tree (Il Grande Albero delle Stagioni): facts, rules, art, app loop.

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

from activities.quattro_stagioni.tree_app import AppState, TreeActivity
from activities.quattro_stagioni.tree_art import POSE_TRANSFORMS, SeasonsArt
from activities.quattro_stagioni.tree_audio import TreeAudio
from activities.quattro_stagioni.tree_content import (
    CORE_SLOTS,
    EMBLEMS,
    ITEMS,
    LEVELS,
    MAX_LEVEL,
    REFERENCE_HEIGHT,
    REFERENCE_WIDTH,
    SCENES,
    SEASONS,
    SLOT_ICONS,
    STORAGE_KEY,
    Season,
    Slot,
    plan_missions,
    right_items,
    slot_available,
    wrong_items,
)
from activities.quattro_stagioni.tree_layout import (
    CARD_SIZE,
    SLOT_SPOTS,
    TILE_SIZE,
    TITO_TAP_RECT,
    TREE_TAP_RECT,
    row_rects,
)
from activities.quattro_stagioni.tree_model import DressRound, Pick, adapt_level
from activities.quattro_stagioni.tree_services import (
    SCHEMA_VERSION,
    GreiaSeasonsProgress,
    SeasonsProgress,
    parse_progress,
    progress_payload,
)
from greia_platform.activity_api import get_shared_visual_path
from greia_platform.localization import activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.system_chrome import ActivitySystemChromeLayout
from greia_platform.typography import GreiaTypography

ACTIVITY_DIR = PROJECT_ROOT / "activities" / "quattro_stagioni"
LOCALES = ("en", "it", "es", "fr")
SP, SU, AU, WI = Season.SPRING, Season.SUMMER, Season.AUTUMN, Season.WINTER


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class MemoryProgress:
    def __init__(self, progress: SeasonsProgress | None = None) -> None:
        self.saved = progress or SeasonsProgress()
        self.saves = 0

    def load(self) -> SeasonsProgress:
        return self.saved

    def save(self, progress: SeasonsProgress) -> None:
        self.saved = progress
        self.saves += 1


class RecordedEvents:
    def __init__(self) -> None:
        self.dressed: list[dict] = []
        self.all_seasons: list[dict] = []

    def season_dressed(self, session_id: str, payload: dict) -> None:
        self.dressed.append(payload)

    def all_seasons_dressed(self, session_id: str, payload: dict) -> None:
        self.all_seasons.append(payload)


class FakeStorage:
    def __init__(self, value=None) -> None:
        self.values = {STORAGE_KEY: value} if value is not None else {}

    def kv_get(self, key):
        return self.values.get(key)

    def kv_set(self, key, value) -> None:
        self.values[key] = value


def _bundle(locale: str) -> dict:
    return json.loads((ACTIVITY_DIR / "locales" / f"{locale}.json").read_text(encoding="utf-8"))


class ManifestAndLocaleTests(unittest.TestCase):
    def test_manifest_matches_the_gameplay(self) -> None:
        with (ACTIVITY_DIR / "activity.toml").open("rb") as handle:
            data = tomllib.load(handle)
        self.assertEqual(data["activity"]["id"], "org.greia.quattro-stagioni")
        self.assertEqual(data["activity"]["legacy_ids"], ["quattro_stagioni"])
        self.assertEqual(sorted(data["activity"]["languages"]), ["en", "es", "fr", "it"])  # four released languages (owner 2026-10-17)
        self.assertEqual(data["presentation"]["categories"], ["explore", "learn"])
        self.assertEqual(data["input"]["profile"], "hybrid")
        education = data["education"]
        self.assertEqual((education["recommended_age_min"], education["recommended_age_max"]), (3, 5))
        self.assertTrue(education["adaptive_difficulty"])
        self.assertEqual(education["difficulty_max"], len(LEVELS))
        skills = {skill["id"] for skill in education["skills"]}
        self.assertIn("nature.seasons.awareness", skills)
        self.assertIn("nature.weather.recognition", skills)
        self.assertNotIn("nature.cycles.day_night", skills)  # no day/night toy any more
        events = {event["id"]: event["kind"] for event in education["events"]}
        self.assertEqual(
            events,
            {
                "quattro_stagioni.season_dressed": "completion",
                "quattro_stagioni.all_seasons_discovered": "milestone",
            },
        )

    def test_four_locales_have_key_parity_and_every_content_key(self) -> None:
        english = _bundle("en")["strings"]
        required = {"activity.title", "activity.quattro_stagioni.title", "victory.title", "btn.play_again", "prompt.choose_season"}
        required |= {season.name_key for season in SEASONS}
        required |= {f"ready.{season.value}" for season in SEASONS}
        required |= {slot.prompt_key for slot in Slot}
        required |= {item.name_key for item in ITEMS.values()}
        self.assertTrue(required <= set(english), required - set(english))
        for locale in LOCALES:
            with self.subTest(locale=locale):
                strings = _bundle(locale)["strings"]
                self.assertEqual(set(strings), set(english))
                self.assertTrue(all(value.strip() for value in strings.values()))
                for slot in Slot:
                    self.assertIn("$season", strings[slot.prompt_key])

    def test_text_is_capitalised_and_prompts_name_the_season(self) -> None:
        resources = activity_resources(ACTIVITY_DIR, requested_locale="it")
        season = resources.text("season.winter")
        self.assertEqual(resources.text("prompt.tree", {"season": season}), "INVERNO: L'ALBERO")
        self.assertEqual(resources.text("ready.autumn"), "L'AUTUNNO È PRONTO!")

    def test_audio_bundle_keeps_the_approved_title_clip(self) -> None:
        for locale in ("en", "it"):
            audio = _bundle(locale)["audio"]
            self.assertEqual(audio["activity.title"]["path"], f"locales/{locale}/audio/activity-title.wav")
            self.assertTrue((ACTIVITY_DIR / audio["activity.title"]["path"]).is_file())


class SeasonFactsTests(unittest.TestCase):
    """Every question has exactly one card that belongs, and no wrong facts."""

    def test_no_item_is_both_right_and_wrong(self) -> None:
        for item in ITEMS.values():
            self.assertFalse(item.belongs & item.wrong_for, item.item_id)
            self.assertTrue(item.belongs, item.item_id)

    def test_audit_bugs_cannot_happen(self) -> None:
        # Autumn leaves in summer, snow outside winter, an orange tree in summer.
        self.assertTrue(ITEMS["wind"].clashes(SU))
        for season in (SP, SU, AU):
            self.assertTrue(ITEMS["snow"].clashes(season))
            self.assertTrue(ITEMS["snowman"].clashes(season))
            self.assertTrue(ITEMS["tree_snowy"].clashes(season))
        self.assertTrue(ITEMS["tree_orange"].clashes(SU))
        self.assertTrue(ITEMS["tree_blossom"].clashes(WI))
        self.assertTrue(ITEMS["sunhat"].clashes(WI))
        self.assertTrue(ITEMS["winter_hat"].clashes(SU))
        self.assertTrue(ITEMS["butterfly"].clashes(WI))
        self.assertTrue(ITEMS["hedgehog_asleep"].clashes(SU))

    def test_true_sometimes_facts_are_never_marked_wrong(self) -> None:
        self.assertFalse(ITEMS["tree_apples"].clashes(AU))  # autumn apple harvest
        self.assertFalse(ITEMS["rain"].clashes(SU))  # summer storms
        self.assertFalse(ITEMS["sun"].clashes(WI))  # sunny winter days
        self.assertTrue(ITEMS["sun"].fits(SP) and ITEMS["rain"].fits(SP))

    def test_every_season_has_the_core_missions(self) -> None:
        for season in SEASONS:
            for slot in CORE_SLOTS:
                with self.subTest(season=season, slot=slot):
                    self.assertTrue(slot_available(season, slot))
        self.assertTrue(slot_available(WI, Slot.CLOTHES) and slot_available(SU, Slot.CLOTHES))
        self.assertTrue(slot_available(SP, Slot.ANIMAL) and slot_available(WI, Slot.ANIMAL))
        # No clear-cut clothes or animals for the in-between seasons: never asked.
        self.assertFalse(slot_available(SP, Slot.CLOTHES))
        self.assertFalse(slot_available(AU, Slot.ANIMAL))

    def test_missions_have_one_answer_and_only_clearly_wrong_options(self) -> None:
        rng = random.Random(3)
        for _ in range(40):
            for season in SEASONS:
                for level, ladder in enumerate(LEVELS):
                    missions = plan_missions(season, level, rng)
                    self.assertEqual(missions[0].slot, Slot.TREE)
                    self.assertLessEqual(len(missions), ladder.missions)
                    self.assertGreaterEqual(len(missions), 3)
                    for mission in missions:
                        right = [o for o in mission.options if ITEMS[o].fits(season)]
                        self.assertEqual(right, [mission.answer])
                        for option in mission.options:
                            self.assertEqual(ITEMS[option].slot, mission.slot)
                            if option != mission.answer:
                                self.assertTrue(ITEMS[option].clashes(season), (season, option))
                        self.assertGreaterEqual(len(mission.options), 2)
                        self.assertLessEqual(len(mission.options), ladder.options)
                        self.assertEqual(len(set(mission.options)), len(mission.options))

    def test_ladder_grows_missions_and_cards(self) -> None:
        rng = random.Random(5)
        easy = plan_missions(WI, 0, rng)
        hard = plan_missions(WI, MAX_LEVEL, rng)
        self.assertEqual(len(easy), 3)
        self.assertEqual(len(hard), 5)
        self.assertTrue(all(len(m.options) == 2 for m in easy))
        self.assertEqual(len(hard[0].options), 4)  # four trees fit
        self.assertEqual(right_items(SU, Slot.SKY)[0].item_id, "sun")
        self.assertEqual({i.item_id for i in wrong_items(WI, Slot.SKY)}, {"wind"})


class RulesTests(unittest.TestCase):
    def test_right_card_places_and_moves_on(self) -> None:
        round_ = DressRound(WI, 0, random.Random(1))
        mission = round_.mission
        outcome = round_.choose(mission.answer)
        self.assertIs(outcome.pick, Pick.RIGHT)
        self.assertEqual(round_.placed[mission.slot], mission.answer)
        self.assertEqual(round_.index, 1)
        self.assertEqual(round_.first_try, 1)

    def test_wrong_card_is_a_kind_miss_and_cannot_count_twice(self) -> None:
        round_ = DressRound(SU, 1, random.Random(2))
        mission = round_.mission
        wrong = next(option for option in mission.options if option != mission.answer)
        self.assertIs(round_.choose(wrong).pick, Pick.WRONG)
        self.assertIs(round_.choose(wrong).pick, Pick.IGNORED)  # greyed card
        self.assertIs(round_.choose("not-a-card").pick, Pick.IGNORED)
        self.assertEqual((round_.misses, round_.task_misses), (1, 1))
        self.assertIs(round_.choose(mission.answer).pick, Pick.RIGHT)
        self.assertEqual(round_.first_try, 0)
        self.assertEqual(round_.task_misses, 0)

    def test_round_completes_and_ignores_more_picks(self) -> None:
        round_ = DressRound(AU, 3, random.Random(4))
        while not round_.complete:
            round_.choose(round_.mission.answer)
        self.assertEqual(len(round_.placed), round_.total)
        self.assertIs(round_.choose("tree_orange").pick, Pick.IGNORED)

    def test_ladder_adapts_from_misses(self) -> None:
        self.assertEqual(adapt_level(0, 0), 1)
        self.assertEqual(adapt_level(MAX_LEVEL, 1), MAX_LEVEL)
        self.assertEqual(adapt_level(2, 2), 2)
        self.assertEqual(adapt_level(2, 5), 1)
        self.assertEqual(adapt_level(0, 9), 0)


class ProgressTests(unittest.TestCase):
    def test_round_trip_and_corrupt_payloads(self) -> None:
        progress = SeasonsProgress(level=2, dressed=(SP, WI), last=WI, rounds=7)
        payload = progress_payload(progress)
        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        self.assertEqual(parse_progress(payload), progress)
        for raw in (None, [], "x", {"schema_version": 99, "level": 3}, {"schema_version": 1, "level": "3"}):
            with self.subTest(raw=raw):
                self.assertEqual(parse_progress(raw).level, 0)
        clamped = parse_progress({"schema_version": 1, "level": 99, "dressed": ["winter", "nope"], "last": "nope", "rounds": -4})
        self.assertEqual((clamped.level, clamped.dressed, clamped.last, clamped.rounds), (MAX_LEVEL, (WI,), None, 0))

    def test_storage_adapter_is_fail_soft(self) -> None:
        storage = FakeStorage()
        adapter = GreiaSeasonsProgress(storage)
        self.assertEqual(adapter.load(), SeasonsProgress())
        adapter.save(SeasonsProgress(level=1, dressed=(SU,)))
        self.assertEqual(storage.values[STORAGE_KEY]["dressed"], ["summer"])
        self.assertEqual(adapter.load().level, 1)

    def test_picker_focuses_the_next_season_to_dress(self) -> None:
        self.assertIs(SeasonsProgress().next_season(), SP)
        self.assertIs(SeasonsProgress(dressed=(SP, SU)).next_season(), AU)
        self.assertIs(SeasonsProgress(dressed=SEASONS, last=AU).next_season(), WI)


class ContentAndArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT))

    def _refs(self):
        for item in ITEMS.values():
            for layer in item.card:
                yield layer.art
            if item.scene is not None:
                yield item.scene
        for layers in SLOT_ICONS.values():
            for layer in layers:
                yield layer.art
        yield from EMBLEMS.values()

    def test_every_art_reference_resolves(self) -> None:
        for ref in self._refs():
            with self.subTest(ref=ref.key):
                if ref.file is not None:
                    self.assertTrue((ACTIVITY_DIR / "assets" / "runtime" / ref.file).is_file())
                    source = ACTIVITY_DIR / "assets" / "source" / ref.file.replace(".png", ".svg")
                    self.assertTrue(source.is_file(), source)
                else:
                    self.assertTrue(get_shared_visual_path(ref.asset_id, variant=ref.variant).is_file())
        for kit in SCENES.values():
            for layer in (kit.sky, *kit.layers):
                self.assertTrue(get_shared_visual_path(layer).is_file(), layer)
        for variant in POSE_TRANSFORMS:
            self.assertTrue(get_shared_visual_path("character.tito", variant=variant).is_file(), variant)

    def test_canonical_cast_only(self) -> None:
        # Tito is the shared canonical character; the package never draws a fox.
        for source in (ACTIVITY_DIR / "assets" / "source").glob("*.svg"):
            self.assertNotIn("fox", source.name)
        code = "".join(path.read_text(encoding="utf-8") for path in ACTIVITY_DIR.glob("*.py"))
        self.assertNotIn("pygame.draw.circle(surface, (2", code)
        self.assertIn('CastFeedback("tito"', code)

    def test_private_svgs_follow_the_authoring_lint(self) -> None:
        forbidden = ("<image", "data:", "<text", "<filter", "<mask", "<pattern", "<style", "<script", "skew", "#000000")
        sources = list((ACTIVITY_DIR / "assets" / "source").glob("*.svg"))
        self.assertGreaterEqual(len(sources), 10)
        for source in sources:
            text = source.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, text, f"{source.name}: {token}")

    def test_worn_clothes_follow_every_pose(self) -> None:
        art = SeasonsArt()
        for item_id in ("winter_hat", "scarf", "sunhat"):
            for variant in ("happy", "pose_cheer", "pose_think", "pose_point"):
                layer = art.wear(ITEMS[item_id], variant)
                self.assertIsNotNone(layer, (item_id, variant))
                self.assertIs(art.wear(ITEMS[item_id], variant), layer)  # cached once
        _, offset = art.wear(ITEMS["winter_hat"], "pose_cheer")
        self.assertLess(offset[1], 0)  # the cheer hop lifts the hat with Tito

    def test_season_sky_has_no_painted_sun(self) -> None:
        art = SeasonsArt()
        backdrop = art.backdrop(SP)
        self.assertIs(art.backdrop(SP), backdrop)
        # The meadow sky layer paints its sun near (930, 30); the rebuilt sky does not.
        colour = backdrop.get_at((930, 28))
        self.assertGreater(colour.b, colour.r)

    def test_layout_is_clear_of_chrome_and_touch_sized(self) -> None:
        protected = ActivitySystemChromeLayout.for_surface(REFERENCE_WIDTH, REFERENCE_HEIGHT).protected_region
        chrome = pygame.Rect(protected.x, protected.y, protected.width, protected.height)
        rects = [*row_rects(4, CARD_SIZE), *row_rects(4, TILE_SIZE), TREE_TAP_RECT, TITO_TAP_RECT]
        rects += [spot.glow for spot in SLOT_SPOTS.values()]
        for rect in rects:
            self.assertFalse(rect.colliderect(chrome), rect)
            self.assertTrue(pygame.Rect(0, 0, REFERENCE_WIDTH, REFERENCE_HEIGHT).contains(rect), rect)
        for rect in row_rects(4, CARD_SIZE):
            self.assertFalse(rect.colliderect(TITO_TAP_RECT))
            # 480x320 is the smallest screen: cards stay above the 40 px touch floor.
            self.assertGreaterEqual(rect.height * 320 / REFERENCE_HEIGHT, 40)


class AudioTests(unittest.TestCase):
    def test_audio_finds_the_approved_clips_and_stays_silent_otherwise(self) -> None:
        pygame.mixer.init()
        resources = activity_resources(ACTIVITY_DIR, requested_locale="it")
        audio = TreeAudio(resources=resources, locale="it")
        for cue in ("welcome", "spring", "summer", "autumn", "winter", "sun", "rain", "wind", "snow", "praise_1"):
            self.assertTrue(audio.has_clip(cue), cue)
        self.assertFalse(audio.has_clip("day_and_night"))
        self.assertFalse(audio.say("not-a-clip"))
        self.assertTrue(audio.say_name("snowman"))  # shared vocab bank clip (2026-10-17)
        self.assertEqual(audio.last_speech, "vocab.snowman")
        self.assertFalse(audio.say_name("unicorn"))  # no recording: silent

    def test_audio_without_mixer_fails_soft(self) -> None:
        with mock.patch("pygame.mixer.get_init", return_value=None):
            audio = TreeAudio(locale="en")
        self.assertFalse(audio.say("winter"))
        self.assertFalse(audio.tito("ready.go"))
        audio.play("pop")
        audio.stop_speech()


class AppLoopTests(unittest.TestCase):
    """Play real rounds through the shared kit input with an injected clock."""

    def setUp(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        self.clock = FakeClock()
        self.progress = MemoryProgress()
        self.events = RecordedEvents()
        self.resources = activity_resources(ACTIVITY_DIR, requested_locale="en")
        self.app = self._make()

    def _make(self, progress: MemoryProgress | None = None) -> TreeActivity:
        return TreeActivity(
            screen=self.screen,
            canvas=PygameReferenceCanvas(self.screen),
            typography=GreiaTypography(),
            resources=self.resources,
            audio=TreeAudio(resources=self.resources, locale="en"),
            progress=progress or self.progress,
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

    def pick_season(self, season: Season) -> None:
        self.assertTrue(self.app.tap(self.app.controls.tiles[season].rect.center))
        self.advance(1.0)

    def card_point(self, item_id: str) -> tuple[int, int]:
        index = self.app.round.mission.options.index(item_id)
        return self.app.controls.card_rect(index).center

    def answer(self) -> str:
        return self.app.round.mission.answer

    def wrong(self) -> str:
        mission = self.app.round.mission
        return next(option for option in mission.options if option != mission.answer and option not in self.app.round.tried)

    def test_round_plays_to_completion_with_feedback_and_restart(self) -> None:
        app = self.app
        self.assertEqual(app.state, AppState.PICK)
        app.render()
        self.pick_season(WI)
        self.assertEqual(app.state, AppState.PLAYING)
        self.assertEqual(app.round.season, WI)
        self.assertEqual(app.round.mission.slot, Slot.TREE)
        self.assertEqual(app.controls.banner.text, "WINTER: THE TREE")
        # A card that does not belong: tried in the scene, comes back greyed; Tito thinks.
        wrong = self.wrong()
        self.assertTrue(app.tap(self.card_point(wrong)))
        index = app.round.mission.options.index(wrong)
        self.assertFalse(app.controls.cards[index].enabled)
        self.advance(0.5)
        app.render()
        self.assertEqual(app.cast.pose.value, "think")
        self.advance(1.0)
        answer_index = app.round.mission.options.index(self.answer())
        self.assertIn(answer_index, app.motion.card_hops)  # the right card hops
        self.assertEqual(app.round.misses, 1)
        done = 0
        while app.state is AppState.PLAYING:
            if app._busy:
                self.advance(0.1)
                continue
            mission = app.round.mission
            self.assertTrue(app.tap(self.card_point(mission.answer)))
            done += 1
            self.advance(0.5)
            app.render()
            self.assertEqual(app.cast.pose.value, "cheer")
            self.assertEqual(app.round.placed[mission.slot], mission.answer)
            self.assertEqual(app.controls.progress.current, done)
        self.assertEqual(app.state, AppState.FINALE)
        self.assertIsNotNone(app.renderer.weather)  # snow keeps falling in the finale
        self.advance(3.2)
        self.assertEqual(app.state, AppState.TERMINAL)
        self.assertEqual(len(self.events.dressed), 1)
        self.assertEqual(self.events.dressed[0]["season"], "winter")
        self.assertEqual(self.events.dressed[0]["misses"], 1)
        self.assertEqual(self.progress.saved.dressed, (WI,))
        self.assertEqual(self.progress.saved.level, 1)  # one miss -> climbs
        self.assertEqual(self.progress.saved.rounds, 1)
        app.render()
        # Play again from the shared completion scene: back to the picker,
        # the next season still to dress is focused and winter wears a star.
        self.assertTrue(app.tap(app.completion.primary_rect.center))
        self.assertEqual(app.state, AppState.PICK)
        self.assertEqual(app.controls.layer.focused_id, "season.spring")

    def test_keyboard_only_round(self) -> None:
        app = self.app
        self.advance(0.5)
        # The picker focuses spring; one step right is summer.
        self.assertEqual(app.controls.layer.focused_id, "season.spring")
        app.press(pygame.K_RIGHT)
        self.assertTrue(app.press(pygame.K_RETURN))
        self.advance(1.0)
        self.assertEqual(app.round.season, SU)
        while app.state is AppState.PLAYING:
            if app._busy:
                self.advance(0.1)
                continue
            mission = app.round.mission
            self.assertEqual(app.controls.layer.focused_id, "card.0")  # never the answer
            target = f"card.{mission.options.index(mission.answer)}"
            for _ in range(len(mission.options)):
                if app.controls.layer.focused_id == target:
                    break
                app.press(pygame.K_RIGHT)
            self.assertEqual(app.controls.layer.focused_id, target)
            self.assertTrue(app.press(pygame.K_RETURN))
            self.advance(0.6)
        self.advance(3.2)
        self.assertEqual(app.state, AppState.TERMINAL)
        self.assertTrue(app.press(pygame.K_RETURN))
        self.assertEqual(app.state, AppState.PICK)

    def test_all_four_seasons_unlock_the_milestone_once(self) -> None:
        app = self._make(MemoryProgress(SeasonsProgress(dressed=(SP, SU, AU))))
        self.app = app
        self.pick_season(WI)
        while app.state is not AppState.TERMINAL:
            if app.state is AppState.PLAYING and not app._busy:
                app.tap(self.card_point(self.answer()))
            self.advance(0.2)
        self.assertEqual(len(self.events.all_seasons), 1)
        app.tap(app.completion.primary_rect.center)
        self.pick_season(SP)
        while app.state is not AppState.TERMINAL:
            if app.state is AppState.PLAYING and not app._busy:
                app.tap(self.card_point(self.answer()))
            self.advance(0.2)
        self.assertEqual(len(self.events.all_seasons), 1)
        self.assertEqual(len(self.events.dressed), 2)

    def test_taps_in_the_protected_chrome_are_ignored(self) -> None:
        protected = ActivitySystemChromeLayout.for_surface(REFERENCE_WIDTH, REFERENCE_HEIGHT).protected_region
        self.assertFalse(self.app.tap((protected.x + 4, protected.y + 4)))
        self.assertEqual(self.app.state, AppState.PICK)

    def test_scene_taps_are_exploration_not_answers(self) -> None:
        app = self.app
        self.pick_season(SP)
        before = (app.round.index, app.round.misses)
        self.assertFalse(app.tap(TREE_TAP_RECT.center))
        self.assertGreater(app.motion.tree_shake, self.clock.now - 0.1)
        self.assertFalse(app.tap(TITO_TAP_RECT.center))
        self.assertEqual((app.round.index, app.round.misses), before)

    def test_idle_hints_point_then_show_the_card(self) -> None:
        app = self.app
        self.pick_season(AU)
        answer = app.round.mission.options.index(self.answer())
        self.advance(6.3)
        self.assertTrue(app.cast.pointing)
        self.assertIsNotNone(app.motion.slot_glow)
        self.assertNotIn(answer, app.motion.card_hops)
        # Back-off: the second hint comes 12 s after the first; a hop lasts 0.5 s.
        self.advance(11.8)
        self.assertIn(answer, app.motion.card_hops)

    def test_second_miss_glows_the_right_card(self) -> None:
        app = self.app
        self.pick_season(WI)
        # Winter weather has one wrong card; use the tree (three wrong ones at rung 2+).
        app.level = 2
        app.start_round(WI)
        self.advance(1.0)
        app.tap(self.card_point(self.wrong()))
        self.advance(1.4)
        self.assertIsNone(app.motion.card_glow)
        app.tap(self.card_point(self.wrong()))
        self.advance(1.4)
        self.assertIsNotNone(app.motion.card_glow)

    def test_frames_render_at_every_supported_size_without_per_frame_scaling(self) -> None:
        app = self.app
        self.pick_season(SU)
        app.tap(self.card_point(self.answer()))  # tree
        self.advance(2.5)
        app.tap(self.card_point(self.answer()))  # weather: the sun
        self.advance(2.5)
        for size in ((1024, 600), (800, 480), (480, 320)):
            with self.subTest(size=size):
                screen = pygame.display.set_mode(size)
                app.screen = screen
                app._resize()
                self.advance(0.5)
                app.render()
                app.canvas.present()
                with mock.patch("pygame.transform.smoothscale", side_effect=AssertionError("per-frame scale")), \
                        mock.patch("pygame.transform.rotate", side_effect=AssertionError("per-frame rotate")):
                    for _ in range(5):
                        self.clock.now += 0.04
                        app.step()
                        app.render()


if __name__ == "__main__":
    unittest.main()
