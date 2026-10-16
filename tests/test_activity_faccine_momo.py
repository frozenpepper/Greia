"""Momo's Happy Faces (Le Faccine di Momo): content, rules, saves, app loop.

Runs headlessly (SDL dummy drivers) against the real shared art catalogue and
the package's approved recordings, with an injected clock, in-memory progress
and recorded events, so no child profile data or windows are touched.
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
sys.dont_write_bytecode = True

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for entry in (PROJECT_ROOT, PROJECT_ROOT / "src"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import pygame

from activities.faccine_momo.momo_app import AppState, MomoActivity
from activities.faccine_momo.momo_art import MomoArt
from activities.faccine_momo.momo_audio import MomoAudio
from activities.faccine_momo.momo_content import (
    ALL_EMOTIONS,
    BACKDROP_LAYERS,
    CORE_EMOTIONS,
    FRIEND_CHARACTERS,
    GUIDE_CHARACTER,
    HELP_ITEMS,
    HELP_PLANS,
    LEVELS,
    MAX_LEVEL,
    MIRROR_ORDER,
    REFERENCE_HEIGHT,
    REFERENCE_WIDTH,
    STORAGE_KEY,
    STORIES,
    STORIES_BY_ID,
    TASKS_PER_VISIT,
    Emotion,
    Stage,
    stories_for,
)
from activities.faccine_momo.momo_controls import choice_id
from activities.faccine_momo.momo_layout import CARD_RECT, GUIDE_MIDBOTTOM, mirror_rects, tile_rects
from activities.faccine_momo.momo_model import MirrorWarmup, MomoVisit, Outcome, TaskFactory, adapt_level
from activities.faccine_momo.momo_services import (
    SCHEMA_VERSION,
    GreiaMomoProgress,
    MomoProgress,
    parse_progress,
    progress_payload,
)
from greia_platform.activity_api import get_shared_visual_path
from greia_platform.activity_controls import ControlKit, ControlLayout
from greia_platform.activity_feedback import CastPose
from greia_platform.localization import activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.typography import GreiaTypography

ACTIVITY_DIR = PROJECT_ROOT / "activities" / "faccine_momo"
LOCALES = ("en", "it", "es", "fr")
EMOTION_CUES = {emotion.value for emotion in Emotion}


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class MemoryProgress:
    def __init__(self, progress: MomoProgress | None = None) -> None:
        self.saved = progress or MomoProgress()
        self.saves = 0

    def load(self) -> MomoProgress:
        return self.saved

    def save(self, progress: MomoProgress) -> None:
        self.saved = progress
        self.saves += 1


class RecordedEvents:
    def __init__(self) -> None:
        self.discovered: list[str] = []
        self.completed: list[dict] = []

    def emotion_discovered(self, emotion: str) -> None:
        self.discovered.append(emotion)

    def visit_completed(self, session_id: str, payload: dict) -> None:
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


# ---------------------------------------------------------------- manifest/locales


class ManifestAndLocaleTests(unittest.TestCase):
    def test_manifest_matches_the_gameplay(self) -> None:
        data = tomllib.loads((ACTIVITY_DIR / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(data["activity"]["id"], "org.greia.faccine-momo")
        self.assertEqual(data["activity"]["legacy_ids"], ["faccine_momo"])
        self.assertEqual(data["activity"]["languages"], ["it", "en"])
        education = data["education"]
        self.assertEqual((education["recommended_age_min"], education["recommended_age_max"]), (3, 5))
        self.assertTrue(education["adaptive_difficulty"])
        self.assertEqual(education["difficulty_max"], MAX_LEVEL + 1)
        skills = {skill["id"] for skill in education["skills"]}
        self.assertIn("emotional.recognition.faces", skills)
        self.assertIn("emotional.understanding.situations", skills)
        self.assertIn("socioemotional.empathy.caring", skills)
        self.assertEqual(
            {(event["id"], event["kind"]) for event in education["events"]},
            {("faccine_momo.emotion_discovered", "milestone"), ("faccine_momo.visit_completed", "completion")},
        )
        self.assertEqual(data["input"]["profile"], "navigation")

    def test_four_locales_share_keys_and_name_every_feeling(self) -> None:
        reference = set(_strings("en"))
        for locale in LOCALES:
            strings = _strings(locale)
            with self.subTest(locale=locale):
                self.assertEqual(set(strings), reference)
                for emotion in Emotion:
                    self.assertTrue(strings[f"emotion.{emotion.value}"].strip())
                for key in ("complete.title", "complete.body", "button.play_again"):
                    self.assertTrue(strings[key].strip())
                for value in strings.values():
                    letters = [c for c in value if c.isalpha()]
                    if len(letters) >= 3:
                        self.assertNotEqual(value, value.upper(), "ADR 0034 cases at render time")

    def test_every_spoken_cue_is_an_approved_recording_in_en_and_it(self) -> None:
        needed = {"welcome", "game_prompt", "comfort", "praise_1", "praise_2", "praise_3", *EMOTION_CUES}
        for locale in ("en", "it"):
            with self.subTest(locale=locale):
                audio = ACTIVITY_DIR / "locales" / locale / "audio"
                for cue in needed:
                    self.assertTrue((audio / f"{cue}.wav").is_file(), cue)
                    self.assertTrue((audio / f"{cue}.wav.receipt.json").is_file(), cue)


# ---------------------------------------------------------------- content


class ContentTests(unittest.TestCase):
    def test_every_story_piece_and_help_item_resolves_to_real_art(self) -> None:
        for story in STORIES:
            for piece in story.pieces:
                with self.subTest(story=story.story_id, asset=piece.asset):
                    if piece.asset.startswith("private:"):
                        name = piece.asset.split(":", 1)[1]
                        self.assertTrue((ACTIVITY_DIR / "assets" / "runtime" / f"{name}.png").is_file())
                        self.assertTrue((ACTIVITY_DIR / "assets" / "source" / f"{name}.svg").is_file())
                    else:
                        self.assertTrue(get_shared_visual_path(piece.asset, variant=piece.variant).is_file())
        for backdrop, layers in BACKDROP_LAYERS.items():
            for layer in layers:
                with self.subTest(backdrop=backdrop, layer=layer):
                    self.assertTrue(get_shared_visual_path(layer).is_file())
        for item in HELP_ITEMS.values():
            for asset, variant in (item.stack or ((item.asset, item.variant),)):
                with self.subTest(item=item.item_id, asset=asset):
                    self.assertTrue(get_shared_visual_path(asset, variant=variant).is_file())
        for character in ("momo", GUIDE_CHARACTER, *FRIEND_CHARACTERS):
            for variant in (*EMOTION_CUES, "pose_cheer", "pose_think", "pose_point"):
                with self.subTest(character=character, variant=variant):
                    self.assertTrue(get_shared_visual_path(f"character.{character}", variant=variant).is_file())

    def test_story_feelings_never_list_themselves_as_alternatives(self) -> None:
        for story in STORIES:
            self.assertNotIn(story.emotion, story.also_fits, story.story_id)

    def test_every_level_can_build_one_sensible_answer_per_story(self) -> None:
        for level, plan in enumerate(LEVELS):
            self.assertEqual(len(plan.stages), TASKS_PER_VISIT)
            for story in stories_for(plan.pool):
                wrong = [e for e in plan.pool if e is not story.emotion and e not in story.also_fits]
                with self.subTest(level=level, story=story.story_id):
                    self.assertGreaterEqual(len(wrong), plan.explain_choices - 1)
            self.assertGreaterEqual(len(FRIEND_CHARACTERS), plan.recognise_choices)
            self.assertGreaterEqual(
                sum(1 for stage in plan.stages if stage is Stage.EXPLAIN) + sum(1 for stage in plan.stages if stage is Stage.HELP),
                2,
            )

    def test_help_plans_offer_one_kind_choice_and_unrelated_distractors(self) -> None:
        for plan in HELP_PLANS:
            with self.subTest(story=plan.story_id):
                self.assertIn(plan.story_id, STORIES_BY_ID)
                self.assertIn(plan.helper, HELP_ITEMS)
                self.assertNotIn(plan.helper, plan.distractors)
                self.assertGreaterEqual(len(plan.distractors), max(level.help_choices for level in LEVELS) - 1)
                for distractor in plan.distractors:
                    self.assertIn(distractor, HELP_ITEMS)
                    self.assertNotIn(distractor, {other.helper for other in HELP_PLANS if other.story_id == plan.story_id})

    def test_guide_is_never_a_recognise_friend(self) -> None:
        self.assertNotIn(GUIDE_CHARACTER, FRIEND_CHARACTERS)
        self.assertNotIn("momo", FRIEND_CHARACTERS)


# ---------------------------------------------------------------- model


class ModelTests(unittest.TestCase):
    def test_visits_follow_the_ladder_with_exactly_one_sensible_answer(self) -> None:
        for level, plan in enumerate(LEVELS):
            for seed in range(40):
                tasks = TaskFactory(random.Random(seed)).build_visit(level)
                with self.subTest(level=level, seed=seed):
                    self.assertEqual(tuple(task.stage for task in tasks), plan.stages)
                    stories = [task.story_id for task in tasks if task.story_id]
                    self.assertEqual(len(stories), len(set(stories)), "no story twice in one visit")
                    for task in tasks:
                        keys = [choice.key for choice in task.choices]
                        self.assertEqual(len(keys), plan.choices_for(task.stage))
                        self.assertEqual(len(set(keys)), len(keys))
                        self.assertEqual(keys.count(task.answer), 1)
                        if task.stage is Stage.RECOGNISE:
                            self.assertIn(task.feeling, plan.pool)
                            friends = [choice.character for choice in task.choices]
                            self.assertEqual(len(set(friends)), len(friends))
                            self.assertTrue(set(friends) <= set(FRIEND_CHARACTERS))
                        elif task.stage is Stage.EXPLAIN:
                            story = STORIES_BY_ID[task.story_id]
                            self.assertTrue(story.explain)
                            self.assertEqual(task.answer, story.emotion.value)
                            for key in keys:
                                self.assertNotIn(Emotion(key), story.also_fits)
                                self.assertIn(Emotion(key), plan.pool)
                        else:
                            plan_for = next(p for p in HELP_PLANS if p.story_id == task.story_id)
                            self.assertEqual(task.answer, plan_for.helper)
                            self.assertTrue(set(keys) - {task.answer} <= set(plan_for.distractors))

    def test_first_level_uses_only_core_feelings_and_two_choices(self) -> None:
        for seed in range(30):
            for task in TaskFactory(random.Random(seed)).build_visit(0):
                self.assertEqual(len(task.choices), 2)
                if task.stage is not Stage.HELP:
                    self.assertIn(Emotion(task.answer), CORE_EMOTIONS)

    def test_wrong_picks_are_set_aside_with_unlimited_kind_retries(self) -> None:
        tasks = TaskFactory(random.Random(4)).build_visit(2)
        visit = MomoVisit(tasks, level=2)
        task = visit.task
        wrong = [i for i, choice in enumerate(task.choices) if choice.key != task.answer]
        for index in wrong:
            self.assertIs(visit.choose(index), Outcome.TRY_AGAIN)
            self.assertIs(visit.choose(index), Outcome.IGNORED)
        self.assertIs(visit.choose(task.answer_index), Outcome.CORRECT)
        self.assertIs(visit.choose(task.answer_index), Outcome.IGNORED)
        self.assertFalse(visit.records[0].first_try)
        self.assertEqual(visit.records[0].misses, len(wrong))
        self.assertEqual(visit.completed_count, 1)
        self.assertTrue(visit.advance())
        self.assertEqual(visit.rejected, set())
        for _ in range(len(tasks) - 1):
            visit.choose(visit.task.answer_index)
            visit.advance()
        self.assertTrue(visit.finished)
        self.assertFalse(visit.advance())
        self.assertEqual(visit.first_try_count, len(tasks) - 1)

    def test_ladder_adapts_from_first_try_answers(self) -> None:
        self.assertEqual(adapt_level(0, 6), 1)
        self.assertEqual(adapt_level(1, 5), 2)
        self.assertEqual(adapt_level(MAX_LEVEL, 6), MAX_LEVEL)
        self.assertEqual(adapt_level(1, 4), 1)
        self.assertEqual(adapt_level(2, 2), 1)
        self.assertEqual(adapt_level(0, 0), 0)

    def test_mirror_warmup_is_ready_after_three_faces_and_comforts_sad_momo(self) -> None:
        warm = MirrorWarmup()
        self.assertFalse(warm.ready)
        self.assertFalse(warm.comfort())
        warm.show(Emotion.SAD)
        self.assertTrue(warm.comfort())
        self.assertIs(warm.emotion, Emotion.HAPPY)
        self.assertFalse(warm.comfort())
        warm.show(Emotion.ANGRY)
        self.assertFalse(warm.ready)
        warm.show(Emotion.SILLY)
        self.assertTrue(warm.ready)


# ---------------------------------------------------------------- saves


class ProgressTests(unittest.TestCase):
    def test_parse_is_bounded_and_tolerates_corrupt_or_foreign_payloads(self) -> None:
        self.assertEqual(parse_progress(None), MomoProgress())
        self.assertEqual(parse_progress({"schema_version": 99, "level": 2}), MomoProgress())
        self.assertEqual(parse_progress({"schema_version": SCHEMA_VERSION, "level": 999}).level, MAX_LEVEL)
        self.assertEqual(parse_progress({"schema_version": SCHEMA_VERSION, "level": True}).level, 0)
        parsed = parse_progress({"schema_version": SCHEMA_VERSION, "level": 1, "known": ["sad", "nope", 3, "happy"]})
        self.assertEqual(parsed, MomoProgress(level=1, known=("happy", "sad")))

    def test_payload_round_trips_through_greia_storage(self) -> None:
        storage = FakeStorage()
        store = GreiaMomoProgress(storage)
        store.save(MomoProgress(level=2, known=("angry", "happy")))
        self.assertEqual(storage.values[STORAGE_KEY], progress_payload(MomoProgress(level=2, known=("happy", "angry"))))
        self.assertEqual(store.load(), MomoProgress(level=2, known=("happy", "angry")))

    def test_storage_failures_never_crash_the_activity(self) -> None:
        broken = mock.Mock()
        broken.kv_get.side_effect = OSError("disk full")
        broken.kv_set.side_effect = OSError("disk full")
        store = GreiaMomoProgress(broken)
        self.assertEqual(store.load(), MomoProgress())
        store.save(MomoProgress(level=1))


# ---------------------------------------------------------------- app loop


class AppLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        cls.resources = {locale: activity_resources(ACTIVITY_DIR, requested_locale=locale) for locale in ("en", "it")}

    def make_app(
        self,
        *,
        size: tuple[int, int] = (REFERENCE_WIDTH, REFERENCE_HEIGHT),
        locale: str = "en",
        level: int = 0,
        seed: int = 3,
        warmup: bool = True,
        known: tuple[str, ...] = (),
    ) -> MomoActivity:
        screen = pygame.display.set_mode(size)
        self.clock = FakeClock()
        self.progress = MemoryProgress(MomoProgress(level=level, known=known))
        self.events = RecordedEvents()
        resources = self.resources[locale]
        app = MomoActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            typography=GreiaTypography(),
            resources=resources,
            audio=MomoAudio(ACTIVITY_DIR, locale=locale, resources=resources, rng=random.Random(seed)),
            progress=self.progress,
            events=self.events,
            rng=random.Random(seed),
            session_id="test-000001",
            clock=self.clock,
            warmup=warmup,
        )
        return app

    def advance(self, app: MomoActivity, seconds: float, step: float = 1 / 15) -> None:
        end = self.clock.now + seconds
        while self.clock.now < end:
            self.clock.now += step
            app.step()

    def advance_to_next(self, app: MomoActivity) -> None:
        """Step until the next task (or the ending) begins (bounded)."""

        index = app.visit.index
        for _ in range(200):
            if app.visit.index != index or app.state is not AppState.PLAYING:
                return
            self.clock.now += 1 / 15
            app.step()
        self.fail("the visit did not move on after a solved task")

    def physical(self, app: MomoActivity, rect: pygame.Rect) -> tuple[int, int]:
        transform = app.canvas.mapper.transform
        x, y = transform.logical_to_physical(rect.center)
        return int(x), int(y)

    def tap_tile(self, app: MomoActivity, index: int) -> bool:
        return app.tap(self.physical(app, app.controls.tile(index).rect))

    # -- warm-up --

    def test_warmup_mirrors_faces_comforts_and_unlocks_play(self) -> None:
        app = self.make_app()
        self.advance(app, 0.5)
        self.assertIs(app.state, AppState.WARMUP)
        self.assertEqual(app.audio.spoken[-1], "welcome")
        self.assertFalse(app.controls.go.visible)
        self.assertEqual([button.rect for button in app.controls.choices], list(mirror_rects()))
        sad = MIRROR_ORDER.index(Emotion.SAD)
        self.assertTrue(self.tap_tile(app, sad))
        self.assertIs(app.warm.emotion, Emotion.SAD)
        self.assertEqual(app.audio.spoken[-1], "sad")
        self.assertTrue(app.tap(self.physical(app, app.controls.momo.rect)))
        self.assertIs(app.warm.emotion, Emotion.HAPPY)
        self.assertEqual(app.audio.spoken[-1], "comfort")
        self.tap_tile(app, MIRROR_ORDER.index(Emotion.ANGRY))
        self.assertFalse(app.controls.go.visible)
        self.tap_tile(app, MIRROR_ORDER.index(Emotion.SLEEPY))
        self.assertTrue(app.controls.go.visible)
        self.assertTrue(app.tap(self.physical(app, app.controls.go.rect)))
        self.assertIs(app.state, AppState.PLAYING)
        self.assertTrue(app.controls.progress.visible)

    # -- never reveal the answer --

    def test_prompts_never_speak_or_mark_the_answer(self) -> None:
        for seed in range(6):
            app = self.make_app(level=2, seed=seed, warmup=False)
            while app.state is AppState.PLAYING:
                task = app.visit.task
                app.audio.spoken.clear()
                self.advance(app, 0.8)
                # Idle hints point at the cue but never name the feeling.
                self.advance(app, 13.0)
                with self.subTest(seed=seed, stage=task.stage):
                    self.assertFalse(EMOTION_CUES & set(app.audio.spoken), app.audio.spoken)
                    if task.stage is Stage.RECOGNISE:
                        self.assertIn("game_prompt", app.audio.spoken)
                    self.assertFalse(app.motion.glow_id)
                    tiles = app.controls.choices[: app.controls.count]
                    self.assertFalse(any(button.selected for button in tiles))
                    self.assertTrue(all(button.enabled for button in tiles))
                    if task.stage is Stage.EXPLAIN:
                        self.assertEqual(app.frame_view().momo, "silhouette")
                app._on_choice(task.answer_index)
                self.advance_to_next(app)

    # -- a full visit by touch, with mistakes, to the completion scene --

    def test_full_visit_by_touch_with_retries_reaches_the_completion_scene(self) -> None:
        app = self.make_app(warmup=False, level=0, seed=11)
        self.advance(app, 0.8)
        for number in range(TASKS_PER_VISIT):
            self.advance(app, 0.6)  # the new task's short intro
            task = app.visit.task
            self.assertEqual(app.controls.progress.current, number)
            if number % 2 == 0:
                wrong = next(i for i, choice in enumerate(task.choices) if choice.key != task.answer)
                self.assertTrue(self.tap_tile(app, wrong))
                self.assertFalse(app.controls.tile(wrong).enabled)
                self.assertIs(app.guide.pose, CastPose.THINK)
                self.advance(app, 0.9)
                if task.stage is Stage.HELP:
                    self.assertEqual(app.motion.glow_id, choice_id(task.answer_index))
                else:
                    self.assertEqual(app.audio.spoken[-1], task.answer)
            self.assertTrue(self.tap_tile(app, task.answer_index))
            self.assertIs(app.guide.pose, CastPose.CHEER)
            self.assertTrue(app.controls.tile(task.answer_index).selected)
            if task.stage is Stage.HELP:
                self.advance(app, 0.8)
                self.assertEqual(app.frame_view().momo, Emotion.HAPPY.value)
            else:
                self.assertEqual(app.audio.spoken[-1], task.answer)
            self.advance_to_next(app)
        self.assertIs(app.state, AppState.TERMINAL)
        self.assertEqual(len(self.events.completed), 1)
        self.assertEqual(self.events.completed[0]["tasks"], TASKS_PER_VISIT)
        self.assertEqual(self.events.completed[0]["first_try"], TASKS_PER_VISIT // 2)
        self.assertEqual(self.progress.saved.level, 0)
        app.render()
        # Play again: a fresh visit without the warm-up.
        app.tap(self.physical(app, app.completion.primary_rect))
        self.assertIs(app.state, AppState.PLAYING)
        self.assertEqual(app.visit.completed_count, 0)

    def test_perfect_visit_climbs_the_ladder_and_reports_new_feelings_once(self) -> None:
        app = self.make_app(warmup=False, level=0, seed=2, known=("happy",))
        while app.state is AppState.PLAYING:
            self.advance(app, 0.6)
            app._on_choice(app.visit.task.answer_index)
            self.advance_to_next(app)
        self.assertEqual(self.progress.saved.level, 1)
        self.assertNotIn("happy", self.events.discovered)
        self.assertEqual(len(self.events.discovered), len(set(self.events.discovered)))
        self.assertTrue(set(self.events.discovered) <= set(self.progress.saved.known))

    def test_keyboard_alone_answers_a_task(self) -> None:
        app = self.make_app(warmup=False, level=2, seed=5)
        self.advance(app, 0.8)
        task = app.visit.task
        for _ in range(task.answer_index):
            app.press(pygame.K_RIGHT)
        self.assertEqual(app.controls.layer.focused_id, choice_id(task.answer_index))
        self.assertTrue(app.press(pygame.K_SPACE))
        self.assertTrue(app.visit.solved)

    def test_idle_hint_points_and_then_replays_the_question(self) -> None:
        app = self.make_app(warmup=False, level=0, seed=1)
        self.advance(app, 1.0)
        app.audio.spoken.clear()
        self.advance(app, 6.2)
        self.assertTrue(app.guide.pointing)
        self.assertEqual(app.visit.records[0].hints, 1)
        self.assertNotIn("game_prompt", app.audio.spoken)
        self.advance(app, 6.5)
        self.assertIn("game_prompt", app.audio.spoken)

    def test_taps_in_protected_chrome_are_ignored(self) -> None:
        app = self.make_app(warmup=False)
        self.advance(app, 0.8)
        region = activity_viewport_for_surface(app.screen).protected_regions[0]
        self.assertFalse(app.tap((int(region.x) + 2, int(region.y) + 2)))
        self.assertEqual(app.visit.records[0].misses, 0)
        self.assertFalse(app.visit.solved)

    def test_layout_stays_clear_of_protected_chrome_at_every_size(self) -> None:
        for size in ((1024, 600), (800, 480), (480, 320), (1280, 800)):
            app = self.make_app(size=size, warmup=False, level=2)
            rects = [app.controls.listen.rect, app.controls.progress.rect, CARD_RECT, *tile_rects(3), *mirror_rects()]
            chrome = ControlLayout.for_canvas(app.canvas, size).protected
            with self.subTest(size=size):
                for rect in rects:
                    self.assertFalse(rect.colliderect(chrome), rect)
                self.assertGreater(GUIDE_MIDBOTTOM[1] - 150, chrome.bottom)

    def test_italian_captions_fit_their_tiles(self) -> None:
        app = self.make_app(warmup=False, locale="it", level=2, seed=8)
        for emotion in Emotion:
            label = app.kit.painter.label(app._feeling_word(emotion), 29, (0, 0, 0), max_width=tile_rects(3)[0].width - 14)
            self.assertLessEqual(label.get_width(), tile_rects(3)[0].width - 14)
            self.assertEqual(app._feeling_word(emotion), app._feeling_word(emotion).upper())

    def test_steady_frames_do_not_scale_or_decode(self) -> None:
        app = self.make_app(warmup=False, level=2, seed=3)
        self.advance(app, 2.0)
        app.render()
        with mock.patch("pygame.transform.smoothscale", side_effect=AssertionError("per-frame scale")), \
                mock.patch("pygame.transform.rotozoom", side_effect=AssertionError("per-frame rotate")), \
                mock.patch("pygame.image.load", side_effect=AssertionError("per-frame decode")):
            for _ in range(5):
                self.clock.now += 0.1
                app.step()
                app.render()

    def test_story_cards_are_bounded_and_all_compose(self) -> None:
        pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        art = MomoArt(ControlKit(GreiaTypography()).painter)
        for story in STORIES:
            card = art.story_card(story.story_id)
            self.assertIsNotNone(card, story.story_id)
            self.assertEqual(card.get_size(), CARD_RECT.size)
        self.assertLessEqual(len(art._cards), 4)
        for item in HELP_ITEMS:
            self.assertIsNotNone(art.item(item, 96), item)
        for character in ("momo", *FRIEND_CHARACTERS):
            for emotion in ALL_EMOTIONS:
                self.assertEqual(art.face(character, emotion, 80).get_size(), (80, 80))
        self.assertIsNotNone(art.silhouette(200))

    def test_run_presents_before_ready_and_saves_on_exit(self) -> None:
        app = self.make_app(warmup=True)
        calls = {"n": 0}

        def stop() -> bool:
            calls["n"] += 1
            return calls["n"] > 2

        with mock.patch("activities.faccine_momo.momo_app.activity_stop_requested", side_effect=stop), \
                mock.patch("activities.faccine_momo.momo_app.mark_activity_ready") as ready:
            self.assertEqual(app.run(), 0)
        ready.assert_called_once()
        self.assertGreaterEqual(self.progress.saves, 1)


if __name__ == "__main__":
    unittest.main()
