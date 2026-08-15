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

    def test_hardware_pool_manifest_builder_and_inspector_are_present(self) -> None:
        self.assertTrue((PROJECT_ROOT / "tools/build_hardware_support_pool_manifest.py").is_file())
        self.assertTrue((PROJECT_ROOT / "tools/inspect_hardware_enablement.py").is_file())

    def test_hardware_enablement_architecture_decision_is_present(self) -> None:
        self.assertTrue(
            (
                PROJECT_ROOT
                / "docs/adr/0021-automatic-hardware-enablement-and-capability-discovery.md"
            ).is_file()
        )


if __name__ == "__main__":
    unittest.main()
