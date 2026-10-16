"""Badge celebration timing, trophy-shelf library and keyboard route.

The timeline tests are pure. The presentation tests drive a real
``GreiaChildShell`` headlessly with a fake achievement service and a fake
clock, calling the Shell loop's incremental frame hook exactly as the loop
does, so pacing (zero frames while waiting/idle), the single voice clip per
queue, the held-back star count and the keyboard route are all observed on
the production presentation code.
"""

from __future__ import annotations

import os
import re
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[1]
TMP_DIR = tempfile.mkdtemp()
os.environ["GREIA_PROFILES_DIR"] = os.path.join(TMP_DIR, "profiles")
os.environ["GREIA_SYSTEM_SETTINGS_DIR"] = os.path.join(TMP_DIR, "settings")
os.environ["GREIA_MEDIA_ROOT"] = os.path.join(TMP_DIR, "media")
os.environ["GREIA_ACTIVE_PROFILE_STATUS"] = os.path.join(TMP_DIR, "active-profile.json")
os.environ["GREIA_HARDWARE_STATUS"] = os.path.join(TMP_DIR, "hardware-status.json")
os.environ["GREIA_MAIN_CREDENTIAL_PATH"] = os.path.join(TMP_DIR, "parent-credential.json")
os.environ["GREIA_OS_ROOT"] = str(REPO_ROOT)
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from greia_launcher.achievement_celebration import (
    FLIGHT_BADGE_SIZES,
    FRAME_FPS,
    INTRO_BADGE_SIZES,
    MAX_ANIMATED_SECONDS,
    CelebrationPhase,
    CelebrationTimeline,
    LibraryHop,
)
from greia_launcher import achievement_presentation as presentation
from greia_platform.achievements import (
    AchievementCriterion,
    AchievementDefinition,
    AchievementEntry,
    AchievementSnapshot,
    LocalizedAchievementText,
)

import hermetic_volume


def setUpModule() -> None:
    hermetic_volume.install_for_module()


class CelebrationTimelineTests(unittest.TestCase):
    def test_animated_stretches_stay_within_budget_and_frame_rate(self) -> None:
        for first in (True, False):
            with self.subTest(first=first):
                timeline = CelebrationTimeline(first=first)
                self.assertLessEqual(timeline.intro_seconds, MAX_ANIMATED_SECONDS)
                self.assertLessEqual(timeline.flight_seconds, MAX_ANIMATED_SECONDS)
                for frames in (timeline.intro_keyframes, timeline.flight_keyframes):
                    times = [time for time, _frame in frames]
                    for earlier, later in zip(times, times[1:]):
                        self.assertGreaterEqual(later - earlier, 1.0 / FRAME_FPS - 0.005)

    def test_badge_sizes_are_a_small_fixed_set(self) -> None:
        sizes: set[int] = set()
        for first in (True, False):
            timeline = CelebrationTimeline(first=first, sparkle_frames=3)
            for _time, frame in (*timeline.intro_keyframes, *timeline.flight_keyframes):
                if frame.badge_size is not None:
                    sizes.add(frame.badge_size)
        self.assertLessEqual(sizes, set(INTRO_BADGE_SIZES) | set(FLIGHT_BADGE_SIZES))
        self.assertLessEqual(len(sizes), 9)

    def test_waiting_is_static_and_flight_lands_with_a_bounce(self) -> None:
        timeline = CelebrationTimeline(first=True)
        self.assertIsNone(timeline.next_intro_change(timeline.intro_seconds + 0.01))
        self.assertEqual(timeline.intro_frame(5.0), timeline.resting_frame)
        landed = [frame for _t, frame in timeline.flight_keyframes if frame.landed]
        self.assertTrue(landed)
        self.assertEqual(max(frame.star_scale for frame in landed), 1.25)
        self.assertEqual(timeline.flight_frame(5.0).star_scale, 1.0)
        later = CelebrationTimeline(first=False)
        self.assertLess(later.intro_seconds, timeline.intro_seconds)

    def test_library_hop_curve(self) -> None:
        hop = LibraryHop(index=2, started=10.0)
        self.assertEqual(hop.offset(10.0), 0)
        self.assertEqual(hop.offset(10.2), -18)
        self.assertEqual(hop.offset(10.4), -28)
        self.assertEqual(hop.offset(10.6), -12)
        self.assertEqual(hop.offset(10.8), 0)
        self.assertTrue(hop.finished(10.8))
        self.assertIsNone(hop.next_change(11.0))


def _text(value: str) -> LocalizedAchievementText:
    return LocalizedAchievementText((("en", value),), "en")


def _definition(index: int, *, tier: str = "bronze", secret: bool = False) -> AchievementDefinition:
    return AchievementDefinition(
        achievement_id=f"greia.test.badge-{index:02d}",
        category="test",
        tier=tier,
        icon_id="yellow_star",
        secret=secret,
        title=_text(f"Badge {index}"),
        description=_text("You did a lovely thing."),
        locked_hint=_text("Try something lovely."),
        criteria=(AchievementCriterion(kind="reward_balance", threshold=1, reward_id="star"),),
    )


class _FakeAchievements:
    def __init__(self, definitions: tuple[AchievementDefinition, ...]) -> None:
        self.definitions = definitions
        self.unlocked: set[str] = set()
        self.announced: list[str] = []
        self.seen: list[str] = []

    def refresh(self, _profile) -> AchievementSnapshot:
        return AchievementSnapshot(
            tuple(
                AchievementEntry(
                    item,
                    10.0 if item.achievement_id in self.unlocked else None,
                    10.0 if item.achievement_id in self.announced else None,
                    None,
                )
                for item in self.definitions
            )
        )

    def mark_announced(self, _profile, achievement_id: str) -> None:
        self.announced.append(achievement_id)

    def mark_seen(self, _profile, ids) -> None:
        self.seen.extend(ids)


class AchievementPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.font.init()
        cls.screen = pygame.display.set_mode((1024, 600))

    def setUp(self) -> None:
        from greia_launcher.child_shell import GreiaChildShell

        self.shell = GreiaChildShell(windowed=True)
        self.shell.profiles = self.shell.profile_store.ensure_initialized()
        self.shell._activate_profile(self.shell.profiles[0], pygame)
        definitions = tuple(
            _definition(index, tier="gold" if index == 3 else "bronze", secret=index == 3)
            for index in range(11)
        )
        self.fake = _FakeAchievements(definitions)
        self.fake.unlocked = {definitions[0].achievement_id, definitions[1].achievement_id}
        self.shell.runtime_services = replace(
            self.shell.runtime_services, achievement_service=self.fake
        )
        self.now = [100.0]
        self.shell._achievement_clock = lambda: self.now[0]
        self.voice: list[str] = []
        self.shell._play_greeter_cue = lambda cue, _pygame: self.voice.append(cue) or True
        # These tests call the loop's frame hook themselves with a fake clock.
        self.shell._achievement_loop_drives_frames = lambda: True
        self.shell._refresh_achievements()

    # ------------------------------------------------------------ helpers
    def _frame(self, seconds: float = 1.0 / 24) -> bool:
        self.now[0] = round(self.now[0] + seconds, 6)
        return self.shell._present_ambient_frame(self.screen, pygame, self.now[0])

    def _run(self, seconds: float) -> int:
        presented = 0
        end = self.now[0] + seconds
        while self.now[0] < end - 1e-9:
            presented += int(self._frame())
        return presented

    def _unlock_and_queue(self, *indices: int) -> list[AchievementEntry]:
        for index in indices:
            self.fake.unlocked.add(self.fake.definitions[index].achievement_id)
        snapshot = self.shell._refresh_achievements()
        wanted = {self.fake.definitions[index].achievement_id for index in indices}
        entries = [e for e in snapshot.entries if e.definition.achievement_id in wanted]
        self.shell._queue_achievement_announcements(entries, pygame)
        self.shell._draw(self.screen, pygame)
        return entries

    # -------------------------------------------------------------- tests
    def test_frames_are_driven_by_the_loop_hook_not_a_blocking_sleep(self) -> None:
        from greia_launcher.presentation import GreiaLauncherPresentation

        if "_present_ambient_frame" not in vars(GreiaLauncherPresentation):
            self.skipTest("Shell loop incremental-frame hook not present in this checkout")
        self.assertTrue(type(self.shell)._achievement_loop_drives_frames(self.shell))

    def test_celebration_animates_then_presents_zero_frames_while_waiting(self) -> None:
        self._unlock_and_queue(4)
        self.assertGreater(self._run(0.7), 3)
        celebration = self.shell._achievement_celebration
        self.assertIs(celebration.phase, CelebrationPhase.WAITING)
        self.assertEqual(self._run(3.0), 0)
        self.assertIsNone(self.shell._achievement_wait_seconds(self.now[0]))

    def test_voice_once_per_queue_and_count_increments_on_landing(self) -> None:
        self._unlock_and_queue(4, 5)
        snapshot = self.shell._achievement_snapshot
        self.assertEqual(snapshot.unlocked_count, 4)
        self.assertEqual(self.shell._achievement_display_count(snapshot), 2)
        self._run(0.7)
        self.shell._dismiss_achievement_celebration(pygame)
        self._run(0.2)
        self.assertEqual(self.shell._achievement_display_count(snapshot), 2)
        self._run(0.6)
        # First badge landed: second badge's short intro is now running.
        self.assertEqual(self.shell._achievement_display_count(snapshot), 3)
        self.assertEqual(
            self.shell._achievement_celebration.entry.definition.achievement_id,
            self.fake.definitions[5].achievement_id,
        )
        self._run(0.5)
        self.shell._handle_key(pygame.K_RETURN, pygame)
        self._run(1.0)
        self.assertIsNone(self.shell._achievement_celebration)
        self.assertEqual(self.voice, [presentation.CUE_CELEBRATE])
        self.assertEqual(
            self.fake.announced,
            [self.fake.definitions[4].achievement_id, self.fake.definitions[5].achievement_id],
        )
        self.assertEqual(self._run(2.0), 0)

    def test_taps_during_flight_are_ignored(self) -> None:
        self._unlock_and_queue(4)
        self._run(0.3)
        self.shell._handle_click((512, 300), pygame)
        self.assertIs(self.shell._achievement_celebration.phase, CelebrationPhase.FLIGHT)
        self.shell._handle_click((512, 300), pygame)
        self.assertEqual(self.fake.announced, [self.fake.definitions[4].achievement_id])

    def test_profile_activation_does_not_replay_unlocked_badges(self) -> None:
        self.fake.unlocked.add(self.fake.definitions[6].achievement_id)
        self.shell._activate_profile(self.shell.profiles[0], pygame)
        self.assertIsNone(self.shell._achievement_celebration)
        self.assertEqual(self.voice, [])

    def test_keyboard_route_reaches_the_star_and_opens_the_library(self) -> None:
        shell = self.shell
        shell._draw(self.screen, pygame)
        shell._home_collection_selected = 0
        shell._handle_key(pygame.K_UP, pygame)
        self.assertTrue(shell._achievement_star_focused)
        self.assertEqual(shell._home_collection_selected, -1)
        shell._handle_key(pygame.K_RETURN, pygame)
        self.assertEqual(shell._mode, "achievements")
        shell._handle_key(pygame.K_ESCAPE, pygame)
        self.assertEqual(shell._mode, "activities")
        self.assertTrue(shell._achievement_star_focused)
        shell._handle_key(pygame.K_TAB, pygame)
        self.assertFalse(shell._achievement_star_focused)
        # Cycle continues to the greeter when the Home animator offers it,
        # otherwise straight back to the first portal.
        if getattr(shell, "_home_greeter_focused", False):
            shell._handle_key(pygame.K_TAB, pygame)
        self.assertEqual(shell._home_collection_selected, 0)
        # Tab from the last portal also reaches the star.
        shell._home_collection_selected = len(shell._home_collections()) - 1
        shell._handle_key(pygame.K_TAB, pygame)
        self.assertTrue(shell._achievement_star_focused)
        shell._handle_key(pygame.K_ESCAPE, pygame)
        self.assertFalse(shell._achievement_star_focused)
        self.assertEqual(shell._mode, "activities")

    def test_library_is_a_shelf_without_denominator_and_idles_at_zero_frames(self) -> None:
        shell = self.shell
        rendered: list[str] = []
        original_font = shell._typography.font

        def recording_font(role, size):
            font = original_font(role, size)

            class _Recorder:
                def render(self, text, *args):
                    rendered.append(str(text))
                    return font.render(text, *args)

                def size(self, text):
                    return font.size(text)

                def __getattr__(self, name):
                    return getattr(font, name)

            return _Recorder()

        shell._typography = SimpleNamespace(font=recording_font)
        shell._open_achievement_library()
        shell._draw(self.screen, pygame)
        entries = [t for t in shell._targets if t.action == "achievement_entry"]
        self.assertEqual(len(entries), 8)  # 10 visible (one secret hidden) -> 2 pages
        self.assertTrue(any(t.action == "achievement_page_next" for t in shell._targets))
        self.assertFalse(any(t.action == "achievement_page_prev" for t in shell._targets))
        self.assertIn("2", rendered)
        self.assertFalse(any(re.search(r"\d+\s*/\s*\d+", text) for text in rendered))
        self.assertEqual(self._run(2.0), 0)
        self.assertIsNone(shell._achievement_wait_seconds(self.now[0]))

    def test_tapping_a_badge_hops_and_speaks_with_cooldown(self) -> None:
        shell = self.shell
        shell._open_achievement_library()
        shell._draw(self.screen, pygame)
        locked = next(t for t in shell._targets if t.action == "achievement_entry" and t.value == 2)
        shell._handle_click(locked.rect.center, pygame)
        shell._draw(self.screen, pygame)
        self.assertGreater(self._run(0.9), 5)
        self.assertIsNone(shell._achievement_hop)
        unlocked = next(t for t in shell._targets if t.value == 0 and t.action == "achievement_entry")
        shell._handle_click(unlocked.rect.center, pygame)
        self.assertEqual(self.voice, [presentation.CUE_ENCOURAGE])
        self.now[0] += 3.1
        shell._handle_click(unlocked.rect.center, pygame)
        self.assertEqual(self.voice, [presentation.CUE_ENCOURAGE, presentation.CUE_PRAISE])
        self._run(1.0)
        self.assertEqual(self._run(1.0), 0)

    def test_badge_renderer_cache_is_bounded(self) -> None:
        self.assertLessEqual(self.shell._achievement_badges.max_entries, 64)
        self._unlock_and_queue(4)
        self._run(0.7)
        self.assertLessEqual(len(self.shell._achievement_badges), 64)


if __name__ == "__main__":
    unittest.main()
