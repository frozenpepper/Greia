from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class HardwareSupportPoolBuildScriptTests(unittest.TestCase):
    def test_pool_builder_is_download_only_and_checks_live_package_set_identity(self) -> None:
        source = (PROJECT_ROOT / "build/populate-hardware-support-pool.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("--download-only install", source)
        self.assertIn("before_packages=", source)
        self.assertIn("after_packages=", source)
        self.assertIn('[[ "$before_packages" == "$after_packages" ]]', source)
        self.assertIn("build_hardware_support_pool_manifest.py", source)
        self.assertIn("finalize_hardware_support_pool.py", source)

    def test_dependency_resolution_uses_exact_target_payload_state_not_live_status(self) -> None:
        source = (PROJECT_ROOT / "build/populate-hardware-support-pool.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("TARGET_DPKG_STATUS", source)
        self.assertIn("greia-rootfs.squashfs", source)
        self.assertIn("unsquashfs -cat", source)
        self.assertIn("var/lib/dpkg/status", source)
        self.assertIn("Dir::State::status=/tmp/greia-target-dpkg-status", source)

    def test_pool_builder_does_not_use_vendor_downloaders_or_direct_dpkg_install(self) -> None:
        source = (PROJECT_ROOT / "build/populate-hardware-support-pool.sh").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("curl ", source)
        self.assertNotIn("wget ", source)
        self.assertNotIn("dpkg -i", source)


if __name__ == "__main__":
    unittest.main()
