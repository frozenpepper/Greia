"""Tests for L'Alfabeto di Leo — Leo's Letter Garden (meet, find, trace)."""

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
ACTIVITY_ROOT = ROOT / "activities" / "alfabeto_leo"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from alfabeto_model import (  # noqa: E402
    LETTERS_CATALOGUE,
    LOOK_ALIKES,
    PICTURE_PENDING,
    GardenPlanner,
    GardenRound,
    StepKind,
    get_letter_catalogue,
    next_group,
    teaching_groups,
)
from alfabeto_services import STORAGE_KEY, AlfabetoProgress, GreiaAlfabetoProgress  # noqa: E402
from alfabeto_strokes import LETTER_STROKES, strokes_for  # noqa: E402
from alfabeto_trace import TraceEvent, TraceGuide, TraceTracker  # noqa: E402


def _receipt_text(locale: str, stem: str) -> str:
    path = ACTIVITY_ROOT / "assets" / "audio" / locale / f"{stem}.wav.receipt.json"
    return json.loads(path.read_text(encoding="utf-8"))["request"]["text"]


class ManifestTests(unittest.TestCase):
    def test_manifest_matches_the_letter_garden(self) -> None:
        data = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        act = data["activity"]
        self.assertEqual(act["id"], "org.greia.alfabeto-leo")
        self.assertEqual(act["title_key"], "activity.alfabeto_leo.title")
        self.assertEqual(act["languages"], ["it", "en", "es", "fr"])
        edu = data["education"]
        self.assertEqual((edu["recommended_age_min"], edu["recommended_age_max"]), (3, 5))
        self.assertTrue(edu["adaptive_difficulty"])
        self.assertIn("fine_motor", edu["categories"])  # tracing is real now
        self.assertEqual(
            {event["id"] for event in edu["events"]},
            {"letter.discovered", "alphabet.garden_completed", "alphabet.parade_completed"},
        )
        self.assertEqual(data["input"]["profile"], "hybrid")
        self.assertEqual(data["storage"]["schema_version"], 1)  # in-payload migration only

    def test_four_locale_key_parity(self) -> None:
        bundles = {
            locale: json.loads((ACTIVITY_ROOT / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
            for locale in ("en", "it", "es", "fr")
        }
        keys = {locale: set(bundle["strings"]) for locale, bundle in bundles.items()}
        self.assertEqual(len({frozenset(k) for k in keys.values()}), 1)
        for key in ("victory.title", "button.play_again"):
            self.assertIn(key, keys["en"])
        for bundle in bundles.values():
            for text in bundle["strings"].values():
                self.assertFalse(any(ord(ch) > 0x2000 for ch in text), text)  # no emoji


class ContentTests(unittest.TestCase):
    def test_en_it_pictures_match_the_approved_letter_clips(self) -> None:
        from alfabeto_art import resolve_picture

        for locale, joiner in (("en", " as "), ("it", " come ")):
            for item in get_letter_catalogue(locale):
                with self.subTest(locale=locale, letter=item.char):
                    text = _receipt_text(locale, f"letter_{item.char}")
                    self.assertEqual(text.lower(), f"{item.char}{joiner}{item.word_for(locale)}".lower())
                    self.assertTrue((ACTIVITY_ROOT / "assets" / "audio" / locale / f"ask_{item.char}.wav").is_file())
                    picture = item.picture_for(locale)
                    self.assertNotEqual(picture, PICTURE_PENDING)
                    self.assertTrue(resolve_picture(picture).is_file(), picture)

    def test_staged_pictures_resolve_or_are_marked_pending(self) -> None:
        from alfabeto_art import resolve_picture

        for locale in ("es", "fr"):
            for item in get_letter_catalogue(locale):
                picture = item.picture_for(locale)
                if picture != PICTURE_PENDING:
                    self.assertTrue(resolve_picture(picture).is_file(), (locale, item.char, picture))

    def test_activity_pictures_have_svg_masters(self) -> None:
        runtime = ACTIVITY_ROOT / "assets" / "runtime"
        names = {path.stem for path in runtime.glob("*.png")}
        self.assertTrue(names)
        for name in names:
            source = ACTIVITY_ROOT / "assets" / "source" / f"{name}.svg"
            self.assertTrue(source.is_file(), name)
            text = source.read_text(encoding="utf-8")
            for forbidden in ("<image", "<text", "<filter", "<style", "<script", "<mask"):
                self.assertNotIn(forbidden, text, name)

    def test_teaching_groups_cover_each_alphabet_once(self) -> None:
        for locale in ("en", "it", "es", "fr"):
            letters = "".join(teaching_groups(locale))
            alphabet = "".join(item.char for item in get_letter_catalogue(locale))
            self.assertEqual(sorted(letters), sorted(alphabet), locale)
            self.assertEqual(len(letters), len(set(letters)), locale)
        self.assertEqual(teaching_groups("en")[0], "SAT")  # never A→Z
        self.assertEqual(teaching_groups("it")[0], "AEI")

    def test_every_letter_has_stroke_order_shapes(self) -> None:
        for locale in ("en", "it", "es", "fr"):
            for item in get_letter_catalogue(locale):
                strokes = strokes_for(item.char)
                self.assertTrue(1 <= len(strokes) <= 4, item.char)
                for stroke in strokes:
                    self.assertGreaterEqual(len(stroke), 2)
        for char, related in LOOK_ALIKES.items():
            self.assertIn(char, LETTER_STROKES)
            self.assertNotIn(char, related)


class PlannerAndRoundTests(unittest.TestCase):
    def test_round_shape_and_choice_ladder(self) -> None:
        planner = GardenPlanner(random.Random(3), locale="en")
        for group, tiles in ((0, 2), (1, 2), (2, 3), (5, 3)):
            steps = planner.build(group)
            kinds = [step.kind for step in steps]
            self.assertEqual(kinds[:3], [StepKind.MEET, StepKind.FIND, StepKind.TRACE])
            self.assertEqual(kinds.count(StepKind.REVIEW), 2)
            for step in steps:
                if step.is_find:
                    self.assertEqual(len(step.choices), tiles)
                    self.assertEqual(step.choices[step.correct_index].char, step.letter.char)
        late = planner.build(5)
        finds = [step for step in late if step.is_find]
        self.assertTrue(all(any(c.char in LOOK_ALIKES[s.letter.char] for c in s.choices) for s in finds))
        early = [step for step in planner.build(0) if step.is_find]
        for step in early:
            self.assertFalse(any(c.char in LOOK_ALIKES[step.letter.char] for c in step.choices if c is not step.letter))

    def test_seeded_rounds_are_deterministic_and_answers_move(self) -> None:
        first = GardenPlanner(random.Random(11), locale="it").build(3)
        second = GardenPlanner(random.Random(11), locale="it").build(3)
        self.assertEqual(first, second)
        slots = [step.correct_index for step in first if step.is_find]
        self.assertTrue(all(a != b for a, b in zip(slots, slots[1:])))

    def test_review_after_alphabet_picks_least_traced(self) -> None:
        planner = GardenPlanner(random.Random(5), locale="en")
        traced = {item.char: 5 for item in LETTERS_CATALOGUE}
        traced.pop("Q")
        letters = planner.letters_for(planner.group_count, traced)
        self.assertEqual(len(letters), 3)
        self.assertIn("Q", {item.char for item in letters})

    def test_round_flow_errors_plant_and_complete_once(self) -> None:
        planner = GardenPlanner(random.Random(2), locale="en")
        round_ = GardenRound(planner.build(0), group=0)
        self.assertEqual(round_.task_total, 8)
        round_.finish_meet()
        step = round_.step
        wrong = 1 - step.correct_index
        self.assertFalse(round_.select(wrong).correct)
        self.assertIn(wrong, round_.eliminated)
        self.assertTrue(round_.select(step.correct_index).correct)
        self.assertEqual(round_.step.kind, StepKind.TRACE)
        round_.finish_trace()
        self.assertEqual([item.char for item in round_.planted], [step.letter.char])
        while not round_.is_complete:
            current = round_.step
            if current.kind is StepKind.MEET:
                round_.finish_meet()
            elif current.kind is StepKind.TRACE:
                round_.finish_trace()
            else:
                round_.select(current.correct_index)
        payload = round_.consume_completion()
        self.assertEqual(payload["letters"], 3)
        self.assertEqual(payload["retries"], 1)
        self.assertIsNone(round_.consume_completion())
        self.assertEqual(next_group(0, round_, planner.group_count), 1)
        round_.find_errors = 3
        self.assertEqual(next_group(4, round_, planner.group_count), 4)  # hard round repeats
        round_.find_errors = 0
        self.assertEqual(next_group(planner.group_count, round_, planner.group_count), planner.group_count)


class TraceTests(unittest.TestCase):
    def _follow(self, tracker: TraceTracker, stroke_index: int, *, every: int = 2) -> TraceEvent:
        stroke = tracker.guide.strokes[stroke_index]
        points = list(stroke.points[::every]) + [stroke.points[-1]]
        self.assertTrue(tracker.begin(points[0]))
        event = TraceEvent.NONE
        for point in points[1:]:
            event = tracker.move(point)
            if event in {TraceEvent.STROKE_DONE, TraceEvent.LETTER_DONE}:
                break
        tracker.end()
        return event

    def test_following_every_stroke_in_order_completes_the_letter(self) -> None:
        for char in ("A", "S", "O", "Ñ", "M"):
            tracker = TraceTracker(TraceGuide.fit(char, (0, 0, 360, 360)))
            events = [self._follow(tracker, index) for index in range(len(tracker.guide.strokes))]
            self.assertEqual(events[-1], TraceEvent.LETTER_DONE, char)
            self.assertTrue(tracker.complete)

    def test_wrong_end_and_loop_shortcuts_do_not_trace(self) -> None:
        tracker = TraceTracker(TraceGuide.fit("O", (0, 0, 360, 360)))
        ring = tracker.guide.strokes[0]
        # The end of the O sits next to its start: a tap there is near the
        # start, but sliding to the end point never jumps around the ring.
        self.assertTrue(tracker.begin(ring.start))
        self.assertIn(tracker.move(ring.points[-1]), {TraceEvent.NONE, TraceEvent.ADVANCED})
        self.assertLessEqual(tracker.progress, tracker.lookahead)
        self.assertLess(tracker.progress, ring.length * 0.2)
        tracker.end()
        line = TraceTracker(TraceGuide.fit("L", (0, 0, 360, 360)))
        last = line.guide.strokes[0].points[-1]
        self.assertFalse(line.begin(last))  # starting at the wrong end does nothing

    def test_lifting_the_finger_keeps_the_ink(self) -> None:
        tracker = TraceTracker(TraceGuide.fit("I", (0, 0, 360, 360)))
        stroke = tracker.guide.strokes[0]
        half = stroke.points[: len(stroke.points) // 2]
        tracker.begin(half[0])
        for point in half[1:]:
            tracker.move(point)
        tracker.end()
        kept = tracker.progress
        self.assertGreater(kept, stroke.length * 0.3)
        self.assertTrue(tracker.begin(stroke.point_at(kept)))
        for point in stroke.points[len(half):]:
            tracker.move(point)
        self.assertEqual(tracker.stroke_index, 1)

    def test_follow_the_dot_traces_without_a_pointer(self) -> None:
        tracker = TraceTracker(TraceGuide.fit("E", (0, 0, 300, 300)))
        events = []
        for _ in range(400):
            event = tracker.auto_advance(12.0)
            if event is not TraceEvent.ADVANCED:
                events.append(event)
            if tracker.complete:
                break
        self.assertEqual(events, [TraceEvent.STROKE_DONE] * 3 + [TraceEvent.LETTER_DONE])


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
    def test_v1_save_loads_and_is_carried_forward(self) -> None:
        port = GreiaAlfabetoProgress(_Storage({"discovered_letters": ["A", "B", "Ñ", 7], "rounds_completed": 4}))
        progress = port.load()
        self.assertEqual(progress.discovered_letters, {"A", "B", "Ñ"})
        self.assertEqual(progress.rounds_completed, 4)
        self.assertEqual(progress.group_for("en"), 0)
        self.assertTrue(progress.record_trace("C"))
        self.assertFalse(progress.record_trace("C"))
        payload = progress.to_payload()
        self.assertEqual(payload["schema_version"], 2)
        self.assertEqual(payload["discovered_letters"], ["A", "B", "C", "Ñ"])
        self.assertEqual(AlfabetoProgress.from_payload(payload).traced, {"C": 2})

    def test_malformed_payloads_recover_and_stay_bounded(self) -> None:
        for raw in (None, [], "x", {"groups": {"en": "high", "xx": 3}, "traced": {"AB": 3, "a": 1, "Z": True}}):
            progress = AlfabetoProgress.from_payload(raw)
            self.assertEqual(progress.traced, {})
            self.assertEqual(progress.groups, {})
        progress = AlfabetoProgress.from_payload({"groups": {"it": 10_000}, "traced": {"A": 10_000}})
        self.assertEqual(progress.groups["it"], 64)
        self.assertEqual(progress.traced["A"], 999)
        broken = GreiaAlfabetoProgress(_Storage())
        broken._storage = None
        self.assertIsInstance(broken.load(), AlfabetoProgress)


class _MockAudio:
    def __init__(self) -> None:
        self.played: list[str] = []
        self.sfx: list[str] = []

    def play_speech(self, cue_id: str) -> float | None:
        self.played.append(cue_id)
        return 1.0

    def stop_speech(self) -> None:
        return

    def play_sfx(self, cue: str) -> None:
        self.sfx.append(cue)


class _MockEvents:
    def __init__(self) -> None:
        self.learned: list[str] = []
        self.gardens: list[dict] = []
        self.alphabet: list[int] = []

    def letter_learned(self, session_id, char) -> None:
        self.learned.append(char)

    def garden_completed(self, session_id, payload) -> None:
        self.gardens.append(payload)

    def alphabet_completed(self, session_id, letters) -> None:
        self.alphabet.append(letters)


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
        from alfabeto_app import AlfabetoApp
        from alfabeto_art import AlfabetoArt
        from alfabeto_audio import SpeechQueue
        from alfabeto_renderer import AlfabetoRenderer

        screen = pygame.display.set_mode(size)
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale(locale, support)
        assert context is not None
        resources = LocalizedResources(ACTIVITY_ROOT, context)
        payload = saved if saved is not None else {"schema_version": 2, "groups": {locale: group}}
        self.storage = _Storage(payload)
        self.port = GreiaAlfabetoProgress(self.storage)
        self.events = _MockEvents()
        self.audio = _MockAudio()
        self.now = [100.0]
        return AlfabetoApp(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            planner=GardenPlanner(random.Random(21), locale=locale),
            progress=self.port.load(),
            progress_port=self.port,
            events=self.events,
            renderer=AlfabetoRenderer(AlfabetoArt(1024, 600)),
            typography=GreiaTypography(),
            resources=resources,
            audio=self.audio,
            speech_queue=SpeechQueue(self.audio),
            locale=locale,
            rng=random.Random(21),
            session_id="garden-1",
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

    def _trace_letter(self, app) -> None:
        box = app.controls.geometry.trace_box
        for stroke in app.tracker.guide.strokes:
            points = [(box.left + x, box.top + y) for x, y in list(stroke.points[::3]) + [stroke.points[-1]]]
            app._drag(points)
            self._run(app, 0.1)

    def _until(self, app, predicate, limit: float = 12.0) -> None:
        waited = 0.0
        while not predicate() and waited < limit:
            self._run(app, 0.1)
            waited += 0.1
        self.assertTrue(predicate(), f"timed out in state {app.state}")

    def test_full_garden_round_plays_to_completion_with_feedback_grammar(self) -> None:
        from greia_platform.activity_feedback import CastPose
        from alfabeto_app import AppState

        app = self._app("en", saved={"discovered_letters": ["Z"], "rounds_completed": 2})
        self.assertEqual(app.state, AppState.MEET)
        self._run(app, 1.6)
        self.assertEqual(self.audio.played[:2], ["leo.ready", "letter_S"])
        self.assertTrue(app.scene_state().leo_pointing)
        self._until(app, lambda: app.round.step.kind is StepKind.FIND)
        self._run(app, 0.2)
        self.assertIn("ask_S", self.audio.played)

        # Idle: Leo points and asks again; no tile is revealed.
        self._run(app, 8.0)
        self.assertTrue(app.scene_state().leo_pointing)
        self.assertGreaterEqual(self.audio.played.count("ask_S"), 2)
        self.assertIsNone(app.scene_state().hint_target)

        # A wrong tile: think pose, the tile retires, the right one is demonstrated.
        step = app.round.step
        wrong = 1 - step.correct_index
        self.assertTrue(self._tap_choice(app, wrong))
        self.assertEqual(app.state, AppState.TRY_AGAIN)
        self.assertEqual(app.renderer.cast.pose, CastPose.THINK)
        self._run(app, 0.6)
        self.assertIn("leo.retry", self.audio.played)
        self.assertFalse(app.controls.choices[wrong].enabled)
        self.assertEqual(app.state, AppState.PLAYING)

        while app.state is not AppState.TERMINAL:
            current = app.round.step
            if app.state is AppState.PLAYING and current is not None:
                if current.is_find:
                    self.assertTrue(self._tap_choice(app, current.correct_index))
                    self.assertEqual(app.state, AppState.CELEBRATE)
                    self.assertEqual(app.renderer.cast.pose, CastPose.CHEER)
                elif current.kind is StepKind.TRACE:
                    self._run(app, 0.6)
                    self.assertIsNotNone(app.scene_state().trace.demo_point)  # the hand shows the stroke
                    self._trace_letter(app)
                    self.assertEqual(app.state, AppState.BLOOM)
                    self.assertEqual(app.renderer.cast.pose, CastPose.CHEER)
            self._run(app, 0.2)
            if self.now[0] > 400:
                self.fail("round did not finish")

        self.assertEqual(self.events.learned, ["S", "A", "T"])
        self.assertEqual(len(self.events.gardens), 1)
        saved = self.storage.saved
        self.assertEqual(saved["groups"]["en"], 1)
        self.assertEqual(saved["rounds_completed"], 3)
        self.assertIn("Z", saved["discovered_letters"])  # v1 data is never lost
        self.assertEqual(set(saved["traced"]), {"S", "A", "T"})
        self.assertIn("leo.celebrate", self.audio.played)
        self.assertIn("leo.praise", self.audio.played)

        primary = app.completion.primary_rect
        physical = app.canvas.mapper.transform.logical_to_physical(primary.center)
        self.assertTrue(app._handle_pointer((int(physical[0]), int(physical[1]))))
        self.assertEqual(app.state, AppState.MEET)
        self.assertEqual([item.char for item in app.round.letters], list("PIN"))

    def test_keyboard_and_controller_play_find_and_trace(self) -> None:
        from alfabeto_app import AppState

        app = self._app("it", group=2)
        self._until(app, lambda: app.round.step.kind is StepKind.FIND)
        step = app.round.step
        self.assertEqual(app.controls.layer.focused_id, "choice.0")
        for _ in range(step.correct_index):
            self.assertTrue(app._handle_keyboard(pygame.K_RIGHT))
        self.assertTrue(app._handle_keyboard(pygame.K_SPACE))
        self.assertEqual(app.state, AppState.CELEBRATE)
        self._until(app, lambda: app.round.step.kind is StepKind.TRACE and app.state is AppState.PLAYING)
        self.assertEqual(app.controls.layer.focused_id, "trace")
        strokes = len(app.tracker.guide.strokes)
        for _ in range(strokes):
            self.assertTrue(app._handle_keyboard(pygame.K_SPACE))
            self._until(app, lambda: not app._auto_trace)
        self.assertEqual(app.state, AppState.BLOOM)

    def test_typed_letter_key_picks_its_tile(self) -> None:
        from alfabeto_app import AppState

        app = self._app("en", group=3)
        self._until(app, lambda: app.round.step.kind is StepKind.FIND)
        target = app.round.step.letter.char
        self.assertTrue(app._handle_keyboard(getattr(pygame, f"K_{target.lower()}")))
        self.assertEqual(app.state, AppState.CELEBRATE)

    def test_listen_button_replays_and_home_region_is_protected(self) -> None:
        app = self._app("en")
        self._until(app, lambda: app.round.step.kind is StepKind.FIND)
        self._run(app, 2.0)
        self.audio.played.clear()
        listen = app.controls.listen.rect.center
        physical = app.canvas.mapper.transform.logical_to_physical(listen)
        self.assertTrue(app._handle_pointer((int(physical[0]), int(physical[1]))))
        app.tick()
        self.assertEqual(self.audio.played[:1], ["ask_S"])
        self.assertFalse(app._handle_pointer((10, 10)))

    def test_small_screens_keep_controls_clear_of_home(self) -> None:
        from greia_platform.activity_controls import ControlLayout

        for size in ((800, 480), (480, 320)):
            with self.subTest(size=size):
                app = self._app("it", group=4, size=size)
                layout = ControlLayout.for_canvas(app.canvas, size)
                geometry = app.controls.geometry
                for rect in (geometry.listen, geometry.card, geometry.trace_box, app.controls.dots.rect):
                    self.assertFalse(rect.colliderect(layout.protected), rect)
                self._run(app, 1.0)

    def test_touch_far_from_the_stroke_only_pulses_the_start_dot(self) -> None:
        from greia_platform.activity_controls import KitPointer, PointerPhase

        app = self._app("en")
        self._until(app, lambda: app.round.step.kind is StepKind.FIND)
        self._tap_choice(app, app.round.step.correct_index)
        self._until(app, lambda: app.round.step.kind is StepKind.TRACE and app.tracker is not None)
        box = app.controls.geometry.trace_box
        self.assertTrue(app._trace_pointer(KitPointer(PointerPhase.DOWN, (box.right - 4, box.bottom - 4))))
        self.assertFalse(app.tracker.dragging)
        self.assertTrue(app.scene_state().trace.start_pulse)
        self.assertEqual(app.tracker.progress, 0.0)


class AudioTests(unittest.TestCase):
    def test_speech_queue_is_bounded_and_sequenced(self) -> None:
        from alfabeto_audio import SpeechQueue

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

    def test_only_letter_clips_and_shared_leo_lines_are_loaded(self) -> None:
        from alfabeto_audio import AlfabetoAudio

        pygame.mixer.init()
        try:
            audio = AlfabetoAudio(ACTIVITY_ROOT, locale="en")
            if not audio.has_speech("letter_A"):
                self.skipTest("audio decoding unavailable on this host")
            self.assertTrue(audio.has_speech("ask_Z"))
            self.assertFalse(audio.has_speech("intro"))
            self.assertTrue(audio.has_speech("leo.retry"))
        finally:
            pygame.mixer.quit()


if __name__ == "__main__":
    unittest.main()
