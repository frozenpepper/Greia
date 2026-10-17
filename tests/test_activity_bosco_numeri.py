"""Tests for Tito's Number Forest — numeral recognition and writing 0–10.

Meet a numeral (Tito counts its forest friends into a frame), find it among
numeral tiles, trace it stroke by stroke, then pick the frame that holds that
many friends.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import random
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "bosco_numeri"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from bosco_model import (  # noqa: E402
    LOOK_ALIKES,
    NUMERALS,
    TEACHING_GROUPS,
    ForestWalk,
    StepKind,
    WalkPlanner,
    next_group,
    stage_for,
)
from bosco_services import STORAGE_KEY, BoscoProgress, GreiaBoscoProgress  # noqa: E402
from bosco_strokes import NUMERAL_STROKES, strokes_for  # noqa: E402
from bosco_trace import TraceEvent, TraceGuide, TraceTracker  # noqa: E402

NUMBER_WORDS = {
    "en": ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"],
    "it": ["Uno", "Due", "Tre", "Quattro", "Cinque", "Sei", "Sette", "Otto", "Nove", "Dieci"],
}


def _receipt_text(locale: str, stem: str) -> str:
    path = ACTIVITY_ROOT / "assets" / "audio" / locale / f"{stem}.wav.receipt.json"
    return json.loads(path.read_text(encoding="utf-8"))["request"]["text"]


class ManifestTests(unittest.TestCase):
    def test_manifest_matches_numeral_writing(self) -> None:
        data = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        act = data["activity"]
        self.assertEqual(act["id"], "org.greia.bosco-numeri")  # package id kept
        self.assertEqual(act["languages"], ["it", "en", "es", "fr"])
        edu = data["education"]
        self.assertEqual((edu["recommended_age_min"], edu["recommended_age_max"]), (4, 6))
        self.assertTrue(edu["adaptive_difficulty"])
        self.assertIn("number_recognition", edu["categories"])
        self.assertIn("fine_motor", edu["categories"])  # tracing is real
        self.assertNotIn("counting", edu["categories"])  # Number Garden owns tap-counting
        self.assertEqual(
            {event["id"]: event["kind"] for event in edu["events"]},
            {"bosco.number_completed": "milestone", "bosco.challenge_completed": "completion"},
        )
        self.assertEqual(data["input"]["profile"], "hybrid")

    def test_four_locale_key_parity_without_text_prompts(self) -> None:
        bundles = {
            locale: json.loads((ACTIVITY_ROOT / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
            for locale in ("en", "it", "es", "fr")
        }
        keys = {locale: set(bundle["strings"]) for locale, bundle in bundles.items()}
        self.assertEqual(len({frozenset(k) for k in keys.values()}), 1)
        self.assertEqual(
            keys["en"],
            {"activity.bosco_numeri.title", "activity.title", "victory.title", "button.play_again"},
        )
        for bundle in bundles.values():
            for text in bundle["strings"].values():
                self.assertFalse(any(ord(ch) > 0x2000 for ch in text), text)  # no emoji

    def test_old_counting_modules_are_gone(self) -> None:
        self.assertFalse((ACTIVITY_ROOT / "bosco_content.py").exists())
        for source in ACTIVITY_ROOT.glob("*.py"):
            text = source.read_text(encoding="utf-8")
            self.assertNotIn("alfabeto", text, source.name)  # no cross-Activity imports
            for emoji in ("🐻", "🍎", "⭐", "🦋"):
                self.assertNotIn(emoji, text, source.name)


class ContentTests(unittest.TestCase):
    def test_approved_number_clips_cover_one_to_ten(self) -> None:
        for locale, words in NUMBER_WORDS.items():
            for value in range(1, 11):
                with self.subTest(locale=locale, value=value):
                    self.assertEqual(_receipt_text(locale, f"count_{value}"), f"{words[value - 1]}!")
                    self.assertIn(str(value), _receipt_text(locale, f"ask_{value}"))
        # Zero was recorded on 2026-10-17 (owner-approved request list).
        self.assertEqual(_receipt_text("en", "count_0"), "Zero!")
        self.assertEqual(_receipt_text("it", "count_0"), "Zero!")
        self.assertIn("0", _receipt_text("en", "ask_0"))

    def test_every_numeral_has_a_library_friend_and_stroke_shapes(self) -> None:
        from bosco_art import resolve_picture

        self.assertEqual([item.value for item in NUMERALS], list(range(11)))
        for item in NUMERALS:
            with self.subTest(value=item.value):
                self.assertTrue(item.creature.startswith(("creature.woodland.", "prop.nature.")))
                self.assertTrue(resolve_picture(item.creature).is_file(), item.creature)
                strokes = strokes_for(item.value)
                self.assertTrue(1 <= len(strokes) <= 3)
                for stroke in strokes:
                    self.assertGreaterEqual(len(stroke), 2)
        self.assertEqual(len(NUMERAL_STROKES[10]), len(NUMERAL_STROKES[1]) + len(NUMERAL_STROKES[0]))
        for value, related in LOOK_ALIKES.items():
            self.assertIn(value, NUMERAL_STROKES)
            self.assertNotIn(value, related)

    def test_teaching_groups_cover_zero_to_ten_once(self) -> None:
        values = [value for group in TEACHING_GROUPS for value in group]
        self.assertEqual(sorted(values), list(range(11)))
        self.assertEqual(TEACHING_GROUPS[0], (1, 2))
        self.assertGreater(values.index(0), values.index(5) - 1)  # zero after 1-5


class PlannerAndWalkTests(unittest.TestCase):
    def test_walk_shape_and_difficulty_ladder(self) -> None:
        planner = WalkPlanner(random.Random(3))
        for group in range(planner.group_count + 1):
            stage = stage_for(group)
            steps = planner.build(group)
            kinds = [step.kind for step in steps]
            self.assertEqual(kinds[:4], [StepKind.MEET, StepKind.FIND, StepKind.TRACE, StepKind.SHOW])
            self.assertEqual(kinds.count(StepKind.MEET), 2)
            self.assertEqual(kinds.count(StepKind.REVIEW), 2)
            for step in steps:
                if not step.is_choice:
                    continue
                self.assertEqual(step.choices[step.correct_index], step.numeral.value)
                if step.is_find:
                    self.assertEqual(len(step.choices), stage.find_tiles)
                else:
                    self.assertEqual(len(step.choices), stage.show_cards)
                    for value in step.choices:
                        if value != step.numeral.value:
                            gap = abs(value - step.numeral.value)
                            self.assertGreaterEqual(gap, stage.min_gap, step)
        late = [step for step in planner.build(4) if step.is_find]
        self.assertTrue(all(any(c in LOOK_ALIKES[s.numeral.value] for c in s.choices) for s in late))
        early = [step for step in planner.build(0) if step.is_find]
        for step in early:
            others = [c for c in step.choices if c != step.numeral.value]
            self.assertFalse(any(c in LOOK_ALIKES[step.numeral.value] for c in others))

    def test_zero_frames_only_after_zero_is_taught(self) -> None:
        for seed in range(20):
            planner = WalkPlanner(random.Random(seed))
            for group in (0, 1):
                for step in planner.build(group):
                    if step.kind is StepKind.SHOW:
                        self.assertNotIn(0, step.choices)

    def test_seeded_walks_are_deterministic_and_answers_move(self) -> None:
        first = WalkPlanner(random.Random(11)).build(3)
        second = WalkPlanner(random.Random(11)).build(3)
        self.assertEqual(first, second)
        slots = [step.correct_index for step in first if step.is_choice]
        self.assertTrue(all(a != b for a, b in zip(slots, slots[1:])))

    def test_short_and_review_walks_pick_least_traced(self) -> None:
        planner = WalkPlanner(random.Random(5))
        traced = {value: 5 for value in range(11)}
        traced[7] = 1
        ten = planner.numerals_for(5, traced)
        self.assertEqual([item.value for item in ten], [10, 7])
        review = planner.numerals_for(planner.group_count, {**traced, 3: 0})
        self.assertEqual({item.value for item in review}, {3, 7})

    def test_walk_flow_errors_write_and_complete_once(self) -> None:
        planner = WalkPlanner(random.Random(2))
        walk = ForestWalk(planner.build(0), group=0)
        self.assertEqual(walk.task_total, 8)
        walk.finish_meet()
        step = walk.step
        wrong = 1 - step.correct_index
        self.assertFalse(walk.select(wrong).correct)
        self.assertIn(wrong, walk.eliminated)
        self.assertFalse(walk.select(wrong).correct)  # a retired option never counts twice
        self.assertEqual(walk.choice_errors, 1)
        self.assertTrue(walk.select(step.correct_index).correct)
        self.assertEqual(walk.step.kind, StepKind.TRACE)
        walk.finish_trace()
        self.assertEqual([item.value for item in walk.written], [1])
        while not walk.is_complete:
            current = walk.step
            if current.kind is StepKind.MEET:
                walk.finish_meet()
            elif current.kind is StepKind.TRACE:
                walk.finish_trace()
            else:
                walk.select(current.correct_index)
        payload = walk.consume_completion()
        self.assertEqual(payload["numerals"], 2)
        self.assertEqual(payload["retries"], 1)
        self.assertIsNone(walk.consume_completion())
        self.assertEqual(next_group(0, walk, planner.group_count), 1)
        walk.choice_errors = 3
        self.assertEqual(next_group(4, walk, planner.group_count), 4)  # a hard walk repeats
        walk.choice_errors = 0
        self.assertEqual(next_group(planner.group_count, walk, planner.group_count), planner.group_count)


class TraceTests(unittest.TestCase):
    def _follow(self, tracker: TraceTracker, stroke_index: int, *, every: int = 2) -> TraceEvent:
        stroke = tracker.guide.strokes[stroke_index]
        points = list(stroke.points[::every]) + [stroke.points[-1]]
        self.assertTrue(tracker.begin(points[0]))
        event = TraceEvent.NONE
        for point in points[1:]:
            event = tracker.move(point)
            if event in {TraceEvent.STROKE_DONE, TraceEvent.NUMERAL_DONE}:
                break
        tracker.end()
        return event

    def test_following_every_stroke_in_order_completes_each_numeral(self) -> None:
        for value in range(11):
            tracker = TraceTracker(TraceGuide.fit(value, (0, 0, 360, 360)))
            events = [self._follow(tracker, index) for index in range(len(tracker.guide.strokes))]
            self.assertEqual(events[-1], TraceEvent.NUMERAL_DONE, value)
            self.assertTrue(tracker.complete)

    def test_wrong_end_and_loop_shortcuts_do_not_trace(self) -> None:
        for value in (0, 8):
            tracker = TraceTracker(TraceGuide.fit(value, (0, 0, 360, 360)))
            loop = tracker.guide.strokes[0]
            self.assertTrue(tracker.begin(loop.start))
            self.assertIn(tracker.move(loop.points[-1]), {TraceEvent.NONE, TraceEvent.ADVANCED})
            self.assertLess(tracker.progress, loop.length * 0.2, value)
            tracker.end()
        seven = TraceTracker(TraceGuide.fit(7, (0, 0, 360, 360)))
        self.assertFalse(seven.begin(seven.guide.strokes[0].points[-1]))  # wrong end does nothing

    def test_follow_the_dot_traces_without_a_pointer(self) -> None:
        tracker = TraceTracker(TraceGuide.fit(4, (0, 0, 300, 300)))
        events = []
        for _ in range(400):
            event = tracker.auto_advance(12.0)
            if event is not TraceEvent.ADVANCED:
                events.append(event)
            if tracker.complete:
                break
        self.assertEqual(events, [TraceEvent.STROKE_DONE, TraceEvent.NUMERAL_DONE])


class _Storage:
    def __init__(self, value=None) -> None:
        self.value = value
        self.saved = None

    def kv_get(self, key, default=None):
        assert key == STORAGE_KEY
        return self.value if self.value is not None else default

    def kv_set(self, key, value) -> None:
        assert key == STORAGE_KEY
        self.saved = value
        self.value = value


class ProgressTests(unittest.TestCase):
    def test_v1_counting_save_loads_and_is_carried_forward(self) -> None:
        port = GreiaBoscoProgress(_Storage({"total_completed": 12, "current_number": 7}))
        progress = port.load()
        self.assertEqual((progress.group, progress.rounds_completed, progress.traced), (0, 0, {}))
        self.assertTrue(progress.record_trace(3))
        self.assertFalse(progress.record_trace(3))
        progress.group = 2
        port.save(progress)
        payload = port._storage.saved
        self.assertEqual(payload["schema_version"], 2)
        self.assertEqual((payload["total_completed"], payload["current_number"]), (12, 7))  # never lost
        self.assertEqual(payload["traced"], {"3": 2})
        again = BoscoProgress.from_payload(json.loads(json.dumps(payload)))
        self.assertEqual((again.group, again.traced, again.legacy_total_completed), (2, {3: 2}, 12))

    def test_malformed_payloads_recover_and_stay_bounded(self) -> None:
        for raw in (None, [], "x", {"group": "high", "traced": {"11": 3, "a": 1, "2": True}, "current_number": 99}):
            progress = BoscoProgress.from_payload(raw)
            self.assertEqual(progress.traced, {})
            self.assertEqual(progress.group, 0)
            self.assertEqual(progress.legacy_current_number, 1)
        progress = BoscoProgress.from_payload({"group": 10_000, "traced": {"10": 10_000}})
        self.assertEqual(progress.group, 64)
        self.assertEqual(progress.traced[10], 999)
        broken = GreiaBoscoProgress(_Storage())
        broken._storage = None
        self.assertIsInstance(broken.load(), BoscoProgress)


class _MockAudio:
    def __init__(self) -> None:
        self.played: list[str] = []
        self.sfx: list[str] = []

    def play_speech(self, cue_id: str) -> float | None:
        self.played.append(cue_id)
        return None if cue_id == "count_0" else 0.6

    def stop_speech(self) -> None:
        return

    def play_sfx(self, cue: str) -> None:
        self.sfx.append(cue)


class _MockEvents:
    def __init__(self) -> None:
        self.written: list[int] = []
        self.walks: list[dict] = []

    def numeral_written(self, session_id, value) -> None:
        self.written.append(value)

    def walk_completed(self, session_id, payload) -> None:
        self.walks.append(payload)


class AppLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600))

    def _app(self, locale: str = "en", *, group: int = 0, size=(1024, 600), saved=None):
        from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from bosco_app import BoscoApp
        from bosco_art import BoscoArt
        from bosco_audio import SpeechQueue
        from bosco_renderer import BoscoRenderer

        screen = pygame.display.set_mode(size)
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale(locale, support)
        assert context is not None
        resources = LocalizedResources(ACTIVITY_ROOT, context)
        payload = saved if saved is not None else {"schema_version": 2, "group": group}
        self.storage = _Storage(payload)
        self.port = GreiaBoscoProgress(self.storage)
        self.events = _MockEvents()
        self.audio = _MockAudio()
        self.now = [100.0]
        return BoscoApp(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            planner=WalkPlanner(random.Random(21)),
            progress=self.port.load(),
            progress_port=self.port,
            events=self.events,
            renderer=BoscoRenderer(BoscoArt(1024, 600)),
            typography=GreiaTypography(),
            resources=resources,
            audio=self.audio,
            speech_queue=SpeechQueue(self.audio),
            rng=random.Random(21),
            session_id="forest-1",
            clock=lambda: self.now[0],
        )

    def _run(self, app, seconds: float, step: float = 0.1) -> None:
        for _ in range(int(round(seconds / step))):
            self.now[0] += step
            app.tick()
            app._render()

    def _tap_choice(self, app, index: int) -> bool:
        center = app.controls.choice_center(index)
        physical = app.canvas.mapper.transform.logical_to_physical(center)
        return app._handle_pointer((int(physical[0]), int(physical[1])))

    def _trace_numeral(self, app) -> None:
        box = app.controls.geometry.trace_box
        for stroke in app.tracker.guide.strokes:
            points = [(box.left + x, box.top + y) for x, y in list(stroke.points[::3]) + [stroke.points[-1]]]
            app._drag(points)
            self._run(app, 0.1)

    def _until(self, app, predicate, limit: float = 20.0) -> None:
        waited = 0.0
        while not predicate() and waited < limit:
            self._run(app, 0.1)
            waited += 0.1
        self.assertTrue(predicate(), f"timed out in state {app.state}")

    def test_full_walk_plays_to_completion_with_feedback_grammar(self) -> None:
        from greia_platform.activity_feedback import CastPose
        from bosco_app import AppState

        app = self._app("en", saved={"total_completed": 9, "current_number": 4})
        self.assertEqual(app.state, AppState.MEET)
        self._run(app, 2.0)
        # Tito introduces himself, then counts the bear into the frame and names it.
        self.assertEqual(self.audio.played[:3], ["intro", "count_1", "count_1"])
        self.assertTrue(app.scene_state().tito_pointing)
        self.assertEqual(app.scene_state().meet_revealed, 1)
        self._until(app, lambda: app.walk.step.kind is StepKind.FIND)
        self._run(app, 0.2)
        self.assertIn("ask_1", self.audio.played)

        # Idle: Tito points and asks again; no tile is revealed.
        self._run(app, 8.0)
        self.assertTrue(app.scene_state().tito_pointing)
        self.assertGreaterEqual(self.audio.played.count("ask_1"), 2)
        self.assertIsNone(app._hint_target)

        # A wrong tile: think pose, the tile retires, Tito names the right one.
        step = app.walk.step
        wrong = 1 - step.correct_index
        self.assertTrue(self._tap_choice(app, wrong))
        self.assertEqual(app.state, AppState.TRY_AGAIN)
        self.assertEqual(app.renderer.cast.pose, CastPose.THINK)
        self._run(app, 0.6)
        self.assertIn("tito.retry", self.audio.played)
        self.assertFalse(app.controls.choices[wrong].enabled)
        self.assertEqual(app.state, AppState.PLAYING)

        saw_show_counting = False
        while app.state is not AppState.TERMINAL:
            current = app.walk.step
            if app.state is AppState.PLAYING and current is not None:
                if current.kind is StepKind.SHOW and not saw_show_counting:
                    # A wrong frame is counted aloud, item by item.
                    picked = (current.correct_index + 1) % len(current.choices)
                    self.audio.played.clear()
                    self.assertTrue(self._tap_choice(app, picked))
                    self._run(app, 1.2)
                    self.assertEqual(app.scene_state().counting, (picked, 1))
                    self.assertIn("count_1", self.audio.played)
                    saw_show_counting = True
                    self._until(app, lambda: app.state is AppState.PLAYING)
                elif current.is_choice:
                    self.assertTrue(self._tap_choice(app, current.correct_index))
                    self.assertEqual(app.state, AppState.CELEBRATE)
                    self.assertEqual(app.renderer.cast.pose, CastPose.CHEER)
                elif current.kind is StepKind.TRACE:
                    self._run(app, 0.6)
                    self.assertIsNotNone(app.scene_state().trace.demo_point)  # the hand shows the stroke
                    self._trace_numeral(app)
                    self.assertEqual(app.state, AppState.BLOOM)
                    self.assertEqual(app.renderer.cast.pose, CastPose.CHEER)
            self._run(app, 0.2)
            if self.now[0] > 600:
                self.fail("walk did not finish")

        self.assertTrue(saw_show_counting)
        self.assertEqual(self.events.written, [1, 2])
        self.assertEqual(len(self.events.walks), 1)
        saved = self.storage.saved
        self.assertEqual(saved["group"], 1)
        self.assertEqual(saved["rounds_completed"], 1)
        self.assertEqual(saved["traced"], {"1": 1, "2": 1})
        self.assertEqual((saved["total_completed"], saved["current_number"]), (9, 4))  # v1 data kept
        self.assertIn("tito.celebrate", self.audio.played)
        self.assertIn("well_done", self.audio.played)

        primary = app.completion.primary_rect
        physical = app.canvas.mapper.transform.logical_to_physical(primary.center)
        self.assertTrue(app._handle_pointer((int(physical[0]), int(physical[1]))))
        self.assertEqual(app.state, AppState.MEET)
        self.assertEqual([item.value for item in app.walk.numerals], [3, 4])
        self.assertEqual(app.season, "woodland_autumn")  # each walk visits a new season

    def test_tracing_zero_invites_writing_it(self) -> None:
        from bosco_audio import PACKAGE_LINES

        app = self._app("en", group=2)  # the walk that meets 5 and 0
        steps = app.walk.steps
        index = next(
            (i for i, s in enumerate(steps) if s.kind is StepKind.TRACE and s.numeral.value == 0), None
        )
        self.assertIsNotNone(index, "the third walk traces zero")
        app.walk._index = index  # noqa: SLF001 - jump to the zero tracing step
        self.audio.played.clear()
        app._enter_step()  # noqa: SLF001
        for _ in range(120):
            self.now[0] += 0.1
            app.tick()
        self.assertIn("write_zero", self.audio.played)  # "Let's write number 0!"
        self.assertLess(self.audio.played.index("count_0"), self.audio.played.index("write_zero"))
        self.assertIn("write_zero", PACKAGE_LINES)
        from greia_platform.localization import activity_resources

        for locale in ("en", "it", "es", "fr"):
            self.assertEqual(activity_resources(ACTIVITY_ROOT, requested_locale=locale).audio_path("write_zero").parent.name, locale)

    def test_keyboard_and_controller_play_find_trace_and_show(self) -> None:
        from bosco_app import AppState

        app = self._app("it", group=3)
        self._until(app, lambda: app.walk.step.kind is StepKind.FIND)
        step = app.walk.step
        self.assertEqual(app.controls.layer.focused_id, "choice.0")
        for _ in range(step.correct_index):
            self.assertTrue(app._handle_keyboard(pygame.K_RIGHT))
        self.assertTrue(app._handle_keyboard(pygame.K_SPACE))
        self.assertEqual(app.state, AppState.CELEBRATE)
        self._until(app, lambda: app.walk.step.kind is StepKind.TRACE and app.state is AppState.PLAYING)
        self.assertEqual(app.controls.layer.focused_id, "trace")
        for _ in range(len(app.tracker.guide.strokes)):
            self.assertTrue(app._handle_keyboard(pygame.K_SPACE))
            self._until(app, lambda: not app._auto_trace)
        self.assertEqual(app.state, AppState.BLOOM)
        self._until(app, lambda: app.walk.step.kind is StepKind.SHOW and app.state is AppState.PLAYING)
        step = app.walk.step
        self.assertEqual(app.controls.layer.focused_id, "choice.0")
        key = pygame.K_DOWN if not app.controls.show_frame(step).vertical else pygame.K_RIGHT
        for _ in range(step.correct_index):
            self.assertTrue(app._handle_keyboard(key))
        self.assertTrue(app._handle_keyboard(pygame.K_SPACE))
        self.assertEqual(app.state, AppState.CELEBRATE)

    def test_digit_key_picks_its_numeral_tile(self) -> None:
        from bosco_app import AppState

        app = self._app("en", group=1)
        self._until(app, lambda: app.walk.step.kind is StepKind.FIND)
        target = app.walk.step.numeral.value
        self.assertTrue(app._handle_keyboard(getattr(pygame, f"K_{target}")))
        self.assertEqual(app.state, AppState.CELEBRATE)

    def test_zero_is_met_silently_with_an_empty_frame(self) -> None:
        app = self._app("en", group=2)
        walk = app.walk
        self.assertEqual([item.value for item in walk.numerals], [5, 0])
        zero_show = [s for s in walk.steps if s.kind is StepKind.SHOW and s.numeral.value == 0][0]
        self.assertTrue(all(c > 0 for i, c in enumerate(zero_show.choices) if i != zero_show.correct_index))
        while not (walk.step.kind is StepKind.MEET and walk.step.numeral.value == 0):
            current = walk.step
            if current.kind is StepKind.MEET:
                walk.finish_meet()
            elif current.kind is StepKind.TRACE:
                walk.finish_trace()
            else:
                walk.select(current.correct_index)
        app._enter_step()
        self._run(app, 0.3)
        # No "zero" recording yet: the numeral still glows for a pictorial beat.
        self.assertEqual(app.scene_state().speaking, "numeral")
        self.assertEqual(app.scene_state().meet_revealed, 0)
        self.assertIn("count_0", self.audio.played)

    def test_listen_button_replays_and_home_region_is_protected(self) -> None:
        app = self._app("en")
        self._until(app, lambda: app.walk.step.kind is StepKind.FIND)
        self._run(app, 2.0)
        self.audio.played.clear()
        listen = app.controls.listen.rect.center
        physical = app.canvas.mapper.transform.logical_to_physical(listen)
        self.assertTrue(app._handle_pointer((int(physical[0]), int(physical[1]))))
        app.tick()
        self.assertEqual(self.audio.played[:1], ["ask_1"])
        self.assertFalse(app._handle_pointer((10, 10)))

    def test_small_screens_keep_controls_clear_of_home(self) -> None:
        from greia_platform.activity_controls import ControlLayout

        for size in ((800, 480), (480, 320)):
            with self.subTest(size=size):
                app = self._app("it", group=4, size=size)
                layout = ControlLayout.for_canvas(app.canvas, size)
                geometry = app.controls.geometry
                for rect in (geometry.listen, geometry.card, geometry.trace_box, geometry.show_area, app.controls.dots.rect):
                    self.assertFalse(rect.colliderect(layout.protected), rect)
                self._run(app, 1.0)

    def test_touch_far_from_the_stroke_only_pulses_the_start_dot(self) -> None:
        from greia_platform.activity_controls import KitPointer, PointerPhase

        app = self._app("en")
        self._until(app, lambda: app.walk.step.kind is StepKind.FIND)
        self._tap_choice(app, app.walk.step.correct_index)
        self._until(app, lambda: app.walk.step.kind is StepKind.TRACE and app.tracker is not None)
        box = app.controls.geometry.trace_box
        self.assertTrue(app._trace_pointer(KitPointer(PointerPhase.DOWN, (box.right - 4, box.bottom - 4))))
        self.assertFalse(app.tracker.dragging)
        self.assertTrue(app.scene_state().trace.start_pulse)
        self.assertEqual(app.tracker.progress, 0.0)


class AudioTests(unittest.TestCase):
    def test_speech_queue_is_bounded_and_sequenced(self) -> None:
        from bosco_audio import SpeechQueue

        audio = _MockAudio()
        queue = SpeechQueue(audio, max_len=3)
        for index in range(6):
            queue.enqueue(f"cue{index}", tag=f"t{index}")
        queue.update(0.0)
        self.assertEqual(audio.played, ["cue0"])
        self.assertEqual(queue.current_tag, "t0")
        queue.update(1.5)
        self.assertEqual(audio.played, ["cue0", "cue1"])
        queue.clear()
        self.assertFalse(queue.busy)

    def test_only_number_clips_tito_lines_and_shared_tito_are_loaded(self) -> None:
        from bosco_audio import BoscoAudio

        pygame.mixer.init()
        try:
            audio = BoscoAudio(ACTIVITY_ROOT, locale="en")
            if not audio.has_speech("count_1"):
                self.skipTest("audio decoding unavailable on this host")
            self.assertTrue(audio.has_speech("ask_10"))
            self.assertTrue(audio.has_speech("intro"))
            self.assertFalse(audio.has_speech("mode_count"))  # old counting-mode line unused
            self.assertTrue(audio.has_speech("count_0"))
            self.assertTrue(audio.has_speech("tito.retry"))
        finally:
            pygame.mixer.quit()


if __name__ == "__main__":
    unittest.main()
