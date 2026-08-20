from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BootDiagnosticsHardeningTests(unittest.TestCase):
    def test_binary_ppm_parser_does_not_treat_raster_bytes_as_whitespace(self) -> None:
        source = (ROOT / "build/early-boot/greia-fb-splash.c").read_text(
            encoding="utf-8"
        )
        self.assertIn("file_data[offset] != '\\n'", source)
        self.assertIn("offset++;", source)
        self.assertNotIn(
            "while (offset < file_size && file_data[offset] <= ' ') offset++;",
            source,
        )
        self.assertIn("P6 raster data is binary", source)

    def test_target_and_live_installer_prepare_developer_ssh_before_validation(self) -> None:
        for overlay in ("build/overlay", "build/installer-overlay"):
            with self.subTest(overlay=overlay):
                helper = ROOT / overlay / "usr/local/lib/greia-os/prepare-developer-ssh"
                dropin = (
                    ROOT
                    / overlay
                    / "etc/systemd/system/ssh.service.d/10-greia-developer-bootstrap.conf"
                )
                self.assertTrue(helper.is_file())
                self.assertTrue(dropin.is_file())

                helper_text = helper.read_text(encoding="utf-8")
                self.assertIn("/usr/bin/ssh-keygen -A", helper_text)
                self.assertIn("developer-remote", helper_text)
                self.assertIn("AuthenticationMethods any", helper_text)
                self.assertIn("publickey,password", helper_text)

                unit = dropin.read_text(encoding="utf-8")
                self.assertIn("ExecStartPre=\n", unit)
                self.assertIn(
                    "ExecStartPre=+/bin/sh /usr/local/lib/greia-os/prepare-developer-ssh",
                    unit,
                )
                self.assertIn("ExecStartPre=/usr/sbin/sshd -t", unit)

    def test_normal_security_floor_still_disables_password_and_root_ssh(self) -> None:
        security_floor = (
            ROOT / "build/overlay/etc/ssh/sshd_config.d/00-greia-security-floor.conf"
        ).read_text(encoding="utf-8")
        self.assertIn("PasswordAuthentication no", security_floor)
        self.assertIn("KbdInteractiveAuthentication no", security_floor)
        self.assertIn("PermitRootLogin no", security_floor)
        self.assertIn("DenyUsers root", security_floor)


if __name__ == "__main__":
    unittest.main()
