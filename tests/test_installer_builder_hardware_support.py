from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class InstallerBuilderHardwareSupportTests(unittest.TestCase):
    def test_canonical_builder_populates_pool_then_live_firmware_before_initramfs(self) -> None:
        source = (PROJECT_ROOT / "build/build-installer-image.sh").read_text(
            encoding="utf-8"
        )
        populate = source.index("populate-hardware-support-pool.sh")
        live_firmware = source.index("install-live-hardware-firmware.sh")
        initramfs = source.index("update-initramfs -u -k all")
        squash = source.index('mksquashfs "$LIVE_ROOT"')
        self.assertLess(populate, live_firmware)
        self.assertLess(live_firmware, initramfs)
        self.assertLess(initramfs, squash)

    def test_canonical_builder_records_support_pool_size_count_and_manifest_digest(self) -> None:
        source = (PROJECT_ROOT / "build/build-installer-image.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("hardware_support_pool_packages=", source)
        self.assertIn("hardware_support_pool_bytes=", source)
        self.assertIn("hardware_support_manifest_sha256=", source)
        self.assertIn("hardware-support.json", source)

    def test_canonical_builder_requires_debian_package_inspector(self) -> None:
        source = (PROJECT_ROOT / "build/build-installer-image.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("dpkg-deb", source)

    def test_installer_base_explicitly_contains_resolver_and_modinfo_dependencies(self) -> None:
        packages = {
            line.strip()
            for line in (PROJECT_ROOT / "build/package-sets/installer-base.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        self.assertTrue({"isenkram-cli", "kmod"} <= packages)


if __name__ == "__main__":
    unittest.main()
