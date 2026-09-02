"""Small Pygame PCM helpers for bounded Activity-generated sound effects.

Greia Activities may synthesize tiny feedback cues at startup, but raw PCM must
match the mixer that Pygame actually opened.  These helpers deliberately cover
only that format boundary; prerecorded speech and broader audio policy remain
owned by their existing services.
"""

from __future__ import annotations

import pygame


def current_pcm16_mixer_spec() -> tuple[int, int] | None:
    """Return ``(sample_rate, channel_count)`` for a supported active mixer."""

    spec = pygame.mixer.get_init()
    if spec is None:
        return None
    sample_rate, sample_format, channel_count = spec
    if sample_rate <= 0 or abs(sample_format) != 16 or not 1 <= channel_count <= 8:
        return None
    return (sample_rate, channel_count)


def append_mono_pcm16(raw: bytearray, sample: int, channel_count: int) -> None:
    """Append one signed 16-bit mono sample in the mixer's channel layout."""

    if not 1 <= channel_count <= 8:
        raise ValueError("Pygame PCM channel count must be between 1 and 8")
    clamped = max(-32768, min(32767, int(sample)))
    encoded = clamped.to_bytes(2, byteorder="little", signed=True)
    raw.extend(encoded * channel_count)
