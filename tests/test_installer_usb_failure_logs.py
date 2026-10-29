"""Installer USB failure log is retrievable without SSH or installed OS.

No actual mounts, block writes or USB access in these tests.
"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from greia_installer import install_diagnostics as diag


class InstallerUsbLoggingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.live_marker = self.root / "live-uuid"
        self.live_marker.write_text("test-greia-id\n", encoding="ascii")
        self.usb_device = self.root / "GREIA_EFI"
        self.usb_device.touch()
        self.log = self.root / "runtime" / "last-install-failure.log"

    def test_failure_report_survives_on_fat_usb_and_includes_apt_stdout(self) -> None:
        captured: list[str] = []
        ops: list[str] = []
        original_mkdtemp = tempfile.mkdtemp

        def command(argv, **_kwargs):
            ops.append(argv[0] + ":" + argv[1])
            if argv[:2] == ["mount", "-t"]:
                media = Path(argv[-1])
                (media / ".disk").mkdir()
                (media / ".disk/live-uuid").write_text("test-greia-id\n", encoding="ascii")
            elif argv[0] == "sync":
                captured.append(Path(argv[-1]).read_text(encoding="utf-8"))
            return subprocess.CompletedProcess(argv, 0, "", "")

        with (
            mock.patch.object(diag, "LIVE_MEDIA_MARKER", self.live_marker),
            mock.patch.object(diag, "USB_DEVICE", self.usb_device),
            mock.patch.object(diag, "LIVE_LOG", self.log),
            mock.patch.object(diag, "_cmdline_media_id", return_value="test-greia-id"),
            mock.patch.object(
                diag.tempfile,
                "mkdtemp",
                side_effect=lambda **_kw: original_mkdtemp(dir=self.root),
            ),
            mock.patch.object(diag.subprocess, "run", side_effect=command),
        ):
            diag.append_command_failure(
                ["chroot", "/run/greia-slots/slot-a", "apt-get", "install", "firmware-test"],
                100,
                "dpkg: error processing package firmware-test (--configure):\n"
                "post-installation script failed: Permission denied\n",
                "debconf: delaying package configuration\n",
            )
            usb = diag.publish_install_failure(RuntimeError("dpkg exited with 1"))
        self.assertEqual(usb, diag.USB_LOCATION)
        self.assertEqual(len(captured), 1)
        report = captured[0]
        self.assertIn("firmware-test (--configure)", report)
        self.assertIn("Permission denied", report)
        self.assertIn("debconf: delaying", report)
        self.assertIn("FAILED COMMAND (exit 100)", report)
        self.assertIn("RuntimeError: dpkg exited", report)
        self.assertIn("mount:-o", ops)
        self.assertIn("umount:", ops[-1])

    def test_wrong_usb_marker_never_remounts_rw_or_writes(self) -> None:
        original_mkdtemp = tempfile.mkdtemp
        commands: list[tuple[str, ...]] = []

        def command(argv, **_kwargs):
            commands.append(tuple(argv))
            if argv[:2] == ["mount", "-t"]:
                media = Path(argv[-1])
                (media / ".disk").mkdir()
                (media / ".disk/live-uuid").write_text("different-usb\n", encoding="ascii")
            return subprocess.CompletedProcess(argv, 0, "", "")

        with (
            mock.patch.object(diag, "LIVE_MEDIA_MARKER", self.live_marker),
            mock.patch.object(diag, "USB_DEVICE", self.usb_device),
            mock.patch.object(diag, "_cmdline_media_id", return_value="test-greia-id"),
            mock.patch.object(
                diag.tempfile,
                "mkdtemp",
                side_effect=lambda **_kw: original_mkdtemp(dir=self.root),
            ),
            mock.patch.object(diag.subprocess, "run", side_effect=command),
        ):
            saved = diag._write_usb_report("data")
        self.assertFalse(saved)
        self.assertFalse(any("remount,rw" in command for command in commands))
        self.assertFalse(any(command[0] == "sync" for command in commands))

    def test_missing_or_read_only_usb_does_not_hide_original_error(self) -> None:
        with (
            mock.patch.object(diag, "LIVE_MEDIA_MARKER", self.live_marker),
            mock.patch.object(diag, "USB_DEVICE", self.root / "missing-device"),
            mock.patch.object(diag, "LIVE_LOG", self.log),
            mock.patch.object(diag, "_cmdline_media_id", return_value="test-greia-id"),
        ):
            self.assertIsNone(diag.publish_install_failure(ValueError("underlying failure")))
        self.assertIn("underlying failure", self.log.read_text(encoding="utf-8"))

    def test_image_builder_places_matching_live_id_in_efi_partition(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "build/build-installer-image.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn('"$USB_ESP_MOUNT/.disk/live-uuid"', source)
        self.assertIn('"$USB_ESP_MOUNT/greia-logs"', source)
        service = (
            Path(__file__).resolve().parents[1] / "src/greia_installer/transaction_service.py"
        ).read_text(encoding="utf-8")
        self.assertIn("publish_install_failure(exc)", service)


if __name__ == "__main__":
    unittest.main()
