from __future__ import annotations

import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class BootAnimationMigrationTests(unittest.TestCase):
    """Plymouth is migration debt, not the accepted Greia boot architecture.

    The Greia-owned early framebuffer cover replaces Plymouth in target and
    installer boot. The legacy 52-frame Plymouth theme may remain in the tree
    only as historical source material for the canonical artwork derivative; it
    must never be staged into a built image or wired into the builders again.
    """

    def test_legacy_theme_is_only_historical_source_material(self) -> None:
        theme_dir = PROJECT_ROOT / "build" / "overlay" / "etc" / "plymouth" / "themes" / "greia"
        # The legacy theme is permitted to remain as artwork source material.
        self.assertTrue((theme_dir / "frames" / "frame_0051.png").is_file())

    def test_builders_never_stage_or_enable_plymouth(self) -> None:
        for builder_name in ("build/build-image.sh", "build/build-installer-image.sh"):
            with self.subTest(builder=builder_name):
                builder = (PROJECT_ROOT / builder_name).read_text(encoding="utf-8")
                self.assertNotIn("plymouth-set-default-theme", builder)
                self.assertNotIn("usr/share/plymouth/themes", builder)
                self.assertNotIn("plymouth-quit.service", builder)
                self.assertNotIn("plymouth-quit-wait.service", builder)

    def test_launcher_and_installer_services_do_not_order_after_plymouth(self) -> None:
        for unit in (
            PROJECT_ROOT / "build/overlay/etc/systemd/system/greia-launcher.service",
            PROJECT_ROOT / "build/installer-overlay/etc/systemd/system/greia-installer.service",
        ):
            with self.subTest(unit=unit.name):
                text = unit.read_text(encoding="utf-8")
                self.assertNotIn("plymouth-start.service", text)
                self.assertNotIn("plymouth", text)

    def test_no_plymouth_release_binary_or_theme_in_overlays(self) -> None:
        # No Plymouth runtime theme is staged into the built overlays.
        self.assertFalse(
            (PROJECT_ROOT / "build/installer-overlay/etc/plymouth/themes/greia").exists()
        )

    def test_boot_cover_release_and_vt_prep_no_longer_drive_plymouth(self) -> None:
        release = (
            PROJECT_ROOT / "build/overlay/usr/local/lib/greia-os/release-boot-cover"
        ).read_text(encoding="utf-8")
        self.assertNotIn("plymouth", release)
        prepare = (
            PROJECT_ROOT / "build/overlay/usr/local/lib/greia-os/prepare-launcher-vt"
        ).read_text(encoding="utf-8")
        self.assertNotIn("plymouth", prepare)


if __name__ == "__main__":
    unittest.main()
