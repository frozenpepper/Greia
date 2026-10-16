from __future__ import annotations

import os
from pathlib import Path
import random
import sys
import tomllib
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

import hermetic_volume


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "luci_di_momo"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from firefly_model import (  # noqa: E402
    HISTORY_LIMIT,
    MIN_CENTER_SEPARATION,
    ROUND_COUNT,
    Arrangement,
    AttemptSummary,
    FireflyRound,
    FireflyRoundFactory,
    FireflySession,
    adapt_level,
    frame_cell_center,
    stage_rule,
)
from firefly_services import FireflyProgress, GreiaFireflyProgress  # noqa: E402


def setUpModule() -> None:
    # The Simulator supervision test exercises real history/storage services,
    # whose production capacity policy depends on how full the host disk is.
    hermetic_volume.install_for_module()


class FireflyRoundFactoryTests(unittest.TestCase):
    def test_seed_is_deterministic_and_rounds_obey_bounds(self) -> None:
        for level in range(1, 5):
            first = FireflyRoundFactory(random.Random(12345)).build_set(level)
            second = FireflyRoundFactory(random.Random(12345)).build_set(level)
            self.assertEqual(first, second)
            self.assertEqual(len(first), ROUND_COUNT)
            for round_ in first:
                self.assertEqual(len(round_.positions), round_.quantity)
                self.assertEqual(sum(round_.groups), round_.quantity)
                for index, point in enumerate(round_.positions):
                    for other in round_.positions[index + 1:]:
                        dx = point[0] - other[0]
                        dy = point[1] - other[1]
                        self.assertGreaterEqual((dx * dx + dy * dy) ** 0.5, MIN_CENTER_SEPARATION)

    def test_ladder_amounts_arrangements_and_card_faces(self) -> None:
        expected = {
            1: (1, 5, {Arrangement.DICE}, True),
            2: (2, 6, {Arrangement.DICE, Arrangement.SCATTER}, True),
            3: (4, 8, {Arrangement.GROUPS}, True),
            4: (6, 10, {Arrangement.TEN_FRAME}, False),
        }
        for level, (low, high, arrangements, dots) in expected.items():
            rule = stage_rule(level)
            self.assertEqual(rule.card_dots, dots)
            seen: set[Arrangement] = set()
            for seed in range(20):
                for round_ in FireflyRoundFactory(random.Random(seed)).build_set(level):
                    self.assertTrue(low <= round_.quantity <= high, (level, round_.quantity))
                    self.assertIn(round_.arrangement, arrangements)
                    self.assertEqual(round_.reveal_ms, rule.reveal_ms)
                    self.assertLessEqual(round_.reveal_ms, 1600)
                    seen.add(round_.arrangement)
            self.assertEqual(seen, arrangements)

    def test_distractors_are_near_misses_with_one_neighbour(self) -> None:
        for level in range(1, 5):
            for seed in range(25):
                for round_ in FireflyRoundFactory(random.Random(seed)).build_set(level):
                    values = round_.choice_values
                    self.assertEqual(len(set(values)), 3)
                    self.assertIn(round_.quantity, values)
                    offsets = sorted(abs(v - round_.quantity) for v in values if v != round_.quantity)
                    self.assertEqual(offsets[0], 1, values)
                    self.assertLessEqual(offsets[1], 2, values)
                    self.assertTrue(all(1 <= v <= 10 for v in values))

    def test_consecutive_rounds_never_repeat_the_amount(self) -> None:
        for seed in range(10):
            rounds = FireflyRoundFactory(random.Random(seed)).build_set(2)
            for before, after in zip(rounds, rounds[1:]):
                self.assertNotEqual(before.quantity, after.quantity)

    def test_ten_frame_fills_the_top_row_first_and_groups_five_and_more(self) -> None:
        for round_ in FireflyRoundFactory(random.Random(3)).build_set(4):
            self.assertEqual(round_.positions, tuple(frame_cell_center(i) for i in range(round_.quantity)))
            self.assertEqual(round_.groups, (5, round_.quantity - 5))
            self.assertEqual(round_.lead_group, 5)

    def test_grouped_glimpses_show_two_small_parts(self) -> None:
        for seed in range(10):
            for round_ in FireflyRoundFactory(random.Random(seed)).build_set(3):
                self.assertEqual(len(round_.groups), 2)
                self.assertTrue(all(1 <= part <= 5 for part in round_.groups))
                split = round_.groups[0]
                left = max(x for x, _ in round_.positions[:split])
                right = min(x for x, _ in round_.positions[split:])
                self.assertGreater(right - left, 150, "the two parts must read as separate groups")

    def test_round_rejects_far_distractors_and_bad_partitions(self) -> None:
        with self.assertRaises(ValueError):
            FireflyRound("r", 3, ((560, 230), (650, 230), (740, 230)), (3, 4, 6), 1500)
        with self.assertRaises(ValueError):
            FireflyRound("r", 3, ((560, 230), (650, 230), (740, 230)), (2, 3, 4), 1500, groups=(1, 1))


class FireflySessionTests(unittest.TestCase):
    def _session(self) -> FireflySession:
        rounds = FireflyRoundFactory(random.Random(77)).build_set(2)
        return FireflySession(rounds, level=2)

    def test_wrong_answer_and_replay_do_not_advance_round(self) -> None:
        session = self._session()
        current = session.current_round
        assert current is not None
        wrong = next(value for value in current.choice_values if value != current.quantity)

        result = session.choose(wrong)
        self.assertFalse(result.correct)
        self.assertTrue(session.missed)
        self.assertEqual(session.rejected, frozenset({wrong}))
        self.assertEqual(session.round_index, 0)

        session.mark_replay()
        self.assertTrue(session.replay_used)
        self.assertIs(session.current_round, current)

        result = session.choose(current.quantity)
        self.assertTrue(result.correct)
        self.assertTrue(result.used_replay)
        self.assertFalse(result.first_attempt_success)
        self.assertEqual(session.round_index, 1)
        self.assertEqual(session.rejected, frozenset())
        self.assertFalse(session.replay_used)

    def test_idle_hints_count_as_scaffolding(self) -> None:
        session = self._session()
        current = session.current_round
        assert current is not None
        session.note_hint()
        result = session.choose(current.quantity)
        self.assertTrue(result.first_attempt_success)
        self.assertEqual(result.hints_used, 1)

    def test_completion_payload_is_one_shot(self) -> None:
        session = self._session()
        while not session.is_complete:
            current = session.current_round
            assert current is not None
            session.choose(current.quantity)

        payload = session.consume_completion()
        self.assertEqual(payload, {"level": 2, "first_attempt_count": ROUND_COUNT, "replays": 0})
        self.assertIsNone(session.consume_completion())


class AdaptationTests(unittest.TestCase):
    def test_level_moves_only_from_bounded_recent_evidence(self) -> None:
        strong = [AttemptSummary(True, 0, False) for _ in range(HISTORY_LIMIT)]
        self.assertEqual(adapt_level(2, strong), 3)
        self.assertEqual(adapt_level(4, strong), 4)

        scaffolded = [AttemptSummary(False, 2, False) for _ in range(3)]
        self.assertEqual(adapt_level(3, scaffolded), 2)
        self.assertEqual(adapt_level(1, scaffolded), 1)

        mixed = [AttemptSummary(True, 0, False), AttemptSummary(False, 1, True)]
        self.assertEqual(adapt_level(2, mixed), 2)


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
        storage = _Storage({"schema_version": 1, "level": 99, "history": ["bad"]})
        repo = GreiaFireflyProgress(storage)
        self.assertEqual(repo.load(), FireflyProgress())

        history = [AttemptSummary(i % 2 == 0, i % 3, False) for i in range(20)]
        repo.save(4, history)
        self.assertIsNotNone(storage.saved)
        self.assertEqual(storage.saved["level"], 4)
        self.assertEqual(len(storage.saved["history"]), HISTORY_LIMIT)

    def test_existing_v1_saves_still_load(self) -> None:
        saved = {
            "schema_version": 1,
            "level": 3,
            "history": [{"first_attempt_success": True, "hints_used": 0, "used_replay": False}],
        }
        progress = GreiaFireflyProgress(_Storage(saved)).load()
        self.assertEqual(progress.level, 3)
        self.assertEqual(progress.history, (AttemptSummary(True, 0, False),))
        FireflySession(FireflyRoundFactory(random.Random(1)).build_set(progress.level), level=progress.level,
                       history=progress.history)


class ManifestAndLocaleTests(unittest.TestCase):
    def test_manifest_matches_the_subitizing_rung(self) -> None:
        manifest = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["activity"]["id"], "org.greia.luci-di-momo")
        self.assertEqual(manifest["activity"]["languages"], ["it", "en"])
        self.assertEqual(manifest["input"]["profile"], "hybrid")
        education = manifest["education"]
        self.assertEqual((education["recommended_age_min"], education["recommended_age_max"]), (4, 6))
        self.assertIn("subitizing", education["categories"])
        self.assertEqual((education["difficulty_min"], education["difficulty_max"]), (1, 4))
        self.assertEqual(education["events"], [{"id": "firefly.garden_completed", "kind": "completion"}])
        self.assertEqual(manifest["storage"]["schema_version"], 1)

    def test_locales_have_key_parity_and_no_emoji_buttons(self) -> None:
        import json

        bundles = {
            locale: json.loads((ACTIVITY_ROOT / "locales" / f"{locale}.json").read_text(encoding="utf-8"))["strings"]
            for locale in ("en", "it", "es", "fr")
        }
        keys = set(bundles["en"])
        for locale, strings in bundles.items():
            self.assertEqual(set(strings), keys, locale)
            for value in strings.values():
                self.assertTrue(value.strip())
                self.assertFalse(any(ord(ch) > 0x2FFF for ch in value), (locale, value))


class _MockEvents:
    def __init__(self) -> None:
        self.emitted: list[tuple[str, dict[str, int]]] = []

    def garden_completed(self, session_id: str, payload: dict[str, int]) -> None:
        self.emitted.append((session_id, payload))


class _MockAudio:
    def __init__(self) -> None:
        self.played: list[str] = []
        self.speech: list[str] = []
        self.chimes: list[int] = []

    def play(self, cue: str) -> None:
        self.played.append(cue)

    def chime(self, number: int) -> None:
        self.chimes.append(number)

    def play_speech(self, cue_id: str) -> None:
        self.speech.append(cue_id)

    def speech_seconds(self, cue_id: str) -> float:
        return 3.0 if cue_id == "welcome" else 0.0

    def play_welcome(self) -> None:
        self.speech.append("welcome")

    def play_prompt_choose(self) -> None:
        self.speech.append("prompt_choose")

    def play_count(self, quantity: int) -> bool:
        if quantity > 5:
            return False
        self.speech.append(f"count_{quantity}")
        return True

    def praise(self) -> None:
        self.speech.append("praise")

    def encourage(self) -> None:
        self.speech.append("retry")

    def play_garden_complete(self) -> None:
        self.played.append("complete")
        self.speech.append("garden_complete")


class FireflyAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600))

    def _build_app(self, level: int = 1, *, size: tuple[int, int] = (1024, 600)):
        from firefly_app import FireflyActivity
        from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography

        screen = pygame.display.set_mode(size)
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale("it", support)
        assert context is not None
        resources = LocalizedResources(ACTIVITY_ROOT, context)
        storage = _Storage({"schema_version": 1, "level": level, "history": []})
        progress = GreiaFireflyProgress(storage)
        events = _MockEvents()
        audio = _MockAudio()
        rng = random.Random(42)
        factory = FireflyRoundFactory(rng)
        session = FireflySession(factory.build_set(level), level=level)
        now = [100.0]
        app = FireflyActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            session=session,
            factory=factory,
            typography=GreiaTypography(),
            resources=resources,
            progress=progress,
            events=events,
            audio=audio,
            rng=rng,
            session_id="test-session-1",
            clock=lambda: now[0],
        )
        return app, now, events, audio, storage

    @staticmethod
    def _advance(app, now, seconds: float, step: float = 0.05) -> None:
        end = now[0] + seconds
        while now[0] < end:
            now[0] = min(end, now[0] + step)
            app.step()

    def _wait_for_cards(self, app, now) -> None:
        for _ in range(400):
            if app.asking and not app._busy:
                return
            self._advance(app, now, 0.05)
        self.fail("the cards never appeared")

    @staticmethod
    def _physical(app, rect: pygame.Rect) -> tuple[int, int]:
        x, y = app.canvas.mapper.transform.logical_to_physical(rect.center)
        return (int(x), int(y))

    def _tap_value(self, app, value: int) -> bool:
        index = app.controls.index_of(value)
        self.assertIsNotNone(index)
        return app.tap(self._physical(app, app.controls.choices[index].rect))

    def test_glimpse_starts_without_a_play_button_and_hides_the_cards(self) -> None:
        app, now, _, audio, _ = self._build_app(level=1)
        self.assertEqual(audio.speech[0], "welcome")
        self.assertFalse(app.asking)
        self.assertTrue(all(not button.visible for button in app.controls.choices))
        app.render()
        # Fireflies glow only after Momo's welcome and the "watch!" cue.
        self._advance(app, now, 3.3 + 0.95)
        self.assertIsNotNone(app.motion.shown_from)
        self.assertGreaterEqual(now[0], app.motion.shown_from)
        self.assertIn("reveal", audio.played)
        self.assertTrue(all(not button.visible for button in app.controls.choices))
        app.render()
        self._wait_for_cards(app, now)
        # Once the cards are open, nothing on screen shows the fireflies.
        self.assertGreaterEqual(now[0], app.motion.hide_at)
        self.assertTrue(all(button.visible and button.enabled for button in app.controls.choices))
        self.assertIn("prompt_choose", audio.speech)
        app.render()

    def test_wrong_answer_thinks_demonstrates_and_allows_kind_retry(self) -> None:
        app, now, _, audio, _ = self._build_app(level=3)
        self._wait_for_cards(app, now)
        current = app.session.current_round
        assert current is not None
        wrong = next(value for value in current.choice_values if value != current.quantity)
        self.assertTrue(self._tap_value(app, wrong))
        self.assertEqual(app.cast.pose.value, "think")
        self.assertIn("retry", audio.played)
        self.assertIn("retry", audio.speech)
        self.assertTrue(app._busy)
        self.assertFalse(app.controls.replay.visible)
        self._wait_for_cards(app, now)
        # Momo counted together: the first part at once, then counting on.
        numbers = [badge.number for badge in app.motion.badges]
        self.assertEqual(numbers[0], current.groups[0])
        self.assertEqual(numbers[-1], current.quantity)
        self.assertEqual(audio.chimes[-1], current.quantity)
        # The fireflies stay lit; the tried card is greyed, the others work.
        self.assertIsNone(app.motion.hide_at)
        rejected = app.controls.choices[app.controls.index_of(wrong)]
        self.assertTrue(rejected.visible)
        self.assertFalse(rejected.enabled)
        self.assertFalse(self._tap_value(app, wrong))
        app.render()
        self.assertTrue(self._tap_value(app, current.quantity))
        self.assertEqual(app.cast.pose.value, "cheer")

    def test_look_again_replays_once_and_counts_as_a_hint(self) -> None:
        app, now, _, _, _ = self._build_app(level=2)
        self._wait_for_cards(app, now)
        replay = app.controls.replay
        self.assertTrue(replay.visible and replay.enabled)
        self.assertTrue(app.tap(self._physical(app, replay.rect)))
        self.assertTrue(app.session.replay_used)
        self.assertFalse(app.asking)
        self._wait_for_cards(app, now)
        self.assertTrue(replay.visible)
        self.assertFalse(replay.enabled)
        current = app.session.current_round
        assert current is not None
        self._tap_value(app, current.quantity)
        self.assertFalse(app.session.history[-1].first_attempt_success)

    def test_idle_hint_points_then_repeats_the_question(self) -> None:
        app, now, _, audio, _ = self._build_app(level=1)
        self._wait_for_cards(app, now)
        spoken = audio.speech.count("prompt_choose")
        self._advance(app, now, 6.2)
        self.assertTrue(app.cast.pointing)
        self.assertIsNotNone(app.motion.replay_pulse)
        self.assertEqual(audio.speech.count("prompt_choose"), spoken)
        self._advance(app, now, 6.2)
        self.assertEqual(audio.speech.count("prompt_choose"), spoken + 1)
        current = app.session.current_round
        assert current is not None
        self._tap_value(app, current.quantity)
        self.assertEqual(app.session.history[-1].hints_used, 1)

    def test_full_visit_plays_to_the_completion_scene_and_restarts(self) -> None:
        app, now, events, audio, storage = self._build_app(level=1)
        for round_number in range(ROUND_COUNT):
            self._wait_for_cards(app, now)
            self.assertEqual(app.controls.progress.current, round_number)
            current = app.session.current_round
            assert current is not None
            self.assertTrue(self._tap_value(app, current.quantity))
            self.assertEqual(app.cast.pose.value, "cheer")
            self.assertIn(f"count_{current.quantity}", audio.speech)
            app.render()
            self._advance(app, now, 2.8)
            self.assertEqual(app.motion.jar_lights, round_number + 1)
        self._advance(app, now, 3.0)
        from firefly_app import AppState

        self.assertIs(app.state, AppState.TERMINAL)
        self.assertEqual(len(events.emitted), 1)
        session_id, payload = events.emitted[0]
        self.assertEqual(session_id, "test-session-1")
        self.assertEqual(payload, {"level": 1, "first_attempt_count": ROUND_COUNT, "replays": 0})
        self.assertIn("garden_complete", audio.speech)
        self.assertEqual(storage.saved["schema_version"], 1)
        app.render()

        primary = app.completion.primary_rect
        self.assertTrue(app.tap(self._physical(app, primary)))
        self.assertIs(app.state, AppState.PLAYING)
        self.assertEqual(app.session.round_index, 0)
        self.assertEqual(app.motion.jar_lights, 0)
        self.assertEqual(len(events.emitted), 1)

    def test_keyboard_and_controller_navigation_answer_without_a_pointer(self) -> None:
        app, now, _, _, _ = self._build_app(level=1)
        self._wait_for_cards(app, now)
        current = app.session.current_round
        assert current is not None
        target = app.controls.index_of(current.quantity)
        assert target is not None
        app.press(pygame.K_LEFT)
        app.press(pygame.K_LEFT)
        app.press(pygame.K_LEFT)
        for _ in range(target):
            app.press(pygame.K_RIGHT)
        self.assertEqual(app.controls.layer.focused_id, f"choice.{target}")
        self.assertTrue(app.controls.layer.focus_visible)
        app.render()
        self.assertTrue(app.press(pygame.K_SPACE))
        self.assertEqual(app.session.round_index, 1)

    def test_layout_stays_clear_of_protected_chrome_at_small_sizes(self) -> None:
        from greia_platform.activity_controls import ControlLayout

        for size in ((1024, 600), (800, 480), (480, 320)):
            app, now, _, _, _ = self._build_app(level=4, size=size)
            layout = ControlLayout.for_canvas(app.canvas, size)
            self._wait_for_cards(app, now)
            for control in (*app.controls.choices, app.controls.replay, app.controls.listen, app.controls.progress):
                self.assertFalse(layout.overlaps_chrome(control.rect), (size, control.control_id))
            app.render()

    def test_frames_are_blits_only_after_warm_up(self) -> None:
        app, now, _, _, _ = self._build_app(level=4)
        self._advance(app, now, 4.3)
        app.render()
        self._wait_for_cards(app, now)
        app.render()
        built = app.kit.painter.build_count
        surfaces_before = len(app.art.fireflies)
        for _ in range(30):
            now[0] += 1 / 30
            app.step()
            app.render()
        self.assertEqual(app.kit.painter.build_count, built)
        self.assertEqual(len(app.art.fireflies), surfaces_before)


class SimulatorSupervisorTests(unittest.TestCase):
    def test_simulator_supervises_luci_di_momo(self) -> None:
        from simulator_supervision import supervise_builtin_activity

        supervise_builtin_activity(self, "org.greia.luci-di-momo")


class AudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    def test_audio_loads_approved_clips_and_fails_soft(self) -> None:
        from firefly_audio import FireflyAudio
        from greia_platform.localization import activity_resources

        resources = activity_resources(ACTIVITY_ROOT, requested_locale="en")
        audio = FireflyAudio(ACTIVITY_ROOT, locale="en", resources=resources, rng=random.Random(1))
        for cue in ("reveal", "correct", "retry", "complete", "light"):
            audio.play(cue)
        for number in range(1, 12):
            audio.chime(number)
        audio.play_welcome()
        audio.play_prompt_choose()
        self.assertFalse(audio.play_count(7))
        audio.praise()
        audio.encourage()
        audio.play_feedback(True)
        audio.play_feedback(False)
        audio.play_garden_complete()
        audio.stop_speech()
        if pygame.mixer.get_init():
            self.assertGreater(audio.speech_seconds("welcome"), 1.0)
            self.assertTrue(audio.play_count(3))
        self.assertEqual(audio.speech_seconds("no_such_cue"), 0.0)


if __name__ == "__main__":
    unittest.main()
