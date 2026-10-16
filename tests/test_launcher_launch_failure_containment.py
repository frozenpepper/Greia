"""A failed Activity launch must never take the child Shell down.

Regression for the Acer sweep 2026-10-16 P0: a ``ProfileError`` raised while
preparing the per-Activity data directory escaped ``supervisor.start`` and
crashed the whole child Shell into the trusted-presentation fallback.
"""

from __future__ import annotations

import io
import logging
import sys
import unittest
from types import SimpleNamespace

from greia_launcher import main as launcher_main
from greia_launcher.main import LauncherApplication, configure_launcher_logging
from greia_platform.history import HistoryError
from greia_platform.profiles import ProfileError
from greia_platform.storage import StorageError


class _FakeEvents:
    def __init__(self) -> None:
        self.cleared = 0

    def clear(self) -> None:
        self.cleared += 1


class _RaisingSupervisor:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls = 0

    def start(self, manifest: object, profile: object, authority: object) -> object:
        self.calls += 1
        raise self.error


def _shell(supervisor: object) -> LauncherApplication:
    shell = object.__new__(LauncherApplication)
    shell._activities = (SimpleNamespace(activity_id="painting"),)
    shell._selected = 0
    shell._active_profile = SimpleNamespace(
        profile=SimpleNamespace(profile_id="0123456789abcdef0123456789abcdef")
    )
    shell._mode = "activities"
    shell._last_result = None
    shell._catalogue_error = False
    shell.registry = SimpleNamespace(registration_for=lambda manifest: object())
    shell.runtime_services = SimpleNamespace(
        permission_broker=SimpleNamespace(issue=lambda registration: object())
    )
    shell.supervisor = supervisor
    return shell


class LaunchFailureContainmentTests(unittest.TestCase):
    def test_profile_error_during_launch_keeps_shell_on_collection(self) -> None:
        supervisor = _RaisingSupervisor(
            ProfileError(
                "managed profile directory mode is 2770, expected 0770, and "
                "chmod was refused: /var/lib/greia-profiles/data/x/activities"
            )
        )
        shell = _shell(supervisor)
        pygame = SimpleNamespace(event=_FakeEvents())

        with self.assertLogs("greia_launcher.main", level="ERROR") as logs:
            shell._launch_selected(pygame)  # must not raise

        self.assertEqual(supervisor.calls, 1)
        self.assertEqual(shell._mode, "activities")
        self.assertIsNotNone(shell._active_profile)
        self.assertIsNone(shell._last_result)
        self.assertTrue(shell._catalogue_error)  # existing launch-error badge
        self.assertEqual(len(logs.records), 1)
        record = logs.records[0]
        self.assertIn("painting", record.getMessage())
        self.assertIn("ProfileError", record.getMessage())
        self.assertIsNone(record.exc_info)  # expected fault: one bounded line

        # The Shell remains usable: a second tap is handled the same way.
        with self.assertLogs("greia_launcher.main", level="ERROR"):
            shell._launch_selected(pygame)
        self.assertEqual(supervisor.calls, 2)

    def test_expected_operational_faults_are_contained(self) -> None:
        for error in (
            StorageError("storage refused"),
            HistoryError("history refused"),
            OSError(28, "No space left on device"),
            TimeoutError("timed out"),
        ):
            with self.subTest(error=type(error).__name__):
                shell = _shell(_RaisingSupervisor(error))
                with self.assertLogs("greia_launcher.main", level="ERROR"):
                    shell._launch_selected(SimpleNamespace(event=_FakeEvents()))
                self.assertTrue(shell._catalogue_error)

    def test_programming_error_is_contained_but_logged_with_traceback(self) -> None:
        shell = _shell(_RaisingSupervisor(AttributeError("bug in launch path")))
        with self.assertLogs("greia_launcher.main", level="ERROR") as logs:
            shell._launch_selected(SimpleNamespace(event=_FakeEvents()))
        self.assertTrue(shell._catalogue_error)
        self.assertIsNotNone(logs.records[0].exc_info)

    def test_logged_cause_is_bounded(self) -> None:
        shell = _shell(_RaisingSupervisor(ProfileError("x" * 10_000)))
        with self.assertLogs("greia_launcher.main", level="ERROR") as logs:
            shell._launch_selected(SimpleNamespace(event=_FakeEvents()))
        self.assertLess(len(logs.records[0].getMessage()), 600)


class LauncherLoggingTests(unittest.TestCase):
    def setUp(self) -> None:
        root = logging.getLogger()
        self._handlers = list(root.handlers)
        self._level = root.level
        self._hook = sys.excepthook
        self._flag = getattr(root, "_greia_launcher_logging", None)
        if hasattr(root, "_greia_launcher_logging"):
            del root._greia_launcher_logging

    def tearDown(self) -> None:
        root = logging.getLogger()
        root.handlers[:] = self._handlers
        root.setLevel(self._level)
        sys.excepthook = self._hook
        if hasattr(root, "_greia_launcher_logging"):
            del root._greia_launcher_logging
        if self._flag is not None:
            root._greia_launcher_logging = self._flag

    def test_errors_and_uncaught_crashes_reach_the_configured_stream(self) -> None:
        stream = io.StringIO()
        configure_launcher_logging(syslog_address="/nonexistent/greia-log", stream=stream)
        configure_launcher_logging(syslog_address="/nonexistent/greia-log", stream=stream)
        root = logging.getLogger()
        added = [h for h in root.handlers if h not in self._handlers]
        self.assertEqual(len(added), 1)  # idempotent

        try:
            raise RuntimeError("boom")
        except RuntimeError:
            launcher_main.logger.exception("launch failed")
        try:
            raise ValueError("uncaught crash")
        except ValueError:
            exc_type, exc, tb = sys.exc_info()
        original_stderr = sys.stderr
        sys.stderr = io.StringIO()  # default hook output is not under test
        try:
            sys.excepthook(exc_type, exc, tb)
        finally:
            sys.stderr = original_stderr

        output = stream.getvalue()
        self.assertIn("launch failed", output)
        self.assertIn("Traceback", output)
        self.assertIn("RuntimeError: boom", output)
        self.assertIn("child Shell crashed", output)
        self.assertIn("ValueError: uncaught crash", output)


if __name__ == "__main__":
    unittest.main()
