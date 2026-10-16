"""Animal Band (orchestra_animali): echo rules, ladder, saves and the app loop.

Source/headless contracts only (dummy SDL video/audio); no hardware claim.
"""
from __future__ import annotations

import os
import random
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import pygame

from greia_platform.activity_feedback import CastPose
from greia_platform.localization import activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

from activities.orchestra_animali.orchestra_app import OrchestraApp, Phase
from activities.orchestra_animali.orchestra_audio import BandAudio
from activities.orchestra_animali.orchestra_content import BAND, SESSION_ECHOES, STORAGE_KEY, Dynamics, Tempo
from activities.orchestra_animali.orchestra_layout import BAR_RECTS, MUSICIAN_HIT
from activities.orchestra_animali.orchestra_model import (
    Beat,
    ConcertProgress,
    ConcertSession,
    EchoPattern,
    EchoVerdict,
    PatternFactory,
    XYLOPHONE_VOICE,
    judge_echo,
    rhythm_flags,
)
from activities.orchestra_animali.orchestra_playalong import PlayAlong
from activities.orchestra_animali.orchestra_services import GreiaOrchestraProgress


def _pattern(*beats: tuple[int, float], level: int = 1) -> EchoPattern:
    return EchoPattern(tuple(Beat(v, at) for v, at in beats), level)


class EchoRuleTests(unittest.TestCase):
    def test_even_pattern_needs_same_players_in_order_at_any_tempo(self) -> None:
        pattern = _pattern((0, 0.0), (0, 1.0), (0, 2.0))
        self.assertEqual(judge_echo(pattern, [(0, 1.0), (0, 1.3), (0, 2.4)]), EchoVerdict.MATCH)
        self.assertEqual(judge_echo(pattern, [(0, 1.0), (0, 1.3)]), EchoVerdict.TOO_FEW)
        self.assertEqual(judge_echo(pattern, [(0, 1.0), (1, 1.3), (0, 1.6)]), EchoVerdict.WRONG_PLAYER)
        self.assertEqual(
            judge_echo(pattern, [(0, 1.0), (XYLOPHONE_VOICE, 1.3), (0, 1.6)]), EchoVerdict.WRONG_PLAYER
        )

    def test_long_short_rhythm_is_judged_relative_to_the_childs_tempo(self) -> None:
        pattern = _pattern((2, 0.0), (2, 1.0), (2, 1.5), level=4)  # taa ti
        self.assertEqual(pattern.long_flags(), (True, False))
        self.assertEqual(judge_echo(pattern, [(2, 0.0), (2, 0.8), (2, 1.2)]), EchoVerdict.MATCH)
        self.assertEqual(judge_echo(pattern, [(2, 0.0), (2, 1.6), (2, 2.4)]), EchoVerdict.MATCH)
        self.assertEqual(judge_echo(pattern, [(2, 0.0), (2, 0.5), (2, 1.0)]), EchoVerdict.WRONG_RHYTHM)
        self.assertEqual(judge_echo(pattern, [(2, 0.0), (2, 0.4), (2, 1.2)]), EchoVerdict.WRONG_RHYTHM)

    def test_even_rhythm_flags_and_double_tap_jitter(self) -> None:
        self.assertIsNone(rhythm_flags([0.0, 0.5, 1.0]))
        self.assertIsNone(rhythm_flags([0.0, 0.01, 0.05]))

    def test_ladder_grows_from_two_beats_to_two_players_with_rhythm(self) -> None:
        factory = PatternFactory(random.Random(1))
        self.assertEqual(factory.build(1, 3).length, 2)
        self.assertEqual(factory.build(2, 3).voices, (3,))
        self.assertEqual(factory.build(2, 3).length, 3)
        self.assertEqual(set(factory.build(3, 3, 4).voices), {3, 4})
        self.assertIsNone(factory.build(3, 3, 4).long_flags())
        self.assertIsNotNone(factory.build(4, 3).long_flags())
        five = factory.build(5, 3, 2)
        self.assertEqual(set(five.voices), {2, 3})
        self.assertIsNotNone(five.long_flags())

    def test_session_is_finite_and_adapts_cheaply(self) -> None:
        session = ConcertSession(PatternFactory(random.Random(2)), level=1, rng=random.Random(2))
        leads = []
        for _ in range(2):
            invitation = session.invite()
            leads.append(invitation.lead)
            taps = [(b.voice, b.at) for b in invitation.pattern.beats]
            self.assertIs(session.answer(taps), EchoVerdict.MATCH)
            session.close()
        self.assertNotEqual(leads[0], leads[1])
        self.assertEqual(session.level, 2)
        invitation = session.invite()
        for _ in range(2):
            self.assertIsNot(session.answer([]), EchoVerdict.MATCH)
        session.answer([(b.voice, b.at) for b in invitation.pattern.beats])
        session.close()
        self.assertEqual(session.level, 1)
        while not session.finished:
            invitation = session.invite()
            session.answer([(b.voice, b.at) for b in invitation.pattern.beats])
            session.close()
        self.assertEqual(session.completed, SESSION_ECHOES)
        with self.assertRaises(RuntimeError):
            session.invite()


class MemoryStorage:
    def __init__(self, kv=None):
        self.kv = dict(kv or {})

    def kv_get(self, key, default=None):
        return self.kv.get(key, default)

    def kv_set(self, key, value):
        self.kv[key] = value


class ProgressMigrationTests(unittest.TestCase):
    def test_legacy_star_counter_survives_and_is_written_forward(self) -> None:
        storage = MemoryStorage({STORAGE_KEY: {"stars": 42}})
        store = GreiaOrchestraProgress(storage)
        loaded = store.load()
        self.assertEqual(loaded, ConcertProgress(level=1, stars=42, concerts=0))
        store.save(ConcertProgress(level=3, stars=43, concerts=1))
        self.assertEqual(
            storage.kv[STORAGE_KEY],
            {"schema_version": 2, "level": 3, "stars": 43, "concerts": 1},
        )
        self.assertEqual(store.load().level, 3)

    def test_garbage_is_bounded(self) -> None:
        self.assertEqual(ConcertProgress.from_raw({"level": 99, "stars": -4, "concerts": True}).level, 5)
        self.assertEqual(ConcertProgress.from_raw("nope"), ConcertProgress())


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


class FakeProgress:
    def __init__(self) -> None:
        self.value = ConcertProgress(level=1, stars=7)
        self.saves = []

    def load(self):
        return self.value

    def save(self, progress):
        self.saves.append(progress)
        self.value = progress


class FakeEvents:
    def __init__(self) -> None:
        self.calls = []

    def instrument_played(self, session_id, instrument):
        self.calls.append(("instrument.played", instrument))

    def echo_matched(self, session_id, index, level):
        self.calls.append(("rhythm.echoed", index))

    def concert_completed(self, session_id, payload):
        self.calls.append(("band.concert_completed", payload))

    def concert_performed(self, key, live_inputs):
        self.calls.append(("concert.performed", live_inputs))


class OrchestraAppLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((1024, 600))
        self.clock = FakeClock()
        self.progress = FakeProgress()
        self.events = FakeEvents()
        resources = activity_resources(ROOT / "activities" / "orchestra_animali", requested_locale="en")
        self.app = OrchestraApp(
            screen=self.screen,
            canvas=PygameReferenceCanvas(self.screen),
            typography=GreiaTypography(),
            resources=resources,
            audio=BandAudio(locale="en"),
            progress=self.progress,
            events=self.events,
            playalong=PlayAlong(creations=None, store=None),
            rng=random.Random(5),
            session_id="test-000001",
            clock=self.clock,
        )

    def tearDown(self) -> None:
        pygame.quit()

    def advance(self, seconds: float, step: float = 0.05) -> None:
        for _ in range(max(1, int(round(seconds / step)))):
            self.clock.now += step
            self.app.step()

    def wait_for(self, phase: Phase, limit: float = 40.0) -> None:
        waited = 0.0
        while self.app.phase is not phase:
            self.advance(0.05)
            waited += 0.05
            self.assertLess(waited, limit, f"never reached {phase}")

    def echo_correctly(self) -> None:
        pattern = self.app.session.current.pattern
        for index, beat in enumerate(pattern.beats):
            if index:
                self.advance((beat.at - pattern.beats[index - 1].at) * self.app.tempo.beat_seconds)
            self.assertTrue(self.app.press(pygame.K_1 + beat.voice))

    def test_free_play_sounds_on_touch_and_keys_without_text(self) -> None:
        self.wait_for(Phase.FREE)
        drum = MUSICIAN_HIT[0].center
        self.assertTrue(self.app.tap(drum))
        self.assertTrue(self.app.press(pygame.K_6))
        self.assertTrue(self.app.press(pygame.K_a))
        self.assertGreater(self.app.motion.bars_lit[0], 0)
        played = [name for kind, name in self.events.calls if kind == "instrument.played"]
        self.assertEqual(played, ["drum", "keyboard"])
        self.app.press(pygame.K_1)
        self.assertEqual(len([c for c in self.events.calls if c[0] == "instrument.played"]), 2)
        self.app.render()
        self.app.canvas.present()

    def test_arrow_focus_and_space_play_the_band(self) -> None:
        self.wait_for(Phase.FREE)
        self.app.controls.layer.focus("musician.2")
        before = self.app.motion.strikes[3]
        self.app.press(pygame.K_RIGHT)
        self.app.press(pygame.K_SPACE)
        self.assertGreater(self.app.motion.strikes[3], before)

    def test_protected_chrome_never_plays(self) -> None:
        self.wait_for(Phase.FREE)
        self.assertFalse(self.app.tap((8, 8)))

    def test_loud_soft_and_fast_slow_are_band_properties(self) -> None:
        self.wait_for(Phase.FREE)
        soft = self.app.controls.volume.controls[0]
        self.assertTrue(self.app.tap(soft.rect.center))
        self.assertIs(self.app.dynamics, Dynamics.SOFT)
        self.assertIs(self.app.audio.dynamics, Dynamics.SOFT)
        fast = self.app.controls.tempo.controls[1]
        self.assertTrue(self.app.tap(fast.rect.center))
        self.assertIs(self.app.tempo, Tempo.FAST)

    def test_listen_locks_the_stage_and_wrong_echo_demonstrates_again(self) -> None:
        self.wait_for(Phase.LISTEN)
        self.assertFalse(self.app.press(pygame.K_1))
        self.wait_for(Phase.ECHO)
        invitation = self.app.session.current
        wrong = (invitation.pattern.beats[0].voice + 1) % len(BAND)
        self.app.press(pygame.K_1 + wrong)
        self.advance(2.6)
        self.assertIs(self.app.feedback[invitation.lead].pose, CastPose.THINK)
        self.assertEqual(self.app.motion.bubble.mode, "listen")
        self.wait_for(Phase.ECHO)
        self.assertIs(self.app.session.current, invitation)
        self.assertEqual(invitation.attempts, 1)

    def test_idle_echo_gets_graduated_hints(self) -> None:
        self.wait_for(Phase.ECHO)
        lead = self.app.session.current.lead
        self.advance(6.2)
        self.assertEqual(self.app.motion.borrowed[lead][0], "pose_point")
        self.assertTrue(self.app.motion.rings)
        # IdleHintScheduler backs off: the second hint comes a further 12 s later.
        self.advance(12.2)
        self.assertIs(self.app.phase, Phase.LISTEN)
        self.assertGreaterEqual(self.app.session.current.hints, 2)

    def test_hint_replays_do_not_restart_the_back_off_forever(self) -> None:
        self.wait_for(Phase.ECHO)
        self.advance(6.2 + 12.2 + 6.0)  # point, then the replay of the call
        self.wait_for(Phase.ECHO)
        hints = self.app.session.current.hints
        self.assertEqual(hints, 2)
        self.advance(24.5 + 6.0)  # third and last hint, its replay finished
        self.wait_for(Phase.ECHO)
        self.assertEqual(self.app.session.current.hints, 3)
        self.advance(120.0)  # an absent child: no further hints or replays
        self.assertIs(self.app.phase, Phase.ECHO)
        self.assertEqual(self.app.session.current.hints, 3)

    def test_a_concert_plays_to_the_shared_completion_scene(self) -> None:
        for round_index in range(SESSION_ECHOES):
            self.wait_for(Phase.ECHO)
            self.echo_correctly()
            self.advance(0.5)
            self.assertIs(self.app.phase, Phase.CHEER)
            self.assertIs(self.app.feedback[self.app.session.current.lead].pose, CastPose.CHEER)
            self.assertEqual(self.app.controls.progress.current, round_index + 1)
        self.wait_for(Phase.COMPLETE)
        self.app.render()
        self.app.canvas.present()
        echoed = [c for c in self.events.calls if c[0] == "rhythm.echoed"]
        self.assertEqual(len(echoed), SESSION_ECHOES)
        self.assertEqual(self.events.calls[-1][0], "band.concert_completed")
        saved = self.progress.saves[-1]
        self.assertEqual(saved.stars, 7 + SESSION_ECHOES)
        self.assertEqual(saved.concerts, 1)
        self.assertGreater(saved.level, 1)
        # Replay (primary) starts a new concert at the adapted stage.
        self.app.press(pygame.K_RETURN)
        self.assertIs(self.app.phase, Phase.INTRO)
        self.assertEqual(self.app.session.level, saved.level)
        self.assertEqual(self.app.session.completed, 0)

    def test_backing_track_postpones_invitations(self) -> None:
        self.wait_for(Phase.FREE)

        class Playing:
            track = object()
            state = "playing"

            def refresh(self):
                return False

            def stop(self):
                pass

        self.app.playalong.player = Playing()
        self.advance(20.0)
        self.assertIs(self.app.phase, Phase.FREE)


if __name__ == "__main__":
    unittest.main()
