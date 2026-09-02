from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
