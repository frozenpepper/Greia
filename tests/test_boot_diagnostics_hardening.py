from __future__ import annotations

import subprocess
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
                self.assertGreaterEqual(text.count('"developer-remote"'), 2)

    def test_developer_remote_package_set_owns_ssh_and_mdns_dependencies(self) -> None:
        package_set = (
            ROOT / "build/package-sets/developer-remote.txt"
        ).read_text(encoding="utf-8")
        for package in ("openssh-server", "avahi-daemon", "libnss-mdns"):
            self.assertRegex(package_set, rf"(?m)^{package}$")

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

    def test_reference_acer_syslinux_remains_observable_per_postmortem(self) -> None:
        cfg = (ROOT / "build/live-syslinux/syslinux.cfg.in").read_text(
            encoding="utf-8"
        )
        self.assertIn("DEFAULT live", cfg)
        self.assertIn("PROMPT 0", cfg)
        self.assertIn("TIMEOUT 0", cfg)
        self.assertIn("console=tty1", cfg)
        self.assertIn("panic=30", cfg)
        self.assertNotIn("console=null", cfg)
        self.assertNotIn("DISPLAY ", cfg)
        self.assertNotIn("clear.msg", cfg)
        self.assertNotIn("NOESCAPE", cfg)
        self.assertNotIn("NOCOMPLETE", cfg)

    def test_boot_art_generator_stays_on_accepted_rgb565_safe_transform(self) -> None:
        generator = (ROOT / "tools/generate_boot_artwork.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("MedianFilter(3)", generator)
        self.assertIn("_LOGO_COLOR = (62, 70, 130)", generator)
        self.assertIn("luminance > 90", generator)
        self.assertIn("_WHITE = (255, 255, 255)", generator)
        self.assertNotIn("canonical_full_color_frame", generator)
        self.assertNotIn("pixel-identical to the canonical full-color frame", generator)

    def test_development_builder_routes_legacy_hardware_through_proven_front_door(self) -> None:
        wrapper = (ROOT / "tools/build-development-installer.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("developer-remote", wrapper)
        self.assertIn("*-dev", wrapper)
        self.assertIn("build-legacy-x86-sd-installer.sh", wrapper)
        self.assertIn('legacy-x86)', wrapper)
        self.assertIn("verify-development-installer.sh", wrapper)
        self.assertIn("greia-installer.local", wrapper)

        legacy = (ROOT / "build/build-legacy-x86-sd-installer.sh").read_text(
            encoding="utf-8"
        )
        # This file is the physically proven image-builder wrapper. Boot-art
        # experiments must not be inserted here without another hardware pass.
        self.assertIn('"$SCRIPT_DIR/build-installer-image.sh" "$PROFILE" "$OUTPUT_DIR"', legacy)
        self.assertNotIn("canonical-full-color-rgb", legacy)
        self.assertNotIn("pixel-identical", legacy)

    def test_active_direct_developer_builder_does_not_generate_client_keys(self) -> None:
        builder = (ROOT / "build/build-developer-image.sh").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("provision_developer_image.py", builder)
        self.assertNotIn("greiaadmin", builder)
        self.assertNotIn("greia_remote.py", builder)
        self.assertIn("verify-development-target-image.sh", builder)
        self.assertIn("developer-remote", builder)
        self.assertIn("no operator SSH key file", builder)

    def test_artifact_verifiers_cover_recovery_contract(self) -> None:
        installer = (ROOT / "tools/verify-development-installer.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("live/filesystem.squashfs", installer)
        self.assertIn("payload/pip-rootfs.squashfs", installer)
        self.assertIn("etc/shadow", installer)
        self.assertIn("multi-user.target.wants/ssh.service", installer)
        self.assertIn("prepare-developer-ssh", installer)
        self.assertIn("AuthenticationMethods password", installer)
        self.assertIn("20-greia-wired.network", installer)
        self.assertIn("25-greia-wireless.network", installer)
        self.assertIn("developer-remote", installer)

        target = (ROOT / "tools/verify-development-target-image.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("etc/shadow", target)
        self.assertIn("multi-user.target.wants/ssh.service", target)
        self.assertIn("prepare-developer-ssh", target)
        self.assertIn("ssh_host_*_key", target)
        self.assertIn("developer-remote", target)

    def test_proven_usb_writer_is_minimal_and_readback_is_separate(self) -> None:
        writer = (ROOT / "tools/build-live-usb.sh").read_text(encoding="utf-8")
        self.assertIn("syslinux --install", writer)
        self.assertIn("mbr.bin", writer)
        self.assertIn("mkfs.vfat -F 32", writer)
        self.assertIn("live-uuid", writer)
        self.assertIn("LIVE_MEDIA_ID", writer)
        self.assertNotIn("clear.msg", writer)
        self.assertNotIn("usb_flash_verification=PASS", writer)

        verifier = (ROOT / "tools/verify-live-usb.sh").read_text(encoding="utf-8")
        self.assertIn("read-only", verifier)
        self.assertIn("fsck.vfat -n", verifier)
        self.assertIn("cmp -s", verifier)
        self.assertIn("cmp -n 440", verifier)
        self.assertIn("usb_readback_verification=PASS", verifier)
        self.assertIn("console=tty1", verifier)
        self.assertIn("console=null", verifier)  # explicit rejection check
        self.assertIn("DISPLAY .*clear", verifier)

    def test_one_command_dev_workflow_builds_writes_then_verifies(self) -> None:
        workflow = (
            ROOT / "tools/build-and-flash-development-usb.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("build-development-installer.sh", workflow)
        self.assertIn("build-live-usb.sh", workflow)
        self.assertIn("verify-live-usb.sh", workflow)
        self.assertIn("source_artifact_verification=PASS", workflow)
        self.assertIn("usb_flash_readback_verification=PASS", workflow)
        self.assertIn("postmortem-proven-syslinux-fat32", workflow)
        self.assertIn("no operator SSH key is required", workflow)

    def test_new_development_shell_front_doors_are_bash_syntax_valid(self) -> None:
        scripts = (
            ROOT / "tools/build-development-installer.sh",
            ROOT / "tools/build-and-flash-development-usb.sh",
            ROOT / "tools/build-live-usb.sh",
            ROOT / "tools/verify-live-usb.sh",
            ROOT / "tools/verify-development-installer.sh",
            ROOT / "tools/verify-development-target-image.sh",
            ROOT / "build/build-developer-image.sh",
            ROOT / "build/build-legacy-x86-sd-installer.sh",
        )
        for script in scripts:
            with self.subTest(script=script.name):
                completed = subprocess.run(
                    ["bash", "-n", str(script)],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)

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
