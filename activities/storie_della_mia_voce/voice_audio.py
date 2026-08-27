"""Storie della Mia Voce — audio playback of saved story recordings.

Saved stories are ordinary WAV blobs (16-bit signed mono PCM,
22050 Hz, written by `VoiceRecorder.stop()`). Playback uses the
standard pygame mixer so it is real audio output on the device.

The mixer is initialised once at launch; each saved scene is
played as one short `Sound` instance. Long sounds (the cap is
30 s) are well within the mixer's buffer.
"""

from __future__ import annotations

import io
import wave
from typing import Any

import pygame


class VoicePlayback:
    def __init__(self) -> None:
        self._enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=4096)
            self._enabled = True
        except Exception:
            self._enabled = False

    def play(self, wav_bytes: bytes) -> bool:
        if not self._enabled:
            return False
        if not wav_bytes:
            return False
        try:
            # Validate by re-opening the WAV header
            with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
                wf.getframerate()
                wf.getnframes()
            snd = pygame.mixer.Sound(io.BytesIO(wav_bytes))
            snd.play()
            return True
        except Exception:
            return False
