"""Launcher-owned one-shot Greia boot chime.

The chime is optional presentation polish. It must never be on the boot
critical path: it starts only after the launcher has presented its first real
graphical frame, plays asynchronously, fails silently when audio is
unavailable, and plays once per machine boot (not per launcher restart).
"""

from __future__ import annotations

import os
import threading
import wave
from pathlib import Path


_ONE_SHOT_MARKER = Path("/run/greia-os/boot-chime-played")
_DEFAULT_CHIME = Path("/opt/greia-os/assets/audio/system/greia-boot-chime.wav")


def _marker_path() -> Path:
    override = os.environ.get("GREIA_BOOT_CHIME_MARKER")
    if override:
        return Path(override)
    return _ONE_SHOT_MARKER


def chime_played() -> bool:
    return _marker_path().exists()


def _mark_played() -> None:
    marker = _marker_path()
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("played\n", encoding="ascii")
    except OSError:
        pass


def _play_with_alsa(path: Path) -> bool:
    """Try aplay for the smallest footprint; returns False when unavailable."""
    import subprocess

    try:
        completed = subprocess.run(
            ["aplay", "-q", str(path)],
            check=False,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return completed.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _valid_chime(path: Path) -> bool:
    try:
        with wave.open(str(path), "rb") as handle:
            channels = handle.getnchannels()
            rate = handle.getframerate()
            duration = handle.getnframes() / max(1, rate)
            return 1 <= channels <= 2 and 0.1 <= duration <= 1.2
    except (OSError, wave.Error):
        return False


def play_boot_chime() -> None:
    """Start the one-shot boot chime in the background, fail-silently."""

    if chime_played():
        return
    if os.environ.get("GREIA_SKIP_BOOT_CHIME") == "1":
        _mark_played()
        return
    path = Path(os.environ.get("GREIA_BOOT_CHIME", str(_DEFAULT_CHIME)))
    if not path.is_file() or not _valid_chime(path):
        _mark_played()
        return

    def worker() -> None:
        try:
            _play_with_alsa(path)
        finally:
            _mark_played()

    try:
        threading.Thread(target=worker, daemon=True, name="greia-boot-chime").start()
    except Exception:  # noqa: BLE001 - never fail boot for a chime
        _mark_played()
