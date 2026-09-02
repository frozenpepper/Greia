from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from greia_launcher.child_shell import GreiaChildShell
from greia_launcher.presentation import GreiaLauncherPresentation
from greia_launcher.trusted_presentation import TrustedGreiaLauncherPresentation
from greia_platform.activities import ActivityValidationError


class _BrokenParentRegistry:
    def __init__(self, *args, **kwargs) -> None:
        del args, kwargs

    def discover(self):
        raise ActivityValidationError("synthetic damaged Parent package")


class ParentSourceSupervisorFallbackTests(unittest.TestCase):
    def _assert_rebuild(self, presentation_type) -> None:
        presentation = object.__new__(presentation_type)
        presentation.paths = SimpleNamespace(activities=Path("/opt/greia-os/activities"))
        presentation.runtime = object()

        existing_registry = object()
        existing_activities = (object(), object())
        presentation.registry = existing_registry
        presentation._activities = existing_activities
        presentation._catalogue_error = False
        presentation._rebuild_runtime_services = Mock()

        with (
            patch(
                "greia_launcher.presentation._activity_sources",
                return_value=(),
            ),
            patch(
                "greia_launcher.presentation.ActivityRegistry",
                _BrokenParentRegistry,
            ),
        ):
            GreiaLauncherPresentation._configure_parent_package_source(presentation)

        self.assertTrue(presentation._catalogue_error)
        self.assertIs(presentation.registry, existing_registry)
        self.assertIs(presentation._activities, existing_activities)
        presentation._rebuild_runtime_services.assert_called_once_with()

    def test_parent_source_failure_rebuilds_launcher_presentation(self) -> None:
        self._assert_rebuild(GreiaLauncherPresentation)

    def test_parent_source_failure_rebuilds_child_shell(self) -> None:
        self._assert_rebuild(GreiaChildShell)

    def test_parent_source_failure_rebuilds_trusted_fallback(self) -> None:
        self._assert_rebuild(TrustedGreiaLauncherPresentation)


if __name__ == "__main__":
    unittest.main()
