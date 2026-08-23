from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_platform.boot_contract import (
    GrubContractError,
    kernel_command_lines,
    validate_grub_config,
    validate_grub_text,
)
from greia_platform.grub_security import RECOVERY_USER


GOOD_RELEASE_LINE = (
    "linux /vmlinuz root=UUID=12345678-1234-5678-9abc-def012345678 ro "
    "quiet splash loglevel=0 console=null panic=5 "
    "systemd.show_status=false rd.systemd.show_status=false "
    "systemd.crash_shell=no systemd.crash_chvt=0 "
    "udev.log_priority=3 vt.global_cursor_default=0 consoleblank=0"
)
GOOD_LINE = GOOD_RELEASE_LINE

GOOD_DEVELOPER_LINE = (
    "linux /vmlinuz root=UUID=12345678-1234-5678-9abc-def012345678 ro "
    "loglevel=4 console=tty1 panic=0 "
    "systemd.show_status=true rd.systemd.show_status=true "
    "systemd.crash_shell=no systemd.crash_chvt=0 "
    "udev.log_priority=4 vt.global_cursor_default=1 consoleblank=0"
)
AUTH = (
    'set superusers="greia-recovery"\n'
    "export superusers\n"
    "password_pbkdf2 greia-recovery grub.pbkdf2.sha512.10000.ABCD1234\n"
)


def config(line: str = GOOD_LINE, *, unrestricted: bool = True) -> str:
    permission = " --unrestricted" if unrestricted else ""
    return (
        AUTH
        + f"menuentry 'Greia OS'{permission} --id greia-os {{\n"
        + f"  {line}\n"
        + "  initrd /initrd.img\n"
        + "}\n"
    )


class BootContractTests(unittest.TestCase):
    def test_accepts_single_authenticated_unrestricted_appliance_entry(self) -> None:
        entries = validate_grub_text(config())
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].kernel_path, "/vmlinuz")

    def test_developer_mode_keeps_boot_observable(self) -> None:
        # Developer/test builds must keep the boot visible: a kernel panic
        # prints to tty1 and does not auto-reboot (panic=0) so failure state
        # remains observable. Normal/release builds stay fully silent and consoleless.
        entries = validate_grub_text(config(GOOD_DEVELOPER_LINE), developer=True)
        self.assertEqual(len(entries), 1)
        # The release consoleless line must NOT validate as developer mode.
        with self.assertRaises(GrubContractError):
            validate_grub_text(config(GOOD_RELEASE_LINE), developer=True)
        # And the dev line must NOT validate as a normal (release) build.
        with self.assertRaises(GrubContractError):
            validate_grub_text(config(GOOD_DEVELOPER_LINE))

    def test_developer_mode_rejects_conflicting_or_stale_arguments(self) -> None:
        for bad_arg, good_arg in (
            ("panic=30", "panic=0"),
            ("panic=5", "panic=0"),
            ("console=null", "console=tty1"),
            ("quiet", None),
            ("splash", None),
            ("systemd.show_status=false", "systemd.show_status=true"),
            ("rd.systemd.show_status=false", "rd.systemd.show_status=true"),
            ("loglevel=0", "loglevel=4"),
        ):
            with self.subTest(bad_arg=bad_arg):
                if good_arg:
                    bad_line = GOOD_DEVELOPER_LINE.replace(good_arg, bad_arg)
                else:
                    bad_line = GOOD_DEVELOPER_LINE + f" {bad_arg}"
                with self.assertRaises(GrubContractError):
                    validate_grub_text(config(bad_line), developer=True)

    def test_developer_marker_flips_appliance_grub_args(self) -> None:
        script_path = (
            Path(__file__).resolve().parents[1]
            / "build"
            / "overlay"
            / "etc"
            / "grub.d"
            / "10_greia_appliance"
        )
        script = script_path.read_text(encoding="utf-8")
        self.assertIn("developer-remote", script)
        self.assertIn('console_arg="console=null"', script)
        self.assertIn('panic_arg="panic=5"', script)
        self.assertIn('console_arg="console=tty1"', script)
        self.assertIn('panic_arg="panic=0"', script)
        self.assertIn("loglevel=4", script)
        self.assertIn("systemd.show_status=true", script)
        self.assertIn("rd.systemd.show_status=true", script)
        self.assertNotIn("panic=30", script)

    def test_checked_in_grub_auth_generator_matches_recovery_identity(self) -> None:
        script_path = (
            Path(__file__).resolve().parents[1]
            / "build"
            / "overlay"
            / "etc"
            / "grub.d"
            / "01_greia_auth"
        )
        script = script_path.read_text(encoding="utf-8")
        self.assertIn(f'set superusers="{RECOVERY_USER}"', script)
        self.assertIn(f"password_pbkdf2 {RECOVERY_USER} $hash", script)
        self.assertNotIn("pip-recovery", script)

    def test_rejects_an_extra_console(self) -> None:
        with self.assertRaisesRegex(GrubContractError, "console=null"):
            validate_grub_text(config(GOOD_LINE + " console=tty0"))

    def test_rejects_missing_auth_or_locked_normal_entry(self) -> None:
        with self.assertRaisesRegex(GrubContractError, "superuser"):
            validate_grub_text(config().replace(AUTH, ""))
        with self.assertRaisesRegex(GrubContractError, "--unrestricted"):
            validate_grub_text(config(unrestricted=False))

    def test_rejects_multiple_entries_and_submenus(self) -> None:
        with self.assertRaisesRegex(GrubContractError, "exactly one"):
            validate_grub_text(config() + config())
        with self.assertRaisesRegex(GrubContractError, "submenus"):
            validate_grub_text(config().replace("menuentry", "submenu", 1))

    def test_rejects_initramfs_shell_and_text_console_paths(self) -> None:
        for argument in (
            "break=premount",
            "rd.break",
            "debug=vc",
            "init=/bin/sh",
            "single",
            "systemd.unit=rescue.target",
            "rd.systemd.unit=emergency.target",
            "systemd.debug_shell=1",
            "rd.systemd.debug_shell=1",
            "systemd.run=/bin/sh",
            "rd.systemd.run=/bin/sh",
            "systemd.wants=debug-shell.service",
            "rd.systemd.wants=debug-shell.service",
            "earlycon=uart8250,io,0x3f8",
            "earlyprintk=vga",
            "ignore_loglevel",
            "plymouth.enable=0",
            "systemd.confirm_spawn=1",
            "systemd.log_target=console",
        ):
            with self.subTest(argument=argument):
                with self.assertRaises(GrubContractError):
                    validate_grub_text(config(GOOD_LINE + f" {argument}"))

    def test_rejects_recovery_menu_even_when_kernel_line_is_quiet(self) -> None:
        with self.assertRaisesRegex(GrubContractError, "recovery-mode"):
            validate_grub_text(config().replace("Greia OS", "Recovery mode"))

    def test_rejects_missing_or_conflicting_silent_arguments(self) -> None:
        for required in (
            "panic=5",
            "quiet",
            "splash",
            "systemd.show_status=false",
            "udev.log_priority=3",
            "consoleblank=0",
        ):
            with self.subTest(required=required):
                with self.assertRaises(GrubContractError):
                    validate_grub_text(config(GOOD_LINE.replace(f" {required}", "")))
        with self.assertRaises(GrubContractError):
            validate_grub_text(config(GOOD_LINE + " systemd.show_status=true"))

    def test_live_installer_requires_bounded_uuid_matched_nonpersistent_boot(self) -> None:
        media_id = "4f6fc2a3-578e-4af1-bf48-8b6eab7c72d9"
        live_args = (
            GOOD_LINE
            + " boot=live components live-media-path=/live"
            + " live-media-timeout=15 nopersistence noeject silent overlay-size=128M"
            + f" greia.live_media_id={media_id}"
        )
        validate_grub_text(config(live_args), live_installer=True)
        for required in (
            "greia.live_media_id",
            "nopersistence",
            "silent",
            "overlay-size=128M",
        ):
            with self.subTest(required=required):
                token = (
                    f" greia.live_media_id={media_id}"
                    if required == "greia.live_media_id"
                    else f" {required}"
                )
                with self.assertRaisesRegex(GrubContractError, required.split("=")[0]):
                    validate_grub_text(
                        config(live_args.replace(token, "")),
                        live_installer=True,
                    )

    def test_live_installer_rejects_bad_or_bypassed_media_identity(self) -> None:
        base = (
            GOOD_LINE
            + " boot=live components live-media-path=/live live-media-timeout=15"
            + " nopersistence noeject silent overlay-size=128M"
        )
        for bad in (
            "greia.live_media_id=not-a-uuid",
            "greia.live_media_id=4F6FC2A3-578E-4AF1-BF48-8B6EAB7C72D9",
            "live-media=removable greia.live_media_id=4f6fc2a3-578e-4af1-bf48-8b6eab7c72d9",
            "live-media-uuid=aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee greia.live_media_id=4f6fc2a3-578e-4af1-bf48-8b6eab7c72d9",
            "ignore_uuid greia.live_media_id=4f6fc2a3-578e-4af1-bf48-8b6eab7c72d9",
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(GrubContractError):
                    validate_grub_text(config(base + " " + bad), live_installer=True)

    def test_live_installer_rejects_conflicting_duplicate_live_values(self) -> None:
        media_id = "4f6fc2a3-578e-4af1-bf48-8b6eab7c72d9"
        live_args = (
            GOOD_LINE
            + " boot=live components live-media-path=/live live-media-timeout=15"
            + " nopersistence noeject silent overlay-size=128M"
            + f" greia.live_media_id={media_id}"
        )
        for duplicate in (
            "boot=local",
            "live-media-path=/other",
            "live-media-timeout=1",
            "overlay-size=512M",
        ):
            with self.subTest(duplicate=duplicate):
                with self.assertRaises(GrubContractError):
                    validate_grub_text(
                        config(live_args + " " + duplicate),
                        live_installer=True,
                    )

    def test_file_validator_and_parser_handle_generated_indentation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "grub.cfg"
            path.write_text(config().replace("  linux", "\tlinux"), encoding="utf-8")
            entries = validate_grub_config(path)
            self.assertEqual(entries, kernel_command_lines(path.read_text()))


if __name__ == "__main__":
    unittest.main()
