from __future__ import annotations

import os
from pathlib import Path
import random
import sys
import unittest

import pygame

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "casa_del_dieci"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from ten_house_model import (  # noqa: E402
    AttemptSummary,
    CHALLENGE_COUNT,
    HISTORY_LIMIT,
    OperationMode,
    Phase,
    RoomChange,
    RoomState,
    StagePresentation,
    TenHouseChallenge,
    TenHouseRoundFactory,
    TenHouseSession,
    adapt_level,
    near_miss_choices,
)
from ten_house_services import GreiaTenHouseProgress, TenHouseProgress  # noqa: E402


def _challenge(mode: OperationMode, target: int, start: int, delta: int, answer: int, choices=()) -> TenHouseChallenge:
    return TenHouseChallenge(f"t-{mode}-{target}-{start}", mode, target, start, delta, answer, tuple(choices))


class TenHouseRoundFactoryTests(unittest.TestCase):
    def test_seed_is_deterministic_and_sets_have_six_challenges(self) -> None:
        first = TenHouseRoundFactory(random.Random(12345)).build_set(3)
        second = TenHouseRoundFactory(random.Random(12345)).build_set(3)
        self.assertEqual(first, second)
        self.assertEqual(len(first), CHALLENGE_COUNT)

    def test_levels_are_stages_of_one_loop(self) -> None:
        factory = TenHouseRoundFactory(random.Random(7))
        modes = {level: {c.mode for c in factory.build_set(level)} for level in range(1, 6)}
        self.assertEqual(modes[1], {OperationMode.COMPOSE})
        self.assertEqual(modes[2], {OperationMode.COMPOSE})
        self.assertEqual(modes[3], {OperationMode.ADD, OperationMode.COMPOSE})
        self.assertIn(OperationMode.TAKE_AWAY, modes[4])
        self.assertIn(OperationMode.MISSING_PART, modes[5])
        level1 = factory.build_set(1)
        self.assertTrue(all(c.starting_lit == 0 for c in level1))
        level2 = factory.build_set(2)
        self.assertTrue(any(c.starting_lit > 0 for c in level2), "level 2 makes numbers from a given part")

    def test_invariants_and_near_miss_distractors_hold_across_seeds(self) -> None:
        for seed in range(40):
            factory = TenHouseRoundFactory(random.Random(seed))
            for level in range(1, 6):
                for c in factory.build_set(level):
                    if c.mode == OperationMode.COMPOSE:
                        self.assertEqual(c.choice_values, ())
                        self.assertLess(c.starting_lit, c.target)
                        continue
                    self.assertEqual(len(set(c.choice_values)), 3)
                    self.assertIn(c.answer, c.choice_values)
                    for value in c.choice_values:
                        self.assertLessEqual(abs(value - c.answer), 2, f"{c} distractor too far")
                        self.assertTrue(0 <= value <= 10)
                    if c.mode == OperationMode.ADD:
                        self.assertEqual(c.starting_lit + c.delta, c.answer)
                    elif c.mode == OperationMode.TAKE_AWAY:
                        self.assertEqual(c.starting_lit - c.delta, c.answer)
                        self.assertGreaterEqual(c.answer, 1)
                    else:
                        self.assertEqual(c.starting_lit + c.answer, c.target)

    def test_near_miss_choices_always_include_a_plus_minus_one(self) -> None:
        rng = random.Random(3)
        for answer in range(1, 11):
            values = near_miss_choices(answer, rng)
            self.assertIn(answer, values)
            self.assertTrue(any(abs(v - answer) == 1 for v in values))

    def test_challenge_rejects_answer_revealing_or_far_distractors(self) -> None:
        with self.assertRaises(ValueError):
            _challenge(OperationMode.ADD, 7, 5, 2, 7, (7, 1, 9))
        with self.assertRaises(ValueError):
            _challenge(OperationMode.COMPOSE, 4, 4, 0, 4)


class TenHouseSessionTests(unittest.TestCase):
    def test_rooms_fill_in_ten_frame_order_wherever_the_child_taps(self) -> None:
        session = TenHouseSession([_challenge(OperationMode.COMPOSE, 7, 0, 0, 7)] * 6, level=1)
        self.assertEqual(session.phase, Phase.BUILD)
        for tapped in (9, 3, 6, 8):
            self.assertEqual(session.tap_room(tapped), RoomChange.LIT)
        self.assertEqual(session.room_states, (True,) * 4 + (False,) * 6)
        self.assertEqual(session.tap_room(1), RoomChange.UNLIT)  # a lit room removes the last one
        self.assertEqual(session.lit, 3)
        self.assertEqual(session.room_state(0), RoomState.HOME)

    def test_given_part_is_locked_and_added_rooms_are_guests(self) -> None:
        session = TenHouseSession([_challenge(OperationMode.COMPOSE, 7, 5, 0, 7)] * 6, level=2)
        self.assertEqual(session.lit, 5)
        self.assertEqual(session.tap_room(0), RoomChange.NONE)
        session.tap_room(8)
        self.assertEqual(session.room_state(4), RoomState.HOME)
        self.assertEqual(session.room_state(5), RoomState.GUEST)

    def test_wrong_confirm_then_retry_records_evidence(self) -> None:
        session = TenHouseSession([_challenge(OperationMode.COMPOSE, 3, 0, 0, 3)] * 6, level=1)
        session.tap_room(0)
        self.assertFalse(session.confirm().correct)
        self.assertEqual(session.phase, Phase.BUILD)
        session.tap_room(5)
        session.tap_room(5)
        result = session.confirm()
        self.assertTrue(result.correct)
        self.assertTrue(result.used_retry)
        self.assertEqual(session.phase, Phase.SOLVED)
        self.assertEqual(session.completed_count, 1)
        self.assertIsNotNone(session.consume_milestone())
        session.advance()
        self.assertEqual(session.challenge_index, 1)
        self.assertEqual(session.lit, 0)

    def test_add_is_enacted_before_asking(self) -> None:
        session = TenHouseSession([_challenge(OperationMode.ADD, 7, 5, 2, 7, (6, 7, 8))] * 6, level=3)
        self.assertEqual(session.phase, Phase.ARRIVING)
        with self.assertRaises(RuntimeError):
            session.choose(7)
        self.assertTrue(session.invite_guest())
        self.assertTrue(session.invite_guest())
        self.assertFalse(session.invite_guest())
        self.assertEqual(session.phase, Phase.ASKING)
        self.assertEqual(session.room_state(6), RoomState.GUEST)
        self.assertFalse(session.choose(8).correct)
        self.assertIn(8, session.rejected)
        self.assertTrue(session.choose(7).correct)

    def test_take_away_lights_leave_before_asking(self) -> None:
        session = TenHouseSession([_challenge(OperationMode.TAKE_AWAY, 6, 8, 2, 6, (5, 6, 7))] * 6, level=4)
        self.assertEqual(session.phase, Phase.LEAVING)
        session.depart_one()
        session.depart_one()
        self.assertFalse(session.depart_one())
        self.assertEqual((session.lit, session.phase), (6, Phase.ASKING))

    def test_missing_part_correct_answer_fills_the_house(self) -> None:
        session = TenHouseSession([_challenge(OperationMode.MISSING_PART, 10, 7, 0, 3, (2, 3, 4))] * 6, level=5)
        self.assertEqual(session.phase, Phase.ASKING)
        self.assertFalse(session.choose(4).correct)
        self.assertEqual(session.lit, 7)
        self.assertTrue(session.choose(3).correct)
        self.assertEqual(session.lit, 10)

    def test_completion_payload_is_one_shot(self) -> None:
        session = TenHouseSession(TenHouseRoundFactory(random.Random(42)).build_set(1), level=1)
        for index in range(CHALLENGE_COUNT):
            current = session.current_challenge
            assert current is not None
            while session.lit < current.target:
                session.tap_room(9)
            self.assertTrue(session.confirm().correct)
            if index < CHALLENGE_COUNT - 1:
                session.advance()
        payload = session.consume_completion()
        self.assertIsNotNone(payload)
        self.assertEqual(payload["first_attempt_count"], CHALLENGE_COUNT)
        self.assertIsNone(session.consume_completion())

    def test_scaffolds_fade_with_level(self) -> None:
        self.assertTrue(StagePresentation.for_level(1).sign_dots)
        self.assertFalse(StagePresentation.for_level(2).sign_dots)
        self.assertTrue(StagePresentation.for_level(3).card_frames)
        self.assertFalse(StagePresentation.for_level(4).card_frames)
        self.assertFalse(StagePresentation.for_level(5).card_frames)


class AdaptationTests(unittest.TestCase):
    def test_adaptation_respects_level_bounds(self) -> None:
        strong = [AttemptSummary(True, 0, False) for _ in range(HISTORY_LIMIT)]
        struggling = [AttemptSummary(False, 2, True) for _ in range(3)]
        self.assertEqual(adapt_level(1, strong), 2)
        self.assertEqual(adapt_level(5, strong), 5)
        self.assertEqual(adapt_level(4, struggling), 3)
        self.assertEqual(adapt_level(1, struggling), 1)


class _Storage:
    def __init__(self, value=None) -> None:
        self.value = value
        self.saved = None

    def kv_get(self, key):
        return self.value

    def kv_set(self, key, value):
        self.saved = value


class ProgressTests(unittest.TestCase):
    def test_malformed_storage_recovers_and_save_is_bounded(self) -> None:
        storage = _Storage({"schema_version": 1, "level": 99, "history": "corrupt"})
        repo = GreiaTenHouseProgress(storage)
        self.assertEqual(repo.load(), TenHouseProgress())
        history = [AttemptSummary(True, 0, False) for _ in range(20)]
        repo.save(3, history)
        self.assertEqual(storage.saved["level"], 3)
        self.assertEqual(len(storage.saved["history"]), HISTORY_LIMIT)

    def test_existing_v1_saves_still_load(self) -> None:
        storage = _Storage(
            {
                "schema_version": 1,
                "level": 4,
                "history": [{"first_attempt_success": True, "hints_used": 0, "used_retry": False}],
            }
        )
        loaded = GreiaTenHouseProgress(storage).load()
        self.assertEqual(loaded.level, 4)
        self.assertEqual(loaded.history, (AttemptSummary(True, 0, False),))


class _MockEvents:
    def __init__(self) -> None:
        self.milestones = []
        self.completions = []

    def room_completed(self, session_id, payload) -> None:
        self.milestones.append(payload)

    def house_completed(self, session_id, payload) -> None:
        self.completions.append(payload)


class _MockAudio:
    def __init__(self) -> None:
        self.played: list[str] = []
        self.spoken: list[str] = []

    def play(self, cue: str) -> None:
        self.played.append(cue)

    def chime(self, number: int) -> None:
        self.played.append(f"chime_{number}")

    def say(self, cue: str) -> None:
        self.spoken.append(cue)

    def say_if_quiet(self, cue: str) -> None:
        self.spoken.append(cue)

    def praise(self) -> None:
        self.spoken.append("correct")

    def encourage(self) -> None:
        self.spoken.append("retry")

    def stop_speech(self) -> None:
        pass


class AppIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600))

    def _build_app(self, level: int, *, seed: int = 77):
        from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from ten_house_app import TenHouseActivity

        screen = pygame.display.get_surface()
        assert screen is not None
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale("it", support)
        assert context is not None
        resources = LocalizedResources(ACTIVITY_ROOT, context)
        storage = _Storage({"schema_version": 1, "level": level, "history": []})
        events = _MockEvents()
        audio = _MockAudio()
        rng = random.Random(seed)
        factory = TenHouseRoundFactory(rng)
        session = TenHouseSession(factory.build_set(level), level=level)
        clock = [100.0]
        app = TenHouseActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            session=session,
            factory=factory,
            typography=GreiaTypography(),
            resources=resources,
            progress=GreiaTenHouseProgress(storage),
            events=events,
            audio=audio,
            rng=rng,
            session_id="casa-session-1",
            clock=lambda: clock[0],
        )
        self._clock = clock
        self._app = app
        self._storage = storage
        return app, events, audio

    def _advance(self, seconds: float, step: float = 0.05) -> None:
        end = self._clock[0] + seconds
        while self._clock[0] < end:
            self._clock[0] += step
            self._app.step()

    def _tap(self, rect) -> bool:
        return self._app.tap(rect.center)

    def test_no_counter_or_printed_sum_on_the_play_screen(self) -> None:
        from greia_platform.activity_controls import HudChip, PromptBanner

        app, _, audio = self._build_app(level=1)
        self.assertFalse(any(isinstance(t, (PromptBanner, HudChip)) for t in app.controls.layer.targets))
        challenge = app.session.current_challenge
        self.assertIn(f"prompt_compose_{challenge.target}", audio.spoken)
        app.render()  # one real frame through the shared kit

    def test_keyboard_lights_rooms_in_order_and_confirms(self) -> None:
        app, _, audio = self._build_app(level=1)
        self._advance(1.0)
        layer = app.controls.layer
        self.assertEqual(layer.focused_id, "room.0")
        app.press(pygame.K_RIGHT)
        self.assertEqual(layer.focused_id, "room.1")
        app.press(pygame.K_SPACE)
        self.assertEqual(app.session.lit, 1)
        self.assertIn("pop", audio.played)
        self.assertEqual(app.session.room_states[0], True)

    def test_wrong_house_shows_think_pose_demonstrates_and_allows_retry(self) -> None:
        from greia_platform.activity_feedback import CastPose
        from ten_house_layout import CONFIRM_RECT, ROOM_RECTS

        app, _, audio = self._build_app(level=1)
        self._advance(1.0)
        target = app.session.current_challenge.target
        self._tap(ROOM_RECTS[5])
        self.assertTrue(self._tap(CONFIRM_RECT))
        self.assertEqual(app.cast.pose, CastPose.THINK)
        self.assertIn("retry", audio.spoken)
        self._advance(1.0)
        self.assertTrue(app.motion.badges, "Dani counts the lit rooms with badges")
        self.assertFalse(self._tap(ROOM_RECTS[6]), "the house is locked while Dani demonstrates")
        self._advance(4.0)
        while app.session.lit < target:
            self.assertTrue(self._tap(ROOM_RECTS[9]))
        self.assertTrue(self._tap(CONFIRM_RECT))
        self.assertEqual(app.session.phase, Phase.SOLVED)
        self._advance(0.2)
        self.assertEqual(app.cast.pose, CastPose.CHEER)
        self.assertTrue(app.motion.bond)

    def test_guests_are_brought_in_by_the_child_then_asked(self) -> None:
        from ten_house_layout import CHOICE_RECTS

        app, events, audio = self._build_app(level=3, seed=11)
        while app.session.current_challenge.mode is not OperationMode.ADD:
            app.session._index += 1
            app.session._reset_for_current()
            app._start_round()
        self._advance(1.5)
        self.assertIn("friends_coming", audio.spoken)  # guests appear: Dani invites them in
        self.assertFalse(app.controls.choices[0].visible)
        waiting = list(app.motion.waiting)
        self.assertEqual(app.controls.layer.focused_id, f"guest.{waiting[0]}")
        for _ in waiting:
            app.press(pygame.K_SPACE)
            self._advance(0.1)
        self._advance(1.2)
        self.assertEqual(app.session.phase, Phase.ASKING)
        self.assertIn("prompt_add", audio.spoken)
        challenge = app.session.current_challenge
        index = challenge.choice_values.index(challenge.answer)
        self.assertTrue(self._tap(CHOICE_RECTS[index]))
        self.assertEqual(len(events.milestones), 1)

    def test_take_away_and_missing_part_are_acted_out(self) -> None:
        from ten_house_layout import CHOICE_RECTS

        app, _, audio = self._build_app(level=4, seed=3)
        challenge = app.session.current_challenge
        self.assertEqual(challenge.mode, OperationMode.TAKE_AWAY)
        self.assertFalse(self._tap(CHOICE_RECTS[0]), "no answer before the lights have left")
        self._advance(6.0)
        self.assertEqual(app.session.phase, Phase.ASKING)
        # The departure line comes first, the question after the lights have left.
        self.assertLess(audio.spoken.index("fireflies_home"), audio.spoken.index("prompt_take_away"))
        self.assertEqual(app.motion.sky, challenge.delta)

        app, _, audio = self._build_app(level=5, seed=8)
        while app.session.current_challenge.mode is not OperationMode.MISSING_PART:
            app.session._index += 1
            app.session._reset_for_current()
            app._start_round()
        self._advance(1.5)
        challenge = app.session.current_challenge
        wrong = next(v for v in challenge.choice_values if v != challenge.answer)
        lit = app.session.lit
        self.assertTrue(self._tap(CHOICE_RECTS[challenge.choice_values.index(wrong)]))
        self._advance(0.1)
        self.assertTrue(app.motion.flights, "the chosen fireflies try to move in")
        self._advance(9.0)
        self.assertEqual(app.session.lit, lit, "a wrong try leaves the house as it was")
        self.assertIn("retry", audio.spoken)
        # The counting demonstration invites the child after the retry line.
        self.assertLess(audio.spoken.index("retry"), audio.spoken.index("count_lights"))
        self.assertFalse(app.controls.choices[challenge.choice_values.index(wrong)].enabled)
        self.assertTrue(self._tap(CHOICE_RECTS[challenge.choice_values.index(challenge.answer)]))
        self._advance(3.0)
        self.assertEqual(app.session.lit, challenge.target)

    def test_controller_reaches_answers_and_listen(self) -> None:
        from greia_platform import pygame_input

        app, _, audio = self._build_app(level=4, seed=3)
        self._advance(6.0)
        layer = app.controls.layer
        self.assertTrue(layer.focused_id.startswith("choice."))
        for _ in range(4):
            app.press(pygame.K_UP)
        self.assertEqual(layer.focused_id, "listen")
        app.press(pygame.K_SPACE)
        self.assertIn("prompt_take_away", audio.spoken)
        if pygame_input.sdl_controller is not None and pygame_input._CONTROLLER_BUTTON_DOWN >= 0:
            press = pygame_input._CONTROLLER_BUTTON_DOWN
            for _ in range(4):
                app._handle_event(pygame.event.Event(press, button=pygame_input.CONTROLLER_BUTTON_DPAD_DOWN))
            self.assertTrue(layer.focused_id.startswith("choice."))
            app._handle_event(pygame.event.Event(press, button=pygame_input.CONTROLLER_BUTTON_A))
            self.assertTrue("retry" in audio.spoken or "correct" in audio.spoken)

    def test_idle_hint_points_without_revealing(self) -> None:
        app, _, _ = self._build_app(level=2)
        self._advance(7.0)
        self.assertTrue(app.cast.pointing)
        self.assertFalse(app.motion.badges, "an idle hint never prints numbers")

    def test_protected_chrome_region_is_ignored(self) -> None:
        app, _, _ = self._build_app(level=1)
        self._advance(1.0)
        self.assertFalse(app.tap((4, 4)))
        self.assertEqual(app.session.lit, 0)

    def test_full_visit_plays_to_completion_and_restarts(self) -> None:
        from ten_house_app import AppState
        from ten_house_layout import CHOICE_RECTS, CONFIRM_RECT, ROOM_RECTS

        app, events, _ = self._build_app(level=3, seed=5)
        for _ in range(CHALLENGE_COUNT):
            self._advance(1.5)
            session = app.session
            challenge = session.current_challenge
            if challenge.mode is OperationMode.COMPOSE:
                while session.lit < challenge.target:
                    self._tap(ROOM_RECTS[session.lit])
                self.assertTrue(self._tap(CONFIRM_RECT))
            else:
                for slot in list(app.motion.waiting):
                    app.tap(app.controls.guests[slot].rect.center)
                    self._advance(0.1)
                self._advance(1.5)
                index = challenge.choice_values.index(challenge.answer)
                self.assertTrue(self._tap(CHOICE_RECTS[index]))
            self._advance(4.5)
        self.assertEqual(app.state, AppState.TERMINAL)
        self.assertEqual(len(events.milestones), CHALLENGE_COUNT)
        self.assertEqual(len(events.completions), 1)
        # Six clean answers are not yet the eight-strong window needed to level up.
        self.assertEqual(self._storage.saved["level"], 3)
        self.assertEqual(len(self._storage.saved["history"]), CHALLENGE_COUNT)
        app.render()
        handled = app.tap(app.completion.primary_rect.center)
        self.assertTrue(handled)
        self.assertEqual(app.state, AppState.PLAYING)
        self.assertEqual(app.session.level, 3)
        self.assertEqual(app.session.challenge_index, 0)


if __name__ == "__main__":
    unittest.main()
