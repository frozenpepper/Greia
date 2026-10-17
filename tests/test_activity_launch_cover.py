"""Launch hand-off: the Shell's launch card covers the Activity's black window.

The Activity entry paints the card exactly once, inside the Activity's first
``set_mode`` (so never after the Activity's own frames), falls back to the
theme colour (never black) without a usable card, and imports nothing an
Activity may not import.
"""

from __future__ import annotations

import ast
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import tomllib
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from types import SimpleNamespace

from greia_launcher.foreground_cadence import ActivityForegroundCadence
from greia_launcher.lifecycle import ActivitySessionState
from greia_launcher.main import LauncherApplication
from greia_platform import activity_launch_cover as cover_module
from greia_platform.activity_launch_cover import (
    DEFAULT_COVER_COLOR,
    ActivityLaunchCover,
    LaunchCard,
    LaunchCardError,
    LaunchCardPublisher,
    install_activity_launch_cover,
    launch_card_path,
    read_launch_card,
    theme_background_color,
)

ROOT = Path(__file__).resolve().parents[1]
CORAL = (240, 110, 90)
SNAPSHOT = '{"background":"cream","background_color":"#102030","schema_version":1}'


def _solid_card(size: tuple[int, int], color: tuple[int, int, int]) -> LaunchCard:
    return LaunchCard(size[0], size[1], bytes(color) * (size[0] * size[1]))


class LaunchCardFormatTests(unittest.TestCase):
    def test_round_trip_keeps_pixels(self) -> None:
        card = LaunchCard(3, 2, bytes(range(18)))
        decoded = LaunchCard.decode(card.encode())
        self.assertEqual(decoded.size, (3, 2))
        self.assertEqual(bytes(decoded.rgb), bytes(range(18)))

    def test_malformed_cards_are_rejected(self) -> None:
        good = LaunchCard(2, 2, bytes(12)).encode()
        for data in (b"", good[:10], b"NOTACARD" + good[8:], good + b"x", good[:-1]):
            with self.subTest(length=len(data)):
                with self.assertRaises(LaunchCardError):
                    LaunchCard.decode(data)
        with self.assertRaises(LaunchCardError):
            LaunchCard(2, 2, bytes(11))
        with self.assertRaises(LaunchCardError):
            LaunchCard(4000, 4000, b"")

    def test_reader_is_fail_soft(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "launch-card"
            self.assertIsNone(read_launch_card(path))
            path.write_bytes(b"garbage")
            self.assertIsNone(read_launch_card(path))
            target = Path(temporary) / "real"
            target.write_bytes(LaunchCard(1, 1, b"abc").encode())
            path.unlink()
            path.symlink_to(target)
            self.assertIsNone(read_launch_card(path))  # never follows a link

    def test_theme_colour_parsing(self) -> None:
        self.assertEqual(theme_background_color(SNAPSHOT), (0x10, 0x20, 0x30))
        for value in (None, "", "{}", '{"background_color":"#12"}', '{"background_color":"#zzzzzz"}'):
            with self.subTest(value=value):
                self.assertEqual(theme_background_color(value), DEFAULT_COVER_COLOR)


class LaunchCardPublisherTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self.data = self.root / "activity-data"
        self.data.mkdir()
        self.publisher = LaunchCardPublisher()

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def test_publish_consume_discard(self) -> None:
        card = _solid_card((4, 3), CORAL)
        self.assertTrue(self.publisher.consumed(self.data))  # nothing published
        self.assertTrue(self.publisher.publish(self.data, card))
        self.assertFalse(self.publisher.consumed(self.data))
        loaded = read_launch_card(launch_card_path(self.data))
        self.assertIsNotNone(loaded)
        self.assertEqual(bytes(loaded.rgb), bytes(card.rgb))
        self.assertEqual(sorted(p.name for p in (self.data / ".greia").iterdir()), ["launch-card"])
        self.publisher.discard(self.data)
        self.assertTrue(self.publisher.consumed(self.data))
        self.publisher.discard(self.data)  # idempotent

    def test_planted_symlinks_never_redirect_shell_writes(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        (self.data / ".greia").symlink_to(outside, target_is_directory=True)
        self.assertFalse(self.publisher.publish(self.data, _solid_card((2, 2), CORAL)))
        self.assertEqual(list(outside.iterdir()), [])
        self.publisher.discard(self.data)

        (self.data / ".greia").unlink()
        (self.data / ".greia").mkdir()
        victim = self.root / "victim"
        victim.write_bytes(b"precious")
        launch_card_path(self.data).symlink_to(victim)
        self.assertTrue(self.publisher.publish(self.data, _solid_card((2, 2), CORAL)))
        self.assertEqual(victim.read_bytes(), b"precious")  # link replaced, not followed
        self.assertFalse(launch_card_path(self.data).is_symlink())


class _FlipCounter:
    def __init__(self) -> None:
        self.original = pygame.display.flip
        self.count = 0

    def __enter__(self) -> "_FlipCounter":
        def flip() -> None:
            self.count += 1
            self.original()

        pygame.display.flip = flip
        return self

    def __exit__(self, *exc: object) -> None:
        pygame.display.flip = self.original


class ActivityLaunchCoverTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.display.init()
        self.original_set_mode = pygame.display.set_mode
        self._temporary = tempfile.TemporaryDirectory()
        self.data = Path(self._temporary.name)

    def tearDown(self) -> None:
        pygame.display.set_mode = self.original_set_mode
        pygame.display.quit()
        self._temporary.cleanup()

    def _environment(self, **extra: str) -> dict[str, str]:
        return {
            "GREIA_ACTIVITY_SESSION_ID": "0123456789abcdef0123456789abcdef",
            "GREIA_ACTIVITY_DATA_DIR": str(self.data),
            "GREIA_THEME_SNAPSHOT": SNAPSHOT,
            **extra,
        }

    def test_card_is_painted_exactly_once_on_first_set_mode(self) -> None:
        LaunchCardPublisher().publish(self.data, _solid_card((320, 240), CORAL))
        cover = install_activity_launch_cover(pygame, self._environment())
        self.assertIsNotNone(cover)
        self.assertIsNot(pygame.display.set_mode, self.original_set_mode)
        with _FlipCounter() as flips:
            screen = pygame.display.set_mode((320, 240))
            self.assertEqual(flips.count, 1)
            self.assertEqual(tuple(screen.get_at((10, 10)))[:3], CORAL)
            self.assertEqual(tuple(screen.get_at((319, 239)))[:3], CORAL)
            # The real set_mode is back and the consumed card is gone, which
            # tells the Shell the Activity window now covers the screen.
            self.assertIs(pygame.display.set_mode, self.original_set_mode)
            self.assertFalse(launch_card_path(self.data).exists())
            self.assertTrue(LaunchCardPublisher().consumed(self.data))

            # The Activity's own frames are never overpainted afterwards.
            screen.fill((1, 2, 3))
            pygame.display.flip()
            self.assertFalse(cover.paint(screen, pygame))
            pygame.display.set_mode((320, 240))
            self.assertEqual(flips.count, 2)

    def test_outer_wrapper_does_not_cause_a_second_paint(self) -> None:
        LaunchCardPublisher().publish(self.data, _solid_card((64, 48), CORAL))
        install_activity_launch_cover(pygame, self._environment())
        inner = pygame.display.set_mode

        def outer(*args: object, **kwargs: object) -> object:  # e.g. a simulator
            return inner(*args, **kwargs)

        pygame.display.set_mode = outer
        with _FlipCounter() as flips:
            outer((64, 48))
            screen = outer((64, 48))
            screen.fill((9, 9, 9))
            outer((64, 48))
        self.assertEqual(flips.count, 1)

    def test_missing_card_falls_back_to_theme_colour_never_black(self) -> None:
        install_activity_launch_cover(pygame, self._environment())
        with _FlipCounter() as flips:
            screen = pygame.display.set_mode((200, 120))
        self.assertEqual(flips.count, 1)
        self.assertEqual(tuple(screen.get_at((100, 60)))[:3], (0x10, 0x20, 0x30))

    def test_damaged_card_and_no_theme_use_default_cream(self) -> None:
        path = launch_card_path(self.data)
        path.parent.mkdir()
        path.write_bytes(b"GREIALC1 damaged")
        environment = self._environment()
        del environment["GREIA_THEME_SNAPSHOT"]
        install_activity_launch_cover(pygame, environment)
        screen = pygame.display.set_mode((100, 80))
        self.assertEqual(tuple(screen.get_at((50, 40)))[:3], DEFAULT_COVER_COLOR)

    def test_smaller_card_lines_up_at_origin(self) -> None:
        # An 800x480 Shell screen under a 1024x600 Activity window.
        LaunchCardPublisher().publish(self.data, _solid_card((80, 48), CORAL))
        install_activity_launch_cover(pygame, self._environment())
        screen = pygame.display.set_mode((102, 60))
        self.assertEqual(tuple(screen.get_at((0, 0)))[:3], CORAL)
        self.assertEqual(tuple(screen.get_at((79, 47)))[:3], CORAL)
        self.assertEqual(tuple(screen.get_at((90, 55)))[:3], (0x10, 0x20, 0x30))

    def test_paint_failure_never_breaks_the_activity(self) -> None:
        class BrokenSurface:
            def get_flags(self) -> int:
                return 0

            def get_size(self) -> tuple[int, int]:
                return (10, 10)

            def fill(self, color: object) -> None:
                raise pygame.error("surface lost")

        cover = ActivityLaunchCover(None)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertFalse(cover.paint(BrokenSurface(), pygame))
        self.assertFalse(cover.paint(None, pygame))

    def _record_set_mode(self, *, fail_hidden: bool = False) -> list[tuple[tuple, dict]]:
        calls: list[tuple[tuple, dict]] = []
        real = pygame.display.set_mode

        def recording(*args: object, **kwargs: object) -> object:
            calls.append((args, dict(kwargs)))
            flags = args[1] if len(args) > 1 else kwargs.get("flags", 0)
            if fail_hidden and flags & pygame.HIDDEN:
                raise pygame.error("no hidden windows here")
            return real(*args, **kwargs)

        pygame.display.set_mode = recording
        return calls

    def test_first_window_opens_hidden_then_shows_before_the_card_flip(self) -> None:
        # The black frame at 4d6e9c5e came from mapping the window in the
        # first set_mode; the window must be unmapped until it is shown.
        LaunchCardPublisher().publish(self.data, _solid_card((96, 64), CORAL))
        calls = self._record_set_mode()
        install_activity_launch_cover(pygame, self._environment())
        with _FlipCounter() as flips:
            screen = pygame.display.set_mode((96, 64), pygame.RESIZABLE)
        self.assertEqual(len(calls), 2)
        hidden_args, _ = calls[0]
        shown_args, _ = calls[1]
        self.assertEqual(hidden_args[0], (96, 64))
        self.assertTrue(hidden_args[1] & pygame.HIDDEN)
        self.assertTrue(hidden_args[1] & pygame.RESIZABLE)
        self.assertFalse(shown_args[1] & pygame.HIDDEN)
        self.assertTrue(shown_args[1] & pygame.SHOWN)
        self.assertTrue(shown_args[1] & pygame.RESIZABLE)
        self.assertEqual(flips.count, 1)
        self.assertIs(screen, pygame.display.get_surface())
        self.assertEqual(tuple(screen.get_at((50, 30)))[:3], CORAL)

    def test_keyword_and_default_flags_also_open_hidden(self) -> None:
        calls = self._record_set_mode()
        install_activity_launch_cover(pygame, self._environment())
        pygame.display.set_mode(size=(40, 30))
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][1]["flags"], pygame.HIDDEN)
        self.assertEqual(calls[1][1]["flags"], pygame.SHOWN)
        self.assertEqual(calls[1][1]["size"], (40, 30))

    def test_hidden_or_opengl_requests_pass_through_once(self) -> None:
        calls = self._record_set_mode()
        install_activity_launch_cover(pygame, self._environment())
        pygame.display.set_mode((40, 30), pygame.HIDDEN)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0][1], pygame.HIDDEN)

    def test_a_failing_hidden_window_falls_back_to_the_plain_call(self) -> None:
        LaunchCardPublisher().publish(self.data, _solid_card((40, 30), CORAL))
        calls = self._record_set_mode(fail_hidden=True)
        install_activity_launch_cover(pygame, self._environment())
        with contextlib.redirect_stderr(io.StringIO()):
            screen = pygame.display.set_mode((40, 30))
        self.assertEqual([args[1] if len(args) > 1 else None for args, _ in calls][-1], None)
        self.assertEqual(tuple(screen.get_at((5, 5)))[:3], CORAL)

    def test_nothing_is_installed_outside_a_greia_session(self) -> None:
        environment = self._environment()
        del environment["GREIA_ACTIVITY_SESSION_ID"]
        self.assertIsNone(install_activity_launch_cover(pygame, environment))
        self.assertIs(pygame.display.set_mode, self.original_set_mode)


class _Session:
    def __init__(self) -> None:
        self.state = ActivitySessionState.STARTING
        self.control = SimpleNamespace(ready=lambda: False)
        self.result = None


class _CoveringActivitySupervisor:
    """Starts a fake Activity whose entry consumes the card on its 3rd poll."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.card_at_start: bool | None = None
        self.polls = 0

    def start(self, manifest: object, profile: object, authority: object) -> _Session:
        self.card_at_start = launch_card_path(self.data_dir).exists()
        return _Session()

    def poll(self, session: _Session) -> object | None:
        self.polls += 1
        if self.polls == 3:
            launch_card_path(self.data_dir).unlink()  # the Activity painted it
        return "done" if self.polls >= 8 else None


class _Shell(LauncherApplication):
    FOREGROUND_CADENCE = ActivityForegroundCadence(
        starting_poll_seconds=0.0, wait_screen_frame_seconds=0.0
    )

    def _draw_launch_overlay(self, pygame: object, *, text: str) -> None:
        self.overlays.append(self.supervisor.polls)
        pygame.display.get_surface().fill(CORAL)


class ShellLaunchHandOffTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.display.init()
        self.screen = pygame.display.set_mode((64, 48))
        self._temporary = tempfile.TemporaryDirectory()
        self.data = Path(self._temporary.name)

    def tearDown(self) -> None:
        pygame.display.quit()
        self._temporary.cleanup()

    def _shell(self) -> _Shell:
        shell = object.__new__(_Shell)
        shell.overlays = []
        profile = SimpleNamespace(
            profile=SimpleNamespace(profile_id="0123456789abcdef0123456789abcdef"),
            activity_data_dir=lambda activity_id: self.data,
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
        shell.supervisor = _CoveringActivitySupervisor(self.data)
        shell._shell_input = SimpleNamespace(start=lambda: None)
        shell.profile_store = SimpleNamespace(consume_avatar_request=lambda profile_id: None)
        shell.session = SimpleNamespace(activate=lambda store, profile_id: profile)
        shell.theme_controller = SimpleNamespace(invalidate=lambda: None, theme=None)
        return shell

    def test_card_is_published_before_start_and_repaint_stops_once_covered(self) -> None:
        shell = self._shell()
        shell._launch_selected(pygame)
        supervisor = shell.supervisor
        self.assertTrue(supervisor.card_at_start)  # the Activity can read it at once
        self.assertEqual(shell.overlays[0], 0)  # launch screen shown before start
        # Repainted while visible (polls 1-2), never after the card was consumed.
        self.assertTrue(shell.overlays[1:])
        self.assertLessEqual(max(shell.overlays), 2)
        self.assertEqual(shell._last_result, "done")
        self.assertFalse(launch_card_path(self.data).exists())

    def test_card_is_discarded_when_the_activity_never_consumes_it(self) -> None:
        shell = self._shell()
        supervisor = shell.supervisor
        supervisor.poll = lambda session: "crashed"  # exits before set_mode
        shell._launch_selected(pygame)
        self.assertEqual(shell._last_result, "crashed")
        self.assertFalse(launch_card_path(self.data).exists())

    def test_card_holds_the_presented_launch_screen(self) -> None:
        shell = self._shell()
        shell.supervisor.start = lambda manifest, profile, authority: (
            self.__setattr__("card", read_launch_card(launch_card_path(self.data)))
            or SimpleNamespace(result="refused")
        )
        shell._launch_selected(pygame)
        self.assertEqual(self.card.size, (64, 48))
        self.assertEqual(bytes(self.card.rgb[:3]), bytes(CORAL))
        self.assertFalse(launch_card_path(self.data).exists())


class _HomeAwareSupervisor(_CoveringActivitySupervisor):
    """Adds the trusted-chrome hooks the Shell uses during a launch."""

    def __init__(self, data_dir: Path) -> None:
        super().__init__(data_dir)
        self.cancelled = 0
        self.restacked: list[int] = []
        self.tap_during_start: tuple[int, int] | None = None

    def start(self, manifest: object, profile: object, authority: object) -> _Session:
        session = super().start(manifest, profile, authority)
        if self.tap_during_start is not None:
            # The child taps the launch screen's Home while the Shell is busy.
            pygame.event.post(
                pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=self.tap_during_start)
            )
        return session

    def paint_launch_home(self, surface: object, pygame_module: object) -> object:
        surface.fill((78, 56, 40), (8, 8, 20, 20))
        return SimpleNamespace(x=8, y=8, width=20, height=20)

    def cancel_launch(self, session: _Session) -> None:
        self.cancelled += 1
        session.result = "cancelled"

    def poll(self, session: _Session) -> object | None:
        if session.result is not None:
            return session.result
        return super().poll(session)

    def ensure_system_chrome_visible(self, session: _Session) -> bool:
        self.restacked.append(self.polls)
        return True


class _HomeShell(_Shell):
    """Subclasses (the child Shell) replace the overlay; Home is still drawn."""


class ShellLaunchHomeTests(unittest.TestCase):
    """Home is on the launch screen and works before the Activity is READY."""

    setUp = ShellLaunchHandOffTests.setUp
    tearDown = ShellLaunchHandOffTests.tearDown
    _shell = ShellLaunchHandOffTests._shell

    def _home_shell(self) -> _HomeShell:
        shell = self._shell()
        shell.__class__ = _HomeShell
        shell.supervisor = _HomeAwareSupervisor(self.data)
        return shell

    def test_launch_card_carries_home(self) -> None:
        shell = self._home_shell()
        shell.supervisor.start = lambda manifest, profile, authority: (
            self.__setattr__("card", read_launch_card(launch_card_path(self.data)))
            or SimpleNamespace(result="refused")
        )
        shell._launch_selected(pygame)
        offset = (10 * 64 + 10) * 3  # pixel (10, 10) of the 64x48 card
        self.assertEqual(bytes(self.card.rgb[offset:offset + 3]), bytes((78, 56, 40)))

    def test_home_tap_on_the_launch_screen_cancels_the_launch(self) -> None:
        shell = self._home_shell()
        shell.supervisor.tap_during_start = (12, 12)
        shell._launch_selected(pygame)
        self.assertEqual(shell.supervisor.cancelled, 1)
        self.assertEqual(shell._last_result, "cancelled")
        self.assertFalse(launch_card_path(self.data).exists())

    def test_tap_outside_home_is_ignored(self) -> None:
        shell = self._home_shell()
        shell.supervisor.tap_during_start = (40, 30)
        shell._launch_selected(pygame)
        self.assertEqual(shell.supervisor.cancelled, 0)
        self.assertEqual(shell._last_result, "done")

    def test_home_is_restacked_once_the_activity_window_covers_the_shell(self) -> None:
        shell = self._home_shell()
        shell._launch_selected(pygame)
        # The fake Activity consumed the card on poll 3: restacked right then.
        self.assertEqual(shell.supervisor.restacked, [3])


class ActivityEntryIntegrationTests(unittest.TestCase):
    """The real platform entry, as the Python runtime adapter launches it."""

    def _run(self, temporary: Path, *, session: bool) -> dict[str, object]:
        activity = temporary / "activity"
        activity.mkdir()
        (activity / "main.py").write_text(
            textwrap.dedent(
                """
                import json, os, sys
                import pygame
                wrapped = not isinstance(pygame.display.set_mode, type(len))
                screen = pygame.display.set_mode((64, 48))
                data = os.environ.get("GREIA_ACTIVITY_DATA_DIR", "")
                print(json.dumps({
                    "wrapped_before": wrapped,
                    "restored": isinstance(pygame.display.set_mode, type(len)),
                    "pixel": list(screen.get_at((5, 5)))[:3],
                    "card_left": os.path.exists(os.path.join(data, ".greia", "launch-card")),
                }))
                """
            ),
            encoding="utf-8",
        )
        data = temporary / "data"
        data.mkdir()
        LaunchCardPublisher().publish(data, _solid_card((64, 48), CORAL))
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("GREIA_")
        }
        environment.update(
            PYTHONPATH=str(ROOT / "src"),
            PYTHONDONTWRITEBYTECODE="1",
            SDL_VIDEODRIVER="dummy",
            SDL_AUDIODRIVER="dummy",
            GREIA_ACTIVITY_DATA_DIR=str(data),
        )
        if session:
            environment["GREIA_ACTIVITY_SESSION_ID"] = "0123456789abcdef0123456789abcdef"
        result = subprocess.run(
            [sys.executable, "-P", "-m", "greia_platform.python_activity_entry",
             str(activity / "main.py")],
            cwd=temporary, env=environment, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout.strip().splitlines()[-1])

    def test_entry_presents_the_card_in_a_greia_session(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            payload = self._run(Path(temporary), session=True)
        self.assertTrue(payload["wrapped_before"])
        self.assertTrue(payload["restored"])
        self.assertEqual(payload["pixel"], list(CORAL))
        self.assertFalse(payload["card_left"])

    def test_entry_leaves_set_mode_alone_outside_a_session(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            payload = self._run(Path(temporary), session=False)
        self.assertFalse(payload["wrapped_before"])
        self.assertTrue(payload["card_left"])


class ActivityImportBoundaryTests(unittest.TestCase):
    def test_cover_imports_no_module_forbidden_to_activities(self) -> None:
        policy = tomllib.loads((ROOT / "runtime" / "child-runtime.toml").read_text("utf-8"))
        # ``os`` is already loaded by every interpreter; only *new* modules count.
        forbidden = set(policy["python"]["forbidden_import_roots"]) - {"os"}
        # The entry module's own package is loaded before the cover anyway.
        probe = (
            "import sys, json\n"
            "import greia_platform.python_activity_entry\n"
            "before = set(sys.modules)\n"
            "import greia_platform.activity_launch_cover\n"
            "print(json.dumps(sorted(set(sys.modules) - before)))\n"
        )
        result = subprocess.run(
            [sys.executable, "-P", "-c", probe],
            env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        added = json.loads(result.stdout)
        roots = {name.split(".", 1)[0] for name in added}
        self.assertFalse(roots & forbidden, sorted(roots & forbidden))
        self.assertFalse(roots & {"json", "PIL", "pygame", "subprocess", "ctypes"}, sorted(roots))

    def test_module_does_not_import_pygame_itself(self) -> None:
        tree = ast.parse(Path(cover_module.__file__).read_text("utf-8"))
        imported = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            (node.module or "").split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        self.assertNotIn("pygame", imported)


if __name__ == "__main__":
    unittest.main()
