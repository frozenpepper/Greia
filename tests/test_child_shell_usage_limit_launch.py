from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

from greia_launcher.catalogue_view import ALL_ACTIVITIES_ID
from greia_launcher.child_shell import GreiaChildShell
from greia_launcher.presentation import GreiaLauncherPresentation
from greia_platform.usage_limits import UsageLimitError


class _UsageService:
    def __init__(self, *, exhausted: bool = False, error: Exception | None = None):
        self.exhausted = exhausted
        self.error = error

    def status(self, profile_id: str):
        if self.error is not None:
            raise self.error
        return SimpleNamespace(profile_id=profile_id, exhausted=self.exhausted)


def _shell(service: _UsageService) -> GreiaChildShell:
    shell = object.__new__(GreiaChildShell)
    shell._active_profile = SimpleNamespace(
        profile=SimpleNamespace(profile_id="child")
    )
    shell._usage_limits = service
    shell._last_result = object()
    shell._catalogue_error = True
    shell._cached_activities_key = "cached"
    shell._home_collection_selected = 3
    shell._shell_window_backend = mock.Mock()
    return shell


class ChildShellUsageLimitLaunchTests(unittest.TestCase):
    def test_exhausted_budget_stays_on_home_without_starting_activity(self) -> None:
        shell = _shell(_UsageService(exhausted=True))
        categories: list[str] = []
        shell._set_category = categories.append  # type: ignore[method-assign]

        with mock.patch.object(GreiaLauncherPresentation, "_launch_selected") as launch:
            shell._launch_selected(SimpleNamespace())

        launch.assert_not_called()
        self.assertEqual(categories, [ALL_ACTIVITIES_ID])
        self.assertIsNone(shell._last_result)
        self.assertFalse(shell._catalogue_error)
        self.assertEqual(shell._home_collection_selected, 0)
        self.assertIsNone(shell._cached_activities_key)
        shell._shell_window_backend.after_activity_return.assert_not_called()

    def test_available_budget_delegates_to_authoritative_lifecycle(self) -> None:
        shell = _shell(_UsageService(exhausted=False))
        pygame = SimpleNamespace()

        with mock.patch.object(GreiaLauncherPresentation, "_launch_selected") as launch:
            shell._launch_selected(pygame)

        launch.assert_called_once_with(pygame)
        self.assertIsNone(shell._cached_activities_key)
        shell._shell_window_backend.after_activity_return.assert_called_once_with(pygame)

    def test_presentation_read_failure_does_not_bypass_supervisor(self) -> None:
        shell = _shell(_UsageService(error=UsageLimitError("bad ledger")))
        pygame = SimpleNamespace()

        with mock.patch.object(GreiaLauncherPresentation, "_launch_selected") as launch:
            shell._launch_selected(pygame)

        launch.assert_called_once_with(pygame)
        shell._shell_window_backend.after_activity_return.assert_called_once_with(pygame)


if __name__ == "__main__":
    unittest.main()
