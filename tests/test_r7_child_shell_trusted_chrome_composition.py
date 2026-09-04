from __future__ import annotations

import unittest
from unittest import mock

from greia_launcher.child_shell import ProfileVisualActivitySupervisor
from greia_launcher.trusted_chrome_supervisor import TrustedChromeActivitySupervisor
from greia_launcher.usage_limited_supervisor import UsageLimitedActivitySupervisor


class ChildShellTrustedChromeCompositionTests(unittest.TestCase):
    def test_profile_supervisor_extends_trusted_chrome_lifecycle(self) -> None:
        self.assertTrue(
            issubclass(
                ProfileVisualActivitySupervisor,
                TrustedChromeActivitySupervisor,
            )
        )
        self.assertTrue(
            issubclass(
                TrustedChromeActivitySupervisor,
                UsageLimitedActivitySupervisor,
            )
        )

    def test_profile_supervisor_forwards_controller_set(self) -> None:
        class _FakeControllerSource:
            def poll_guide_button(self) -> bool:
                return False

        source = _FakeControllerSource()
        supervisor = ProfileVisualActivitySupervisor(
            runtime_manager=unittest.mock.MagicMock(),
            storage_service=unittest.mock.MagicMock(),
            history_service=unittest.mock.MagicMock(),
            controller_set=source,
        )
        self.assertIs(supervisor._controller_set, source)


if __name__ == "__main__":
    unittest.main()
