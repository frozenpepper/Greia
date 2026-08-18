"""Launcher-owned Greia boot intro.

This module renders the short branded intro that plays once per machine boot
between the early framebuffer/GRUB white frame and the profile picker. It is
deliberately small and bounded:

- driven by ``time.monotonic()`` elapsed time, never per-frame ``sleep()``;
- hard product maximum of 1.0 second of intentional delay before the caller
  proceeds to the profile picker (target 0.75-0.95 s);
- plays only when a one-shot boot marker is absent under ``/run/greia-os``;
- fail-soft: any asset/decode problem is ignored and the intro is skipped;
- does not read from ``/usr/share/plymouth``.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any


# Hard product maximum: never exceed this intentional delay before the profile
# picker is interactive. 0.75-0.95 s is the design target.
MAX_INTRO_SECONDS = 1.0
TARGET_INTRO_SECONDS = 0.85

_ONE_SHOT_MARKER = Path("/run/greia-os/boot-intro-played")
_DEFAULT_LOGO = Path("/opt/greia-os/assets/boot/static/greia-boot-logo.png")


def _boot_marker() -> Path:
    override = os.environ.get("GREIA_BOOT_INTRO_MARKER")
    if override:
        return Path(override)
    return _ONE_SHOT_MARKER


def boot_intro_played() -> bool:
    return _boot_marker().exists()


def mark_boot_intro_played() -> None:
    marker = _boot_marker()
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("played\n", encoding="ascii")
        try:
            os.chmod(marker, 0o660)
        except OSError:
            pass
    except OSError:
        pass


def skip_intro() -> bool:
    """Return True when the intro must be skipped (development/diagnostics)."""
    if os.environ.get("GREIA_SKIP_BOOT_INTRO") == "1":
        return True
    if os.environ.get("GREIA_SKIP_BOOT_HANDOFF") == "1":
        return True
    return boot_intro_played()


def load_logo() -> Any | None:
    """Load and cache the canonical boot logo surface, or None on failure."""
    path = Path(os.environ.get("GREIA_BOOT_LOGO", str(_DEFAULT_LOGO)))
    try:
        import pygame

        if not path.is_file():
            return None
        return pygame.image.load(str(path))
    except Exception:  # noqa: BLE001 - fail-soft by design
        return None


def run_intro(screen: Any, pygame: Any, *, marker: Path | None = None) -> None:
    """Present the one-shot branded intro if it has not already played.

    Returns immediately (without blocking) if the intro is disabled, already
    played, or an asset cannot be loaded. On success it drives a short
    scale/settle animation from monotonic elapsed time and then returns so the
    caller can present the profile picker.
    """

    if skip_intro():
        return
    logo = load_logo()
    if logo is None:
        mark_boot_intro_played()
        return

    start = time.monotonic()
    width, height = screen.get_size()
    try:
        while True:
            elapsed = time.monotonic() - start
            if elapsed >= MAX_INTRO_SECONDS:
                break
            # Gentle scale-in to ~1.0 with a small settle. Monotonic time
            # selects the pose; frames are dropped on slow machines.
            progress = min(1.0, elapsed / TARGET_INTRO_SECONDS)
            scale = 0.82 + 0.18 * progress
            draw_intro_frame(screen, pygame, logo, width, height, scale)
            pygame.display.flip()
            if elapsed + (1.0 / 60.0) >= MAX_INTRO_SECONDS:
                break
            pygame.time.wait(max(1, int((1.0 / 60.0) * 1000)))
    finally:
        mark_boot_intro_played()


def draw_intro_frame(
    screen: Any,
    pygame: Any,
    logo: Any,
    width: int,
    height: int,
    scale: float,
) -> None:
    """Render one intro frame: white background with the scaled logo centered."""

    screen.fill((255, 255, 255))
    logo_w = int(logo.get_width() * scale)
    logo_h = int(logo.get_height() * scale)
    if logo_w > width:
        logo_h = int(logo_h * width / logo_w)
        logo_w = width
    if logo_h > height:
        logo_w = int(logo_w * height / logo_h)
        logo_h = height
    try:
        scaled = pygame.transform.smoothscale(logo, (max(1, logo_w), max(1, logo_h)))
    except Exception:  # noqa: BLE001
        return
    screen.blit(scaled, scaled.get_rect(center=(width // 2, height // 2)))
