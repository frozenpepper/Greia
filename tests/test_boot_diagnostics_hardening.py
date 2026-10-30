from __future__ import annotations

import subprocess
import tempfile
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
                # Password login always; key login is added (OR) only when an
                # operator public key is installed.
                self.assertIn("methods=password", helper_text)
                self.assertIn('methods="publickey password"', helper_text)
                self.assertIn("AuthenticationMethods $methods", helper_text)
                self.assertIn("/etc/ssh/greia-operator-keys/greia", helper_text)
                self.assertNotIn("publickey,password", helper_text.replace(
                    "accidentally used `publickey,password`", ""))
                self.assertIn("PasswordAuthentication yes", helper_text)
                self.assertIn("KbdInteractiveAuthentication no", helper_text)
                self.assertIn("PermitRootLogin no", helper_text)
                self.assertIn("AllowUsers greia", helper_text)
                self.assertIn("passwd -S greia", helper_text)
                self.assertIn("ssh_host_ed25519_key", helper_text)
                self.assertIn("ssh-keygen -q -t ed25519", helper_text)
                self.assertIn("/usr/sbin/sshd -T", helper_text)
                self.assertIn("passwordauthentication yes", helper_text)
                self.assertIn('grep -qx "authenticationmethods $methods"', helper_text)
                self.assertIn('grep -qx "pubkeyauthentication $pubkey"', helper_text)
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
        # Assert on configuration, not on the prose of the explanatory comment.
        wired_directives = self._directives_only(wired)
        wireless_directives = self._directives_only(wireless)
        # Wired recovery networking is systemd-networkd's job and stays.
        self.assertIn("DHCP=yes", wired_directives)
        self.assertIn("MulticastDNS=yes", wired_directives)
        # Wireless recovery networking is iwd's job. The installer must still
        # start iwd and networkd, but networkd must not claim the wireless
        # link: iwd only publishes Device/Station while it holds the adapter in
        # station mode, so a networkd DHCP policy on wl* left the installer
        # unable to list or join any network on the reference Acer. The policy
        # file is retained only to declare that ownership boundary.
        self.assertIn("Unmanaged=yes", wireless_directives)
        self.assertNotIn("DHCP=yes", wireless_directives)
        self.assertNotIn("MulticastDNS=yes", wireless_directives)

    @staticmethod
    def _directives_only(path: Path) -> str:
        """Return the .network file with comments and blank lines removed."""

        return "\n".join(
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith(("#", ";"))
        )

    def test_reference_acer_syslinux_remains_observable_per_postmortem(self) -> None:
        cfg = (ROOT / "build/live-syslinux/syslinux.cfg.in").read_text(
            encoding="utf-8"
        )
        self.assertIn("DEFAULT live", cfg)
        self.assertIn("PROMPT 0", cfg)
        self.assertIn("TIMEOUT 0", cfg)
        self.assertIn("console=tty1", cfg)
        self.assertIn("panic=0", cfg)
        self.assertIn("loglevel=4", cfg)
        self.assertIn("systemd.show_status=true", cfg)
        self.assertIn("rd.systemd.show_status=true", cfg)
        self.assertNotIn("panic=30", cfg)
        self.assertNotIn("console=null", cfg)
        self.assertNotIn(" quiet ", f" {cfg} ")
        self.assertNotIn(" splash ", f" {cfg} ")
        self.assertNotIn("loglevel=0", cfg)
        self.assertNotIn("DISPLAY ", cfg)
        self.assertNotIn("clear.msg", cfg)
        self.assertNotIn("NOESCAPE", cfg)
        self.assertNotIn("NOCOMPLETE", cfg)

    def test_developer_installed_boot_is_observable_and_non_rebooting(self) -> None:
        grub = (
            ROOT / "build/overlay/etc/grub.d/10_greia_appliance"
        ).read_text(encoding="utf-8")
        self.assertNotIn('console_arg="console=null"', grub)
        self.assertIn('panic_arg="panic=0"', grub)
        self.assertIn('console_arg="console=tty1"', grub)
        self.assertIn('diagnostic_args="loglevel=4 systemd.show_status=true', grub)
        self.assertIn('visibility_args="$diagnostic_args"', grub)
        # The console policy is its own image fact, not the developer marker.
        self.assertIn("/etc/greia-os/boot-console-policy", grub)
        self.assertNotRegex(grub, r"panic=[1-9]")

    def test_boot_art_generator_preserves_colour_and_builds_safe_canvas(self) -> None:
        generator = (ROOT / "tools/generate_boot_artwork.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("canonical_full_color_frame", generator)
        self.assertIn("compose_boot_canvas", generator)
        self.assertIn("CANVAS_SIZE = (1024, 600)", generator)
        self.assertIn("MIN_SOURCE_COLOURS", generator)
        self.assertIn("GRUB_THEME", generator)
        self.assertIn('desktop-image-scale-method: "padding"', generator)
        self.assertNotIn("MedianFilter", generator)
        self.assertNotIn("_LOGO_COLOR", generator)
        self.assertNotIn("luminance > 90", generator)
        self.assertNotIn("derive_white_frame", generator)

    def test_early_renderer_fits_canvas_and_uses_its_background(self) -> None:
        renderer = (ROOT / "build/early-boot/greia-fb-splash.c").read_text(
            encoding="utf-8"
        )
        self.assertIn("background = pack_pixel", renderer)
        self.assertIn("image->rgb[0]", renderer)
        self.assertIn("dest_w = visible_w", renderer)
        self.assertIn("dest_h > visible_h", renderer)
        self.assertIn("x0 = (visible_w - dest_w) / 2u", renderer)
        self.assertIn("y0 = (visible_h - dest_h) / 2u", renderer)
        self.assertNotIn("visible_h / 12u", renderer)
        self.assertNotIn("max_h", renderer)
        self.assertNotIn("max_w", renderer)

    def test_installed_grub_uses_proportional_theme_not_raw_stretch(self) -> None:
        grub = (ROOT / "build/overlay/etc/grub.d/10_greia_appliance").read_text(
            encoding="utf-8"
        )
        theme = (ROOT / "build/overlay/boot/grub/greia-theme.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn('theme="/boot/grub/greia-theme.txt"', grub)
        self.assertIn("set theme=$theme", grub)
        self.assertNotRegex(grub, r"(?m)^\s*background_image\s")
        self.assertIn('desktop-image-scale-method: "padding"', theme)
        self.assertIn('desktop-image-h-align: "center"', theme)
        self.assertIn('desktop-image-v-align: "center"', theme)

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
        # Boot artwork generation may surround the physically proven image
        # builder, but Syslinux/FAT writer mechanics stay outside this wrapper.
        self.assertIn("generate_boot_artwork.py", legacy)
        self.assertIn("full-color-landscape-canvas-v1", legacy)
        self.assertIn("generated canonical boot source is not pixel-identical", legacy)
        self.assertIn('"$SCRIPT_DIR/build-installer-image.sh" "$PROFILE" "$OUTPUT_DIR"', legacy)
        self.assertNotIn("syslinux --install", legacy)
        self.assertNotIn("mkfs.vfat", legacy)

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

    def test_artifact_verifiers_cover_recovery_and_visual_contract(self) -> None:
        installer = (ROOT / "tools/verify-development-installer.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("live/filesystem.squashfs", installer)
        self.assertIn("payload/greia-rootfs.squashfs", installer)
        self.assertIn("etc/shadow", installer)
        self.assertIn("multi-user.target.wants/ssh.service", installer)
        self.assertIn("prepare-developer-ssh", installer)
        self.assertIn("methods=password", installer)
        self.assertIn("verify-composed-root.sh", installer)
        self.assertIn("20-greia-wired.network", installer)
        self.assertIn("25-greia-wireless.network", installer)
        self.assertIn("developer-remote", installer)
        self.assertIn("P6\\n1024 600\\n255\\n", installer)
        self.assertIn("old_duotone", installer)
        self.assertIn("boot/grub/greia-theme.txt", installer)
        self.assertIn("desktop-image-scale-method", installer)
        self.assertIn("raw GRUB background_image stretch path", installer)

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
        # The writer copies the owner-approved quiet-path display file only
        # when the selected template references it; the file is never
        # generated at write time.
        self.assertIn("build/live-syslinux/clear.msg", writer)
        self.assertIn("DISPLAY /boot/syslinux/clear", writer)
        self.assertNotIn("usb_flash_verification=PASS", writer)

        verifier = (ROOT / "tools/verify-live-usb.sh").read_text(encoding="utf-8")
        self.assertIn("read-only", verifier)
        self.assertIn("fsck.vfat -n", verifier)
        self.assertIn("cmp -s", verifier)
        self.assertIn("cmp -n 440", verifier)
        self.assertIn("usb_readback_verification=PASS", verifier)
        self.assertIn("console=tty1", verifier)
        self.assertIn("panic=0", verifier)
        self.assertIn("panic=[1-9]", verifier)
        self.assertIn("console=null", verifier)  # explicit rejection check
        self.assertIn("clear.msg", verifier)
        self.assertIn("DISPLAY ", verifier)

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


    def test_read_only_usb_verifier_accepts_only_syslinux_fat_metadata_conditions(self) -> None:
        """The read-only media verifier must not be unable to pass proven media.

        The proven Syslinux/FAT32 writer runs `syslinux --install`, which patches
        the primary FAT32 VBR without updating the backup boot sector, and
        leaves minor free-cluster/FSInfo drift. fsck.vfat reports both as
        harmless yet exits 1, so a bare `fsck.vfat -n || exit 1` made the
        verifier reject every stick the proven recipe produced.

        The repaired policy is a narrow allowlist: those two conditions may
        continue, and everything else still fails closed. fsck must stay
        read-only.
        """
        policy = ROOT / "tools/verify-live-usb-fsck-policy.sh"
        verifier = (ROOT / "tools/verify-live-usb.sh").read_text(encoding="utf-8")

        self.assertIn("verify-live-usb-fsck-policy.sh", verifier)
        self.assertIn("greia_fat_fsck_acceptable", verifier)
        # Read-only, locale-stable, and still fatal on invocation failure.
        self.assertIn("LC_ALL=C fsck.vfat -n", verifier)
        self.assertNotIn("fsck.vfat -a", verifier)
        self.assertNotIn("fsck.vfat -r", verifier)
        self.assertNotIn("fsck.vfat -w", verifier)

        # Captured verbatim from fsck.fat 4.2 on the real reference stick.
        syslinux_benign = (
            "fsck.fat 4.2 (2021-01-31)\n"
            "There are differences between boot sector and its backup.\n"
            "This is mostly harmless. Differences: (offset:original/backup)\n"
            "  3:53/6d, 4:59/6b, 5:53/66, 6:4c/73, 7:49/2e, 8:4e/66, 9:55/61, 10:58/74\n"
            "  , 90:fa/0e, 91:fc/1f, 92:31/be, 93:c9/77, 94:8e/7c, 95:d1/ac, 96:bc/22\n"
            "  , 97:76/c0, 98:7b/74, 99:52/0b, 100:06/56\n"
            "  Not automatically fixing this.\n"
            "Reclaimed 29 unused clusters (118784 bytes).\n"
            "Checking free cluster summary.\n"
            "Free cluster summary wrong (1707929 vs. really 1707958)\n"
            "  Auto-correcting.\n"
            "\n"
            "Leaving filesystem unchanged.\n"
            "/dev/sdb1: 74 files, 262200/1970158 clusters\n"
        )
        # An unrelated, genuinely dirty filesystem must still be refused.
        dirty = (
            "fsck.fat 4.2 (2021-01-31)\n"
            "Reclaimed 29 unused clusters (118784 bytes).\n"
            "Checking free cluster summary.\n"
            "Free cluster summary wrong (1707929 vs. really 1707958)\n"
            "  Auto-correcting.\n"
            "Dirty bit is set.  Fs was not properly unmounted and may be further corrupted.\n"
            "File system is dirty - Bit 8 is set in the reserved area\n"
            "There are differences between boot sector and its backup.\n"
            "This is mostly harmless. Differences: (offset:original/backup)\n"
            "  3:53/6d\n"
            "  Not automatically fixing this.\n"
            "\n"
            "Leaving filesystem unchanged.\n"
            "/dev/sdb1: 74 files, 262200/1970158 clusters\n"
        )

        cases = [
            ("clean fsck accepted", "0", "fsck.fat 4.2 (2021-01-31)\n", 0),
            (
                "syslinux fat metadata conditions may continue",
                "1",
                syslinux_benign,
                0,
            ),
            ("dirty filesystem rejected", "1", dirty, 1),
            ("fsck invocation failure rejected", "2", "", 1),
        ]
        for name, status, payload, expected in cases:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as directory:
                    sample = Path(directory) / "fsck.out"
                    sample.write_text(payload, encoding="utf-8")
                    completed = subprocess.run(
                        [
                            "bash",
                            "-c",
                            'source "$1"; greia_fat_fsck_acceptable "$2" "$3"',
                            "bash",
                            str(policy),
                            status,
                            str(sample),
                        ],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                self.assertEqual(
                    completed.returncode, expected, f"{name}: {completed.stderr}"
                )


if __name__ == "__main__":
    unittest.main()
