"""One-shot, fail-silent Greia boot chime player shared by Shell and installer.

The chime is optional presentation polish (``GREIA_BOOT_EXPERIENCE.md`` §8): it
starts only after a real graphical frame, plays asynchronously through the
smallest available player (``aplay``), never changes volume settings, fails
silently when audio is unavailable, and plays once per machine boot. The
launcher (``greia_launcher.boot_chime``) and the live installer
(``greia_installer.boot_intro``) each own their own marker path and asset
location; the player itself lives here so it is not copied.
"""

from __future__ import annotations

import subprocess
import threading
import wave
from dataclasses import dataclass
from pathlib import Path


def play_with_alsa(path: Path) -> bool:
    """Play ``path`` with ``aplay``; ``False`` when no player/device works."""

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


def valid_chime(path: Path) -> bool:
    """Only a short (0.1-1.2 s) mono/stereo WAV is accepted as the chime."""

    try:
        with wave.open(str(path), "rb") as handle:
            channels = handle.getnchannels()
            rate = handle.getframerate()
            duration = handle.getnframes() / max(1, rate)
            return 1 <= channels <= 2 and 0.1 <= duration <= 1.2
    except (OSError, wave.Error):
        return False


@dataclass(frozen=True, slots=True)
class OneShotChime:
    """A chime that plays at most once while ``marker`` exists (per boot).

    ``marker`` belongs under a tmpfs runtime directory (``/run/...``) so it
    disappears at reboot. Every outcome, including "no audio", writes the
    marker, so a missing sound device is probed once rather than retried.
    """

    path: Path
    marker: Path

    def played(self) -> bool:
        return self.marker.exists()

    def mark_played(self) -> None:
        try:
            self.marker.parent.mkdir(parents=True, exist_ok=True)
            self.marker.write_text("played\n", encoding="ascii")
        except OSError:
            pass

    def play(self, *, skip: bool = False) -> bool:
        """Start playback in the background; return whether a thread started."""

        if self.played():
            return False
        if skip or not self.path.is_file() or not valid_chime(self.path):
            self.mark_played()
            return False

        def worker() -> None:
            try:
                play_with_alsa(self.path)
            finally:
                self.mark_played()

        try:
            threading.Thread(target=worker, daemon=True, name="greia-boot-chime").start()
        except Exception:  # noqa: BLE001 - never fail boot for a chime
            self.mark_played()
            return False
        return True
