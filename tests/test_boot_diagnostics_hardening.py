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

    def test_target_and_live_installer_enforce_password_only_developer_ssh(self) -> None:
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
                self.assertIn("developer-remote", helper_text)
                self.assertIn("AuthenticationMethods password", helper_text)
                self.assertIn("PasswordAuthentication yes", helper_text)
                self.assertIn("KbdInteractiveAuthentication no", helper_text)
                self.assertIn("PermitRootLogin no", helper_text)
                self.assertIn("AllowUsers greia", helper_text)
                self.assertIn("passwd -S greia", helper_text)
                self.assertIn("ssh_host_ed25519_key", helper_text)
                self.assertIn("ssh-keygen -q -t ed25519", helper_text)
                self.assertIn("/usr/sbin/sshd -T", helper_text)
                self.assertIn("passwordauthentication yes", helper_text)
                self.assertIn("authenticationmethods password", helper_text)
                self.assertNotIn("AuthenticationMethods any", helper_text)

                unit = dropin.read_text(encoding="utf-8")
                self.assertIn("ExecStartPre=\n", unit)
                self.assertIn(
                    "ExecStartPre=+/bin/sh /usr/local/lib/greia-os/prepare-developer-ssh",
                    unit,
                )
                self.assertIn("ExecStartPre=/usr/sbin/sshd -t", unit)

    def test_developer_profiles_include_remote_support_in_both_artifacts(self) -> None:
        profiles = sorted((ROOT / "build/profiles").glob("*-dev.toml"))
        self.assertGreaterEqual(len(profiles), 1)
        for profile in profiles:
            with self.subTest(profile=profile.name):
                text = profile.read_text(encoding="utf-8")
                # One declaration in target_sets and one in installer_sets.
                self.assertGreaterEqual(text.count('"developer-remote"'), 2)

    def test_live_installer_explicitly_starts_recovery_network_services(self) -> None:
        service = (
            ROOT / "build/installer-overlay/etc/systemd/system/greia-installer.service"
        ).read_text(encoding="utf-8")
        for unit in (
            "iwd.service",
            "systemd-resolved.service",
            "systemd-networkd.service",
            "avahi-daemon.service",
        ):
            self.assertIn(unit, service)

        wired = ROOT / "build/installer-overlay/etc/systemd/network/20-greia-wired.network"
        wireless = ROOT / "build/installer-overlay/etc/systemd/network/25-greia-wireless.network"
        self.assertTrue(wired.is_file())
        self.assertTrue(wireless.is_file())
        self.assertIn("DHCP=yes", wired.read_text(encoding="utf-8"))
        self.assertIn("DHCP=yes", wireless.read_text(encoding="utf-8"))
        self.assertIn("MulticastDNS=yes", wired.read_text(encoding="utf-8"))
        self.assertIn("MulticastDNS=yes", wireless.read_text(encoding="utf-8"))

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
