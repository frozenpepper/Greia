from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OVERLAY = PROJECT_ROOT / "build" / "overlay"
SERVICE = OVERLAY / "etc" / "systemd" / "system" / "greia-kmsdrm-acceptance.service"
CONTROLLER = OVERLAY / "usr" / "local" / "sbin" / "greia-run-kmsdrm-acceptance"
TMPFILES = OVERLAY / "usr" / "lib" / "tmpfiles.d" / "greia-r7-maintenance.conf"
LAUNCHER_SERVICE = OVERLAY / "etc" / "systemd" / "system" / "greia-launcher.service"


class KMSDRMMaintenanceTests(unittest.TestCase):
    def test_acceptance_service_is_manual_bounded_greiakid_pam_vt_session(self) -> None:
        unit = SERVICE.read_text(encoding="utf-8")
        self.assertIn("Type=oneshot", unit)
        self.assertIn("User=greiakid", unit)
        self.assertIn("Group=greiakid", unit)
        self.assertIn("PAMName=login", unit)
        self.assertIn("TTYPath=/dev/tty1", unit)
        self.assertIn("StandardInput=tty-fail", unit)
        self.assertIn("Environment=SDL_VIDEODRIVER=kmsdrm", unit)
        self.assertIn("UnsetEnvironment=DISPLAY WAYLAND_DISPLAY XAUTHORITY", unit)
        self.assertIn("StateDirectory=greia-kmsdrm-acceptance", unit)
        self.assertIn("TimeoutStartSec=20", unit)
        self.assertIn("--acknowledge-display-takeover", unit)
        self.assertIn("/proc/[0-9]*/comm", unit)
        self.assertIn("/sys/class/tty/tty0/active", unit)
        self.assertNotIn("pgrep", unit)
        self.assertNotIn("Conflicts=greia-launcher.service", unit)
        self.assertNotIn("[Install]", unit)
        self.assertNotIn("WantedBy=", unit)

    def test_root_controller_restores_launcher_on_every_exit_path(self) -> None:
        script = CONTROLLER.read_text(encoding="utf-8")
        syntax = subprocess.run(
            ["sh", "-n", str(CONTROLLER)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        self.assertIn('if [ "$(id -u)" -ne 0 ]', script)
        self.assertIn('systemctl is-active --quiet "$launcher"', script)
        self.assertIn("trap restore_launcher EXIT", script)
        self.assertIn('systemctl stop "$launcher"', script)
        self.assertIn('systemctl start "$acceptance"', script)
        self.assertIn('systemctl start "$launcher"', script)
        self.assertIn("CRITICAL: Greia launcher did not restore", script)
        self.assertIn('payload.get("actual_video_driver") != "kmsdrm"', script)
        self.assertIn("/proc/[0-9]*/comm", script)
        self.assertIn("/sys/class/tty/tty0/active", script)
        self.assertIn("expected active VT tty1", script)
        self.assertNotIn("pgrep", script)
        self.assertNotIn("procps", script)

        trap_index = script.index("trap restore_launcher EXIT")
        stop_index = script.index('systemctl stop "$launcher"')
        self.assertLess(trap_index, stop_index)

    def test_controller_is_made_root_only_by_boot_tmpfiles_policy(self) -> None:
        policy = TMPFILES.read_text(encoding="utf-8").strip()
        self.assertEqual(
            policy,
            "z /usr/local/sbin/greia-run-kmsdrm-acceptance 0750 root root - -",
        )

    def test_acceptance_is_not_normal_boot_path_and_x_compatibility_remains(self) -> None:
        launcher = LAUNCHER_SERVICE.read_text(encoding="utf-8")
        self.assertIn("/usr/bin/xinit", launcher)
        self.assertNotIn("greia-kmsdrm-acceptance", launcher)
        self.assertFalse(
            (
                OVERLAY
                / "etc"
                / "systemd"
                / "system"
                / "graphical.target.wants"
                / "greia-kmsdrm-acceptance.service"
            ).exists()
        )

    def test_direct_boot_profile_stays_disabled_until_active_evidence_exists(self) -> None:
        self.assertFalse(
            (PROJECT_ROOT / "build" / "profiles" / "r7-qemu-amd64-direct-kms.toml").exists()
        )
        self.assertFalse(
            (PROJECT_ROOT / "build" / "package-sets" / "display-direct-kms.txt").exists()
        )


if __name__ == "__main__":
    unittest.main()
