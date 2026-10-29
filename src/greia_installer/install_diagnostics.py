"""Best-effort physical-installer error capture and USB export.

The installer image has a 64 MiB FAT32 GREIA_EFI partition, readable from
Windows/macOS. When an install fails, save a detailed report *there*, not only
in a volatile journal or in the potentially broken SYSTEM_A partition.

Nothing in this module is allowed to change the install result or hide the
original failure. A missing/write-protected/full USB falls back to journal +
volatile log and is reported as such.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

LIVE_LOG = Path("/run/greia-install-diagnostics/last-install-failure.log")
USB_DEVICE = Path("/dev/disk/by-label/GREIA_EFI")
USB_LOG = Path("greia-logs/last-install-failure.log")
LIVE_MEDIA_MARKER = Path("/run/live/medium/.disk/live-uuid")
MAX_COMMAND_OUTPUT = 128 * 1024
MAX_REPORT = 512 * 1024
USB_LOCATION = "GREIA_EFI:/greia-logs/last-install-failure.log"


def _tail(data: str | None, maximum: int = MAX_COMMAND_OUTPUT) -> str:
    value = data or ""
    return value if len(value) <= maximum else (
        f"[{len(value) - maximum} earlier characters omitted]\n" + value[-maximum:]
    )


def append_command_failure(
    command: Sequence[str], code: int, stdout: str | None, stderr: str | None
) -> None:
    """Record the real dpkg output from *both* streams, with exit status."""
    report = (
        f"\n--- FAILED COMMAND (exit {code}): {' '.join(map(str, command))} ---\n"
        f"--- stdout ---\n{_tail(stdout)}\n"
        f"--- stderr ---\n{_tail(stderr)}\n"
    )
    try:
        LIVE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with LIVE_LOG.open("a", encoding="utf-8") as handle:
            handle.write(report)
    except OSError:
        pass


def _cmdline_media_id() -> str | None:
    try:
        for part in Path("/proc/cmdline").read_text(encoding="utf-8").split():
            if part.startswith("greia.live_media_id="):
                return part.partition("=")[2].strip()
    except OSError:
        pass
    return None


def _write_usb_report(report: str) -> bool:
    """Use the installer USB's *existing* FAT32 EFI partition, not SYSTEM_A.

    Mount read-only first and check the media marker inserted during image
    assembly; only then remount rw. No partitioning, formatting or modifications
    to boot files. This runs once on failure, not during the installation.
    """
    try:
        expected = LIVE_MEDIA_MARKER.read_text(encoding="ascii").strip()
        boot_id = _cmdline_media_id()
        if not expected or not boot_id or expected != boot_id or not USB_DEVICE.exists():
            return False
        with tempfile.TemporaryDirectory(prefix="greia-log-usb-", dir="/run") as temporary:
            root = Path(temporary)
            mounted = False
            try:
                subprocess.run(
                    ["mount", "-t", "vfat", "-o", "ro,nosuid,nodev,noexec",
                     str(USB_DEVICE), str(root)],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                    timeout=20,
                )
                mounted = True
                marker = root / ".disk/live-uuid"
                if not marker.is_file() or marker.read_text(encoding="ascii").strip() != expected:
                    return False
                subprocess.run(
                    ["mount", "-o", "remount,rw", str(root)],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                    timeout=20,
                )
                target = root / USB_LOG
                target.parent.mkdir(parents=True, exist_ok=True)
                temp = target.with_name(".last-install-failure.tmp")
                try:
                    with temp.open("w", encoding="utf-8") as handle:
                        handle.write(report)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(temp, target)
                    subprocess.run(
                        ["sync", "-f", str(target)],
                        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                        timeout=20,
                    )
                finally:
                    temp.unlink(missing_ok=True)
                return True
            finally:
                if mounted:
                    subprocess.run(
                        ["umount", str(root)], check=False,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        timeout=20,
                    )
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError):
        return False


def publish_install_failure(error: BaseException) -> str | None:
    """Write a diagnostic snapshot to installer USB; return path on success.

    A previous command failure may already have written its full captured apt
    output. Keep that before the final exception and Python traceback.
    """
    try:
        details = LIVE_LOG.read_text(encoding="utf-8") if LIVE_LOG.is_file() else ""
    except OSError:
        details = ""
    report = (
        "GREIA INSTALLER FAILED\n"
        f"UTC: {datetime.now(timezone.utc).isoformat()}\n"
        f"Error: {type(error).__name__}: {error}\n\n"
        f"{_tail(details, MAX_REPORT - 16000)}\n"
        "--- Python exception ---\n"
        f"{_tail(''.join(traceback.format_exception(error)), 12000)}"
    )
    report = _tail(report, MAX_REPORT)
    try:
        LIVE_LOG.parent.mkdir(parents=True, exist_ok=True)
        LIVE_LOG.write_text(report, encoding="utf-8")
    except OSError:
        pass
    saved = _write_usb_report(report)
    try:
        import sys
        print(
            f"greia-install-diagnostics: USB={'SAVED ' + USB_LOCATION if saved else 'NOT WRITABLE'}",
            file=sys.stderr, flush=True,
        )
        if not saved:
            print(f"greia-install-diagnostics: live report {LIVE_LOG}", file=sys.stderr, flush=True)
    except (OSError, ValueError):
        pass
    return USB_LOCATION if saved else None
