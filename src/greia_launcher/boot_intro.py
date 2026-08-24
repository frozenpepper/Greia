"""Launcher-owned Greia boot handoff and frame-by-frame animation intro.

This module owns the first branded frame after X/Pygame acquires a real
graphical surface and the full-height branded sequential frame animation.

Key design invariants:
- the first launcher-owned frame redraws the canonical boot canvas and a
  near-complete milestone progress bar;
- intro timing is driven by ``time.monotonic()``, never by a fake boot timer or blocking sleep;
- intentional intro delay never exceeds 1.0 second (target 0.85s);
- plays the 52 sequential animation frames (222x600) at full screen height centered on screen;
- the source canvas background colour is preserved on aspect-ratio letterbox
  pixels;
- plays only when a one-shot boot marker is absent under ``/run/greia-os``;
- fail-soft: any asset/decode problem is ignored and boot proceeds.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any


MAX_INTRO_SECONDS = 2.5
TARGET_INTRO_SECONDS = 2.2

_ONE_SHOT_MARKER = Path("/run/greia-os/boot-intro-played")
_DEFAULT_LOGO = Path("/opt/greia-os/assets/boot/static/greia-boot-logo.png")
_DEFAULT_FRAMES_DIR = Path("/opt/greia-os/assets/boot/frames")


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


def _candidate_frames_dirs() -> list[Path]:
    candidates: list[Path] = []
    override = os.environ.get("GREIA_BOOT_FRAMES_DIR")
    if override:
        candidates.append(Path(override))
    candidates.append(_DEFAULT_FRAMES_DIR)
    root = Path(__file__).resolve().parents[2]
    candidates.append(root / "assets" / "boot" / "frames")
    return candidates


def load_animation_frames(pygame: Any) -> list[Any]:
    """Load the sequential 52 animation frames, or empty list on failure."""
    for directory in _candidate_frames_dirs():
        if directory.is_dir():
            files = sorted(
                directory.glob("frame_*.png"),
                key=lambda p: p.name,
            )
            if files:
                loaded = []
                try:
                    for f in files:
                        loaded.append(pygame.image.load(str(f)))
                    if loaded:
                        return loaded
                except Exception:  # noqa: BLE001
                    pass
    return []


def load_logo() -> Any | None:
    """Load the canonical boot canvas surface, or None on failure."""
    path = Path(os.environ.get("GREIA_BOOT_LOGO", str(_DEFAULT_LOGO)))
    try:
        import pygame

        if not path.is_file():
            root = Path(__file__).resolve().parents[2]
            local = root / "assets" / "boot" / "static" / "greia-boot-logo.png"
            if local.is_file():
                return pygame.image.load(str(local))
            return None
        return pygame.image.load(str(path))
    except Exception:  # noqa: BLE001 - fail-soft by design
        return None


def _background_rgb(logo: Any) -> tuple[int, int, int]:
    try:
        pixel = logo.get_at((0, 0))
        return (int(pixel[0]), int(pixel[1]), int(pixel[2]))
    except Exception:  # noqa: BLE001
        return (255, 255, 255)


def _draw_canvas(
    screen: Any,
    pygame: Any,
    logo: Any,
    *,
    scale: float = 1.0,
) -> None:
    width, height = screen.get_size()
    screen.fill(_background_rgb(logo))
    base_scale = min(width / max(1, logo.get_width()), height / max(1, logo.get_height()))
    target_scale = max(0.01, base_scale * scale)
    logo_w = max(1, int(round(logo.get_width() * target_scale)))
    logo_h = max(1, int(round(logo.get_height() * target_scale)))
    try:
        if logo_w == logo.get_width() and logo_h == logo.get_height():
            scaled = logo
        else:
            scaled = pygame.transform.smoothscale(logo, (logo_w, logo_h))
    except Exception:  # noqa: BLE001
        scaled = logo
    screen.blit(scaled, scaled.get_rect(center=(width // 2, height // 2)))


def _draw_frame(
    screen: Any,
    pygame: Any,
    frame: Any,
) -> None:
    """Draw one animation frame centered on screen at full height."""
    width, height = screen.get_size()
    screen.fill(_background_rgb(frame))
    frame_w = frame.get_width()
    frame_h = frame.get_height()
    if frame_h != height:
        scale = height / max(1, frame_h)
        target_w = max(1, int(round(frame_w * scale)))
        try:
            scaled = pygame.transform.smoothscale(frame, (target_w, height))
        except Exception:  # noqa: BLE001
            scaled = frame
    else:
        scaled = frame
    rect = scaled.get_rect(center=(width // 2, height // 2))
    screen.blit(scaled, rect)


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
        screen.fill(_background_rgb(logo))
        return False
    _draw_canvas(screen, pygame, logo, scale=1.0)
    return True


def run_intro(screen: Any, pygame: Any, *, marker: Path | None = None) -> None:
    """Publish the X handoff frame, then play the sequential frame animation."""
    draw_boot_handoff_frame(screen, pygame, progress=92)
    pygame.display.flip()

    if skip_intro():
        return

    frames = load_animation_frames(pygame)
    if not frames:
        logo = load_logo()
        if logo is not None:
            _draw_canvas(screen, pygame, logo, scale=1.0)
            pygame.display.flip()
        mark_boot_intro_played()
        return

    total_frames = len(frames)
    start = time.monotonic()
    try:
        while True:
            elapsed = time.monotonic() - start
            if elapsed >= MAX_INTRO_SECONDS:
                break
            ratio = min(1.0, elapsed / TARGET_INTRO_SECONDS)
            frame_idx = min(total_frames - 1, int(ratio * total_frames))
            _draw_frame(screen, pygame, frames[frame_idx])
            pygame.display.flip()
            if elapsed + (1.0 / 60.0) >= MAX_INTRO_SECONDS or ratio >= 1.0:
                break
            pygame.time.wait(max(1, int((1.0 / 60.0) * 1000)))
        # Ensure the final full-fidelity frame is displayed
        _draw_frame(screen, pygame, frames[-1])
        pygame.display.flip()
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
    """Render one intro frame preserving the canonical canvas background."""
    if scale is None:
        effective_scale = float(width_or_scale)
    else:
        effective_scale = float(scale)
    _draw_canvas(screen, pygame, logo, scale=effective_scale)

