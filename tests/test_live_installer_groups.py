"""Regression: systemd must resolve every Greia live-installer UI group.

The physical Acer USB from 2026-10-28 stopped at the Greia cover:
greia-installer.service failed at GROUP with status=216/GROUP. Unlike the
installed target, the live-minbase root had never created netdev. These
tests execute the real composition function with a disposable root and a
fake chroot groupadd; no root, disks, package installs or network required.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "build/lib/compose.sh"
INSTALLER_UNIT = ROOT / "build/installer-overlay/etc/systemd/system/greia-installer.service"
INSTALLER_PACKAGES = ROOT / "build/package-sets/installer-base.txt"
IMAGE_VERIFIER = ROOT / "build/lib/verify-composed-root.sh"


class LiveInstallerGroupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        unit_path = self.root / "etc/systemd/system/greia-installer.service"
        unit_path.parent.mkdir(parents=True)
        shutil.copy2(INSTALLER_UNIT, unit_path)
        (self.root / "usr/sbin").mkdir(parents=True)
        (self.root / "usr/sbin/groupadd").touch(mode=0o755)
        (self.root / "etc/group").write_text("nogroup:x:65534:\n", encoding="utf-8")

    def _run(self) -> subprocess.CompletedProcess[str]:
        script = r"""
source "$1"
root="$2"
chroot() {
  local rootfs="$1" program="$2" system="$3" force="$4" name="$5"
  [[ "$program" == /usr/sbin/groupadd && "$system" == --system && "$force" == --force ]] || return 50
  if ! grep -q "^$name:" "$rootfs/etc/group"; then
    printf '%s:x:999:\n' "$name" >> "$rootfs/etc/group"
  fi
}
compose_create_live_installer_groups "$root"
"""
        return subprocess.run(
            ["bash", "-c", script, "bash", str(COMPOSE), str(self.root)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_provisions_all_real_unit_groups_not_just_netdev(self) -> None:
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stderr)
        groups = {
            line.split(":", 1)[0]
            for line in (self.root / "etc/group").read_text(encoding="utf-8").splitlines()
        }
        declared = {
            name
            for line in INSTALLER_UNIT.read_text(encoding="utf-8").splitlines()
            if line.startswith("SupplementaryGroups=")
            for name in line.split("=", 1)[1].split()
        }
        self.assertIn("netdev", declared)
        self.assertLessEqual(declared, groups)
        self.assertIn("nogroup", groups)

    def test_missing_groupadd_is_explicit_build_error(self) -> None:
        (self.root / "usr/sbin/groupadd").unlink()
        result = self._run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing groupadd", result.stderr)

    def test_composer_and_artifact_verifier_enforce_identity_resolution(self) -> None:
        compose = COMPOSE.read_text(encoding="utf-8")
        self.assertIn('compose_create_live_installer_groups "$rootfs" || return 1', compose)
        self.assertIn('chroot "$rootfs" /usr/sbin/groupadd --system --force "$name"', compose)
        self.assertIn("passwd", INSTALLER_PACKAGES.read_text(encoding="utf-8").splitlines())
        verifier = IMAGE_VERIFIER.read_text(encoding="utf-8")
        self.assertIn("'s/^SupplementaryGroups=//p'", verifier)
        self.assertIn('"$root/etc/group"', verifier)
        self.assertIn("216/GROUP", verifier)


if __name__ == "__main__":
    unittest.main()
