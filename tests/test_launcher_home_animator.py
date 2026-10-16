"""Interactive Home (HomeAnimator) contract: bounded, cheap, input-safe.

Renderer-level unit tests use a fake sprite loader; the Shell-level tests drive
one real ``GreiaChildShell`` Home through the production ambient-frame hook
(``_present_ambient_frame``) with a controlled clock.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

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

import greia_launcher.home_animation_presentation as home_presentation
from greia_launcher.catalogue_view import ALL_ACTIVITIES_ID
from greia_launcher.home_animator import (
    AWAKE_SECONDS,
    MAX_APPLES,
    MAX_EFFECTS,
    SLEEP_AFTER_SECONDS,
    HomeAnimator,
    HomeGreeterVoice,
    VoiceRateLimiter,
)
from greia_launcher.home_scenery import HomeSceneryLayout
from greia_platform.responsive_layout import UiRect

import hermetic_volume


def setUpModule() -> None:
    hermetic_volume.install_for_module()


SCREEN = (1024, 600)
GREETER = UiRect(8, 407, 189, 189)


class _Clock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def monotonic(self) -> float:
        return self.now


def _animator() -> tuple[HomeAnimator, list[tuple[str, str, tuple[int, int]]]]:
    loads: list[tuple[str, str, tuple[int, int]]] = []

    def load(asset_id: str, variant: str, size: tuple[int, int]) -> pygame.Surface:
        loads.append((asset_id, variant, size))
        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.fill((200, 100, 50, 255))
        return surface

    return HomeAnimator(load), loads


def _scenery() -> HomeSceneryLayout:
    return HomeSceneryLayout.compute(SCREEN, (GREETER,))


class HomeAnimatorLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    def _ready(self, now: float = 0.0) -> HomeAnimator:
        animator, _ = _animator()
        animator.place_greeter(GREETER, "leo", now)
        animator.layout_scenery(_scenery())
        animator.note_input(now)
        animator.update(now)
        return animator

    def test_effects_are_bounded(self) -> None:
        animator = self._ready()
        scenery = _scenery()
        tree = scenery.tree_hit
        self.assertIsNotNone(tree)
        for i in range(12):
            animator.tap("tree", 0.01 * i)
            animator.tap("sun", 0.01 * i)
            animator.tap("greeter", 0.01 * i)
            animator.update(0.01 * i)
            self.assertLessEqual(animator.effect_count, MAX_EFFECTS)
        apples = [e for e in animator._effects if type(e).__name__ == "FallingApple"]
        self.assertLessEqual(len(apples), MAX_APPLES)

    def test_everything_stops_after_awake_window_then_one_sleepy_swap(self) -> None:
        animator = self._ready()
        animator.tap("tree", 0.0)
        animator.tap("sun", 0.0)
        animator.tap("greeter", 0.0)
        t = 0.0
        while t < AWAKE_SECONDS + 1:
            animator.update(t)
            t += 1 / 24
        self.assertEqual(animator._effects, [])
        # Between the awake window and sleep, the only scheduled change is
        # the sleepy pose swap itself.
        self.assertAlmostEqual(animator.next_change(t), SLEEP_AFTER_SECONDS, places=3)
        animator.update(SLEEP_AFTER_SECONDS + 0.01)
        self.assertIs(animator._items[-1][0], animator._greeter.sprites["sleepy"])
        self.assertIsNone(animator.seconds_until_due(SLEEP_AFTER_SECONDS + 1))
        self.assertIsNone(animator.seconds_until_due(SLEEP_AFTER_SECONDS + 600))

    def test_input_wakes_the_sleeping_greeter(self) -> None:
        animator = self._ready()
        animator.update(SLEEP_AFTER_SECONDS + 1)
        animator.update(SLEEP_AFTER_SECONDS + 2, last_input=SLEEP_AFTER_SECONDS + 2)
        self.assertIs(animator._items[-1][0], animator._greeter.sprites["surprised"])

    def test_sprites_load_once_per_layout(self) -> None:
        animator, loads = _animator()
        animator.place_greeter(GREETER, "leo", 0.0)
        animator.layout_scenery(_scenery())
        count = len(loads)
        # Re-placing on every cache rebuild must not reload or restart.
        animator.place_greeter(GREETER, "leo", 5.0)
        animator.layout_scenery(_scenery())
        self.assertEqual(len(loads), count)
        for i in range(200):
            animator.tap("tree", i * 0.05)
            animator.update(i * 0.05)
        self.assertEqual(len(loads), count)

    def test_react_is_a_public_bounded_seam(self) -> None:
        animator = self._ready()
        self.assertTrue(animator.react("cheer", 1.0))
        self.assertFalse(animator.react("explode", 1.0))
        animator.clear_greeter()
        self.assertFalse(animator.react("happy", 1.0))


class HomeGreeterVoiceTests(unittest.TestCase):
    def test_twenty_taps_play_at_most_four_clips(self) -> None:
        player = mock.Mock()
        player.is_busy.return_value = False
        player.play_if_idle.return_value = True
        voice = HomeGreeterVoice(REPO_ROOT, player, lambda: "it")
        played = sum(voice.speak("leo", 0.5 * i, None) for i in range(20))
        self.assertLessEqual(played, 4)
        self.assertEqual(player.play_if_idle.call_count, played)
        first = player.play_if_idle.call_args_list[0].args[0]
        self.assertEqual(first.name, "leo.ogg")  # accepted self-introduction
        self.assertIn("_intros", first.parts)
        for call in player.play_if_idle.call_args_list[1:]:
            clip = call.args[0]
            self.assertTrue(clip.is_file())
            self.assertTrue(
                "praise.general" in clip.name or "ready.go" in clip.name, clip.name
            )

    def test_never_interrupts_a_playing_clip(self) -> None:
        player = mock.Mock()
        player.is_busy.return_value = True
        voice = HomeGreeterVoice(REPO_ROOT, player, lambda: "en")
        self.assertFalse(voice.speak("leo", 0.0, None))
        player.play_if_idle.assert_not_called()

    def test_rate_limiter_cooldown_and_window(self) -> None:
        limiter = VoiceRateLimiter()
        limiter.record(0.0)
        self.assertFalse(limiter.allows(2.9))
        for t in (3.0, 6.0, 9.0):
            self.assertTrue(limiter.allows(t))
            limiter.record(t)
        self.assertFalse(limiter.allows(30.0))
        self.assertTrue(limiter.allows(60.5))


class _CountingSurface(pygame.Surface):
    created = 0

    def __init__(self, *args, **kwargs) -> None:
        type(self).created += 1
        super().__init__(*args, **kwargs)


class HomeShellAnimationTests(unittest.TestCase):
    """One real Shell Home driven through the production ambient hook."""

    @classmethod
    def setUpClass(cls) -> None:
        from greia_launcher.child_shell import GreiaChildShell

        pygame.init()
        pygame.font.init()
        cls.clock = _Clock()
        cls._time_patch = mock.patch.object(
            home_presentation, "time", SimpleNamespace(monotonic=cls.clock.monotonic)
        )
        cls._time_patch.start()
        cls.screen = pygame.display.set_mode(SCREEN)
        cls.shell = GreiaChildShell(windowed=True)
        if cls.shell._visual_cache is None:
            raise unittest.SkipTest("shared visuals unavailable")
        cls.shell.profiles = cls.shell.profile_store.ensure_initialized()
        cls.shell._activate_profile(cls.shell.profiles[0], pygame)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._time_patch.stop()

    def setUp(self) -> None:
        self.clock.now += 1000.0
        self.shell._home_greeter_focused = False
        self.shell._home_collection_selected = 0
        self.shell._cached_activities_key = None
        self.shell._last_input_monotonic = self.clock.now
        self.shell._draw(self.screen, pygame)
        self.animator = self.shell._home_animator
        self.assertIsNotNone(self.animator)
        self.assertTrue(self.shell._home_overlay_live)

    def _frame(self, dt: float) -> bool:
        self.clock.now += dt
        return self.shell._present_ambient_frame(self.screen, pygame, self.clock.now)

    def _busy(self) -> None:
        scenery = self.animator._scenery
        greeter = self.animator.greeter_rect
        self.shell._handle_click((greeter.x + greeter.width // 2, greeter.y + 100), pygame)
        tree = scenery.tree_hit
        for _ in range(3):
            self.shell._handle_click((tree.x + tree.width // 2, tree.y + tree.height // 2), pygame)
        self.shell._handle_click(scenery.sun_center, pygame)
        self.shell._last_input_monotonic = self.clock.now

    def test_home_greeter_and_scenery_are_live(self) -> None:
        scenery = self.animator._scenery
        self.assertIsNotNone(scenery.tree_hit)
        self.assertIsNotNone(scenery.sun_center)
        self.assertEqual(len(scenery.clouds), 2)
        self.assertEqual(self.animator.greeter_rect, GREETER)

    def test_sprites_reach_the_screen_rle_encoded_with_the_same_pixels(self) -> None:
        # Acer 87322f0d: un-encoded greeter/cloud sprites cost ~19 ms of each
        # ~28 ms Home pointer-move frame on the Atom.
        from greia_platform.pygame_blit import is_rle

        base = self.shell._cached_activities_surface.copy()
        raw, fast = base.copy(), base.copy()
        for sprite, x, y in self.animator._items:
            raw.blit(sprite, (x, y))
        self.animator.draw(fast)
        self.assertTrue(self.animator._items)
        for sprite, _x, _y in self.animator._items:
            self.assertTrue(is_rle(self.animator._presentable(sprite, fast)))
            self.assertFalse(is_rle(sprite), "the shared visual cache stays untouched")
        worst = max(
            max(abs(a - b) for a, b in zip(raw.get_at((x, y))[:3], fast.get_at((x, y))[:3]))
            for y in range(0, SCREEN[1], 3)
            for x in range(0, SCREEN[0], 3)
        )
        self.assertLessEqual(worst, 1)
        overlay = pygame.Surface(SCREEN, pygame.SRCALPHA)
        sprite = self.animator._items[0][0]
        self.assertIs(self.animator._presentable(sprite, overlay), sprite)

    def test_two_hundred_ticks_construct_no_surfaces(self) -> None:
        self._busy()
        self._frame(0.0)  # first frame after the taps
        calls = {"transform": 0}

        def counting(original):
            def wrapper(*args, **kwargs):
                calls["transform"] += 1
                return original(*args, **kwargs)

            return wrapper

        _CountingSurface.created = 0
        patches = [mock.patch.object(pygame, "Surface", _CountingSurface)]
        for name in ("smoothscale", "scale", "rotozoom", "rotate", "flip"):
            patches.append(
                mock.patch.object(pygame.transform, name, counting(getattr(pygame.transform, name)))
            )
        for patch in patches:
            patch.start()
        try:
            presented = sum(self._frame(1 / 24) for _ in range(200))
        finally:
            for patch in patches:
                patch.stop()
        self.assertGreater(presented, 20)
        self.assertEqual(_CountingSurface.created, 0)
        self.assertEqual(calls["transform"], 0)

    def test_dirty_area_per_frame_is_small(self) -> None:
        self._busy()
        areas: list[int] = []
        real_update = pygame.display.update

        def spy(rects=None):
            areas.append(sum(r.width * r.height for r in rects))
            return real_update(rects)

        with mock.patch.object(pygame.display, "update", spy):
            for _ in range(120):
                self._frame(1 / 24)
        self.assertTrue(areas)
        limit = 0.15 * SCREEN[0] * SCREEN[1]
        self.assertLessEqual(max(areas), limit, max(areas))

    def test_dirty_frames_match_a_full_redraw(self) -> None:
        self._busy()
        for _ in range(30):
            self._frame(1 / 24)
        # Compare at a moment the incremental path actually presented.
        for _ in range(50):
            if self._frame(1 / 24):
                break
        incremental = self.screen.copy()
        self.shell._draw(self.screen, pygame)
        diff = [
            (x, y)
            for y in range(0, SCREEN[1], 2)
            for x in range(0, SCREEN[0], 2)
            if incremental.get_at((x, y)) != self.screen.get_at((x, y))
        ]
        self.assertEqual(diff[:5], [], (min(diff), max(diff)) if diff else None)

    def test_portals_win_hit_testing(self) -> None:
        portal = next(t for t in self.shell._targets if t.action == "home_collection")
        with mock.patch.object(self.animator, "hit", return_value="sun") as hit, mock.patch.object(
            self.animator, "tap"
        ) as tap:
            self.shell._handle_click(portal.rect.center, pygame)
        hit.assert_not_called()
        tap.assert_not_called()
        self.assertEqual(self.shell._category_id, portal.value)
        self.shell._set_category(ALL_ACTIVITIES_ID)

    def test_scenery_never_touches_targets_or_hud(self) -> None:
        scenery = self.animator._scenery
        areas = [scenery.sun_area, scenery.tree_area, *(sweep for _, sweep in scenery.clouds)]
        for target in self.shell._targets:
            for area in areas:
                rect = pygame.Rect(area.x, area.y, area.width, area.height)
                self.assertFalse(rect.colliderect(target.rect), (target.action, area))
        for area in areas:
            self.assertGreaterEqual(area.y, 95)

    def test_keyboard_reaches_greeter_and_activates_it(self) -> None:
        shell = self.shell
        columns = shell._home_columns(pygame)
        shell._home_collection_selected = columns  # first column, second row
        shell._handle_key(pygame.K_LEFT, pygame)
        self.assertTrue(shell._home_greeter_focused)
        self.assertEqual(shell._home_collection_selected, -1)  # no portal ring
        with mock.patch.object(self.animator, "tap") as tap:
            shell._handle_key(pygame.K_RETURN, pygame)
        tap.assert_called_once()
        self.assertEqual(tap.call_args.args[0], "greeter")
        shell._handle_key(pygame.K_RIGHT, pygame)  # back to the portal beside it
        self.assertFalse(shell._home_greeter_focused)
        self.assertEqual(shell._home_collection_selected, columns)
        shell._home_collection_selected = 0
        shell._handle_key(pygame.K_LEFT, pygame)
        self.assertTrue(shell._home_greeter_focused)
        shell._handle_key(pygame.K_TAB, pygame)
        self.assertFalse(shell._home_greeter_focused)
        self.assertEqual(shell._home_collection_selected, 0)

    def test_ceremony_reaction_repaints_only_outside_the_card_zone(self) -> None:
        shell = self.shell
        shell._achievement_celebration = object()
        try:
            self.assertTrue(shell._home_react("cheer"))
            zone = shell._home_celebration_zone(self.screen, pygame)
            painted: list[pygame.Rect] = []
            real_update = pygame.display.update

            def spy(rects=None):
                painted.extend(rects)
                return real_update(rects)

            # Isolate the Home animator: the ceremony's own frames are the
            # achievement presentation's business.
            with mock.patch.object(pygame.display, "update", spy), mock.patch.object(
                shell, "_draw", wraps=shell._draw
            ) as draw, mock.patch.object(
                shell, "_present_achievement_frame", return_value=False, create=True
            ):
                for _ in range(48):
                    self._frame(1 / 24)
            draw.assert_not_called()
            self.assertTrue(painted)
            for rect in painted:
                self.assertFalse(rect.colliderect(zone), rect)
        finally:
            shell._achievement_celebration = None

    def test_scenery_taps_grant_nothing(self) -> None:
        before = self.shell._achievement_snapshot
        self._busy()
        for _ in range(48):
            self._frame(1 / 24)
        self.assertIs(self.shell._achievement_snapshot, before)


if __name__ == "__main__":
    unittest.main()
