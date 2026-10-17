"""A repeated Activity Home tap must not switch the child's profile.

Acer reference, 2026-10-17: Home in an Activity, then Home again 0.94 s
later, went Activity -> Collection page -> profile picker, because the second
tap reached the Shell's active-profile switcher drawn under the protected
Home corner. After any launch the Shell now ignores primary releases in the
protected Home/Back region for a short bounded interval.
"""

from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from greia_launcher import main as launcher_main
from greia_launcher.main import LauncherApplication
from greia_launcher.return_tap_guard import RETURN_TAP_GUARD_SECONDS, ReturnTapGuard
from greia_platform.system_chrome import ActivitySystemChromeLayout

#: Centre of the active-profile switcher on Home and Collection pages (14,10 + 85 px).
PROFILE_BADGE = (56, 52)
#: Centre of the protected Activity Home hit box at 1024x600.
ACTIVITY_HOME = (38, 38)


class ReturnTapGuardTests(unittest.TestCase):
    def test_protected_corner_is_ignored_only_inside_the_window(self) -> None:
        guard = ReturnTapGuard.after_activity(1024, 600, 100.0)
        self.assertTrue(guard.swallows(ACTIVITY_HOME, 100.2))
        self.assertTrue(guard.swallows(PROFILE_BADGE, 100.0 + RETURN_TAP_GUARD_SECONDS - 0.01))
        self.assertFalse(guard.swallows(PROFILE_BADGE, 100.0 + RETURN_TAP_GUARD_SECONDS))
        self.assertFalse(guard.swallows((512, 400), 100.2))  # a Collection tile works at once

    def test_region_is_the_whole_reserved_home_and_back_footprint(self) -> None:
        layout = ActivitySystemChromeLayout.for_surface(1024, 600, back_available=True)
        guard = ReturnTapGuard.after_activity(1024, 600, 0.0)
        self.assertEqual(guard.region, layout.protected_region)
        back = layout.back_hitbox
        self.assertTrue(guard.swallows((back.x + 2, back.y + 2), 0.5))

    def test_a_larger_launch_home_box_widens_the_region(self) -> None:
        box = SimpleNamespace(x=8, y=8, width=120, height=120)
        guard = ReturnTapGuard.after_activity(1024, 600, 0.0, home_box=box)
        self.assertTrue(guard.swallows((120, 120), 0.1))

    def test_unarmed_or_tiny_surface_guards_nothing(self) -> None:
        self.assertFalse(ReturnTapGuard().swallows(ACTIVITY_HOME, 0.0))
        self.assertIsNone(ReturnTapGuard.after_activity(40, 30, 0.0).region)


class _Session:
    def __init__(self) -> None:
        from greia_launcher.lifecycle import ActivitySessionState

        self.state = ActivitySessionState.STARTING
        self.control = SimpleNamespace(ready=lambda: False)
        self.result = None


class _EndingSupervisor:
    """Starts a fake Activity that ends (Home) on its second poll."""

    def __init__(self) -> None:
        self.polls = 0

    def start(self, manifest: object, profile: object, authority: object) -> _Session:
        return _Session()

    def poll(self, session: _Session) -> object | None:
        self.polls += 1
        return "home" if self.polls >= 2 else None


class ShellReturnTests(unittest.TestCase):
    """The Shell arms the guard when it regains the foreground after a launch."""

    def setUp(self) -> None:
        pygame.display.init()
        pygame.display.set_mode((1024, 600))

    def tearDown(self) -> None:
        pygame.display.quit()

    def _shell(self) -> LauncherApplication:
        shell = object.__new__(LauncherApplication)
        profile = SimpleNamespace(
            profile=SimpleNamespace(profile_id="0123456789abcdef0123456789abcdef"),
            activity_data_dir=lambda activity_id: (_ for _ in ()).throw(OSError("no card")),
        )
        shell._activities = (SimpleNamespace(activity_id="org.greia.demo", creations_consumes=False),)
        shell._selected = 0
        shell._active_profile = profile
        shell._last_result = None
        shell._catalogue_error = False
        shell.registry = SimpleNamespace(registration_for=lambda manifest: object())
        shell.runtime_services = SimpleNamespace(
            permission_broker=SimpleNamespace(issue=lambda registration: object())
        )
        shell.supervisor = _EndingSupervisor()
        shell._shell_input = SimpleNamespace(start=lambda: None)
        shell.profile_store = SimpleNamespace(consume_avatar_request=lambda profile_id: None)
        shell.session = SimpleNamespace(activate=lambda store, profile_id: profile)
        shell.theme_controller = SimpleNamespace(invalidate=lambda: None, theme=None)
        shell._draw_launch_overlay = lambda pygame, *, text: None
        shell.FOREGROUND_CADENCE = launcher_main.ActivityForegroundCadence(
            starting_poll_seconds=0.0, wait_screen_frame_seconds=0.0
        )
        return shell

    def test_second_home_tap_after_return_never_reaches_the_profile_switcher(self) -> None:
        shell = self._shell()
        self.assertFalse(shell._return_tap_swallowed(PROFILE_BADGE))  # before any launch
        shell._launch_selected(pygame)
        self.assertEqual(shell._last_result, "home")
        self.assertTrue(shell._return_tap_swallowed(ACTIVITY_HOME))
        self.assertTrue(shell._return_tap_swallowed(PROFILE_BADGE))
        self.assertFalse(shell._return_tap_swallowed((512, 400)))

    def test_profile_switcher_works_again_after_the_interval(self) -> None:
        shell = self._shell()
        shell._launch_selected(pygame)
        later = launcher_main.time.monotonic() + RETURN_TAP_GUARD_SECONDS + 0.1
        with mock.patch.object(launcher_main.time, "monotonic", return_value=later):
            self.assertFalse(shell._return_tap_swallowed(PROFILE_BADGE))

    def test_a_failed_start_also_arms_the_guard(self) -> None:
        shell = self._shell()

        def refuse(manifest: object, profile: object, authority: object) -> object:
            raise OSError("sandbox unavailable")

        shell.supervisor.start = refuse
        shell._launch_selected(pygame)
        self.assertTrue(shell._catalogue_error)
        self.assertTrue(shell._return_tap_swallowed(PROFILE_BADGE))


if __name__ == "__main__":
    unittest.main()
