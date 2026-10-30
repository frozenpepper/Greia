from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ImageRuntimeClosureTests(unittest.TestCase):
    def _packages(self, relative: str) -> set[str]:
        return {
            line.strip()
            for line in (ROOT / relative).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }

    def test_target_has_ext4_fsck_runtime(self) -> None:
        self.assertIn("e2fsprogs", self._packages("build/package-sets/platform-base.txt"))
        self.assertIn("e2fsprogs", self._packages("build/package-sets/installer-base.txt"))

    def test_direct_graphics_pam_session_has_logind_runtime(self) -> None:
        packages = self._packages("build/package-sets/platform-base.txt")
        self.assertIn("libpam-systemd", packages)

        service = (
            ROOT
            / "build/overlay/etc/systemd/system/greia-kmsdrm-acceptance.service"
        ).read_text(encoding="utf-8")
        self.assertIn("PAMName=login", service)
        self.assertIn("User=greiakid", service)

        builder = (ROOT / "build/lib/compose.sh").read_text(encoding="utf-8")
        useradd = next(
            line
            for line in builder.splitlines()
            if "--shell /usr/sbin/nologin --user-group --groups greiasettings,greiaprofiles,audio,netdev greiakid" in line
        )
        self.assertNotIn("video", useradd)
        self.assertNotIn("render", useradd)

    def test_early_framebuffer_boot_cover_has_no_runtime_packages(self) -> None:
        packages = self._packages("build/package-sets/boot-cover-greia-early-framebuffer.txt")
        # The Greia-owned renderer is built inside the target root; the runtime
        # package set must not drag compiler/toolchain/Plymouth into the image.
        self.assertEqual(packages, set())

    def test_no_profile_uses_plymouth_boot_cover_set(self) -> None:
        for profile in (ROOT / "build/profiles").glob("*.toml"):
            text = profile.read_text(encoding="utf-8")
            self.assertNotIn("boot-cover-plymouth", text)
            self.assertIn('cover_backend = "greia-early-framebuffer-v1"', text)

    def test_partscan_mappings_are_removed_before_loop_detach(self) -> None:
        helper = (ROOT / "build/lib/safe-cleanup.sh").read_text(encoding="utf-8")
        partx = helper.index('partx -d "$loop_device"')
        detach = helper.index('losetup -d "$loop_device"')
        self.assertLess(partx, detach)
        self.assertIn("safe_udev_settle", helper[partx:detach])

    def test_both_builders_require_partx(self) -> None:
        for relative in ("build/build-image.sh", "build/build-installer-image.sh"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            command_line = next(
                line for line in text.splitlines()
                if line.startswith(("require_commands=(", "required=("))
            )
            self.assertIn("partx", command_line.split())


if __name__ == "__main__":
    unittest.main()
