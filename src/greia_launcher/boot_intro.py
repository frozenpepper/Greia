"""Launcher-owned Greia boot handoff and short intro.

This module owns the first frame after X/Pygame acquires a real graphical
surface and the short branded intro that follows it. It is deliberately small
and bounded:

- the first X frame redraws the canonical boot canvas before the raw framebuffer
  cover is released, avoiding an uninitialized/black handoff;
- the first X frame carries a near-complete milestone progress bar;
- intro timing is driven by ``time.monotonic()``, never by a fake boot timer;
- intentional intro delay never exceeds 1.0 second;
- the source canvas background colour is preserved on aspect-ratio letterbox
  pixels instead of reintroducing the historical white-frame assumption;
- plays only when a one-shot boot marker is absent under ``/run/greia-os``;
- fail-soft: any asset/decode problem is ignored and boot proceeds;
- does not read from ``/usr/share/plymouth``.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any


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
    """Load the canonical boot canvas surface, or None on failure."""
    path = Path(os.environ.get("GREIA_BOOT_LOGO", str(_DEFAULT_LOGO)))
    try:
        import pygame

        if not path.is_file():
            return None
        return pygame.image.load(str(path))
    except Exception:  # noqa: BLE001 - fail-soft by design
        return None


def _background_rgb(logo: Any) -> tuple[int, int, int]:
    try:
        pixel = logo.get_at((0, 0))
        return (int(pixel[0]), int(pixel[1]), int(pixel[2]))
    except Exception:  # noqa: BLE001
        return (13, 30, 60)


def _draw_canvas(
    screen: Any,
    pygame: Any,
    logo: Any,
    *,
    scale: float,
) -> None:
    width, height = screen.get_size()
    screen.fill(_background_rgb(logo))
    base_scale = min(width / max(1, logo.get_width()), height / max(1, logo.get_height()))
    target_scale = max(0.01, base_scale * scale)
    logo_w = max(1, int(round(logo.get_width() * target_scale)))
    logo_h = max(1, int(round(logo.get_height() * target_scale)))
    try:
        scaled = pygame.transform.smoothscale(logo, (logo_w, logo_h))
    except Exception:  # noqa: BLE001
        return
    screen.blit(scaled, scaled.get_rect(center=(width // 2, height // 2)))


def _draw_progress_bar(screen: Any, pygame: Any, progress: int) -> None:
    width, height = screen.get_size()
    progress = max(0, min(100, int(progress)))
    bar_width = max(120, int(round(width * 0.52)))
    bar_width = min(width, bar_width)
    bar_height = max(8, min(18, height // 48))
    border = 2 if bar_height >= 12 else 1
    x = (width - bar_width) // 2
    y = min(height - bar_height, int(round(height * 0.88)))
    outer = pygame.Rect(x, y, bar_width, bar_height)
    inner = pygame.Rect(
        x + border,
        y + border,
        max(1, bar_width - border * 2),
        max(1, bar_height - border * 2),
    )
    pygame.draw.rect(screen, (87, 66, 45), outer)
    pygame.draw.rect(screen, (255, 247, 226), inner)
    filled = int(round(inner.width * progress / 100.0))
    if filled > 0:
        pygame.draw.rect(
            screen,
            (255, 194, 52),
            pygame.Rect(inner.x, inner.y, min(inner.width, filled), inner.height),
        )


def draw_boot_handoff_frame(screen: Any, pygame: Any, *, progress: int = 92) -> bool:
    """Draw the first X-owned frame and return whether canonical art was available."""
    logo = load_logo()
    if logo is None:
        # Avoid an uninitialized surface even if the asset is unexpectedly absent.
        screen.fill((13, 30, 60))
        _draw_progress_bar(screen, pygame, progress)
        return False
    _draw_canvas(screen, pygame, logo, scale=1.0)
    _draw_progress_bar(screen, pygame, progress)
    return True


def run_intro(screen: Any, pygame: Any, *, marker: Path | None = None) -> None:
    """Present the one-shot branded intro if it has not already played."""
    if skip_intro():
        return
    logo = load_logo()
    if logo is None:
        mark_boot_intro_played()
        return

    start = time.monotonic()
    try:
        while True:
            elapsed = time.monotonic() - start
            if elapsed >= MAX_INTRO_SECONDS:
                break
            progress = min(1.0, elapsed / TARGET_INTRO_SECONDS)
            scale = 0.82 + 0.18 * progress
            draw_intro_frame(screen, pygame, logo, scale)
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
    width_or_scale: int | float,
    height: int | None = None,
    scale: float | None = None,
) -> None:
    """Render one intro frame while preserving the canonical canvas background.

    The compatibility-shaped signature accepts the historical
    ``(width, height, scale)`` call form as well as the new ``(scale,)`` form.
    """
    if scale is None:
        effective_scale = float(width_or_scale)
    else:
        effective_scale = float(scale)
    _draw_canvas(screen, pygame, logo, scale=effective_scale)
