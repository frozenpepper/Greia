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

    def test_live_firmware_restores_full_apt_lists_before_autoclean(self) -> None:
        # Session 04 repair: the local-pool-only update left the live root
        # seeing just the frozen pool, so the later klibc-toolchain install
        # failed with "no installation candidate" and autoclean wiped the
        # shared host .deb cache. The override must be removed and the
        # configured archives re-updated before autoclean runs.
        source = (PROJECT_ROOT / "build/install-live-hardware-firmware.sh").read_text(
            encoding="utf-8"
        )
        local_install = source.index('"${firmware_packages[@]}"')
        restore_update = source.index('chroot "$LIVE_ROOT" apt-get update')
        autoclean = source.index('chroot "$LIVE_ROOT" apt-get autoclean')
        self.assertLess(local_install, restore_update)
        self.assertLess(restore_update, autoclean)
        self.assertIn('rm -f "$source_path"', source)

    def test_framebuffer_toolchain_owns_apt_list_state(self) -> None:
        # The klibc-toolchain install must not assume whatever ran before
        # left main-archive lists intact: update first, then install.
        engine = (PROJECT_ROOT / "build/lib/compose.sh").read_text(encoding="utf-8")
        framebuffer = engine.index("compose_build_early_framebuffer()")
        update = engine.index(
            'apt-get "${APT_ACQUIRE_OPTIONS[@]}" update', framebuffer
        )
        install = engine.index("install -y --no-install-recommends libklibc-dev gcc")
        self.assertLess(update, install)

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
