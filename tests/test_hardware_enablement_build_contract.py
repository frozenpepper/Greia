from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class HardwareEnablementBuildContractTests(unittest.TestCase):
    def test_live_installer_contains_debian_hardware_resolver_metadata(self) -> None:
        packages = {
            line.strip()
            for line in (PROJECT_ROOT / "build/package-sets/installer-base.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        self.assertIn("isenkram-cli", packages)


if __name__ == "__main__":
    unittest.main()
