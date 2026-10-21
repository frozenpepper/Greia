"""Shared Greia boot-logo animation: frames, fitting, timing and skip.

The 52-frame Greia logo animation (``assets/boot/frames``) is product
presentation owned by two surfaces: the installed Shell plays it once per boot
(``greia_launcher.boot_intro``) and the live installer plays it once at start
(``greia_installer.boot_intro``). Both used to need the same asset discovery,
viewport fitting and duration-based frame selection, so those pieces live here
instead of being copied or imported across the launcher/installer boundary.

What stays with each owner: one-shot markers, boot KPIs/systemd readiness
(launcher), skip-on-input and boot-cover release (installer).

Invariants (``docs/design/GREIA_BOOT_EXPERIENCE.md`` §5 Stage D):

- the animation lasts :data:`ANIMATION_SECONDS`, then the exact final frame is
  held for :data:`FINAL_FRAME_HOLD_SECONDS`;
- frame selection is driven by elapsed monotonic time, never by sleeping a
  fixed amount per source frame, so slow hardware drops frames instead of
  stretching the sequence;
- frames and the static canvas are drawn at native pixel size, centred, never
  upscaled and never distorted; they shrink proportionally only when the
  viewport is smaller than the art (:func:`native_scale`);
  the letterbox background is fixed pure white (never sampled from art);
- fail-soft: missing or undecodable art yields no frames and boot proceeds.

Pygame is passed in by callers; this module never imports it, so renderer-free
tooling and unit tests can use the timing model directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Sequence

ANIMATION_SECONDS = 5.0
FINAL_FRAME_HOLD_SECONDS = 2.0
BACKGROUND_RGB = (255, 255, 255)

DEFAULT_FRAMES_DIR = Path("/opt/greia-os/assets/boot/frames")
_FRAME_GLOB = "frame_*.png"


def candidate_frame_directories(root: Path | None = None) -> list[Path]:
    """Ordered places the animation frames may live.

    ``GREIA_BOOT_FRAMES_DIR`` (diagnostics) first, then ``<root>`` when the
    caller knows its Greia OS root, then the installed default, then the
    repository copy for windowed/development runs.
    """

    candidates: list[Path] = []
    override = os.environ.get("GREIA_BOOT_FRAMES_DIR")
    if override:
        candidates.append(Path(override))
    if root is not None:
        candidates.append(Path(root) / "assets" / "boot" / "frames")
    candidates.append(DEFAULT_FRAMES_DIR)
    candidates.append(Path(__file__).resolve().parents[2] / "assets" / "boot" / "frames")
    return list(dict.fromkeys(candidates))


def frame_paths(directories: Sequence[Path]) -> list[Path]:
    """Sorted frame files from the first directory that has any."""

    for directory in directories:
        if directory.is_dir():
            files = sorted(directory.glob(_FRAME_GLOB), key=lambda path: path.name)
            if files:
                return files
    return []


def load_frames(
    pygame: Any,
    directories: Sequence[Path],
    *,
    prepare: Callable[[Any], Any] | None = None,
) -> list[Any]:
    """Decode every frame once, or return ``[]`` on any failure.

    ``prepare`` lets a caller convert/scale each decoded frame exactly once at
    load time (a prepared static layer), so the animation loop only blits.
    """

    # A directory whose frames fail to decode does not end the search: the
    # next candidate (e.g. the repository copy) may still be intact.
    for directory in directories:
        files = frame_paths((directory,))
        if not files:
            continue
        loaded: list[Any] = []
        try:
            for path in files:
                frame = pygame.image.load(str(path))
                loaded.append(prepare(frame) if prepare is not None else frame)
        except Exception:  # noqa: BLE001 - presentation is fail-soft by design
            continue
        if loaded:
            return loaded
    return []


def native_scale(
    art_size: tuple[int, int], screen_size: tuple[int, int]
) -> float:
    """Scale for boot art: native size, reduced only if it cannot fit.

    Boot art is never upscaled (upscaled art looks soft on larger screens);
    it shrinks proportionally only when the display is smaller than the art.
    """

    art_w, art_h = art_size
    screen_w, screen_h = screen_size
    return min(1.0, screen_w / max(1, art_w), screen_h / max(1, art_h))


def fitted_size(
    frame_size: tuple[int, int],
    screen_height: int,
    screen_width: int | None = None,
) -> tuple[int, int]:
    """Native size of a frame, scaled down only if it does not fit the screen."""

    frame_w, frame_h = frame_size
    width_limit = screen_width if screen_width is not None else 1 << 30
    scale = native_scale(frame_size, (width_limit, screen_height))
    if scale >= 1.0:
        return frame_w, frame_h
    return max(1, int(round(frame_w * scale))), max(1, int(round(frame_h * scale)))


def draw_frame(
    screen: Any,
    pygame: Any,
    frame: Any,
    *,
    background: tuple[int, int, int] = BACKGROUND_RGB,
) -> None:
    """Draw one animation frame centred at native size (shrunk only to fit)."""

    width, height = screen.get_size()
    screen.fill(background)
    target = fitted_size((frame.get_width(), frame.get_height()), height, width)
    if target != (frame.get_width(), frame.get_height()):
        try:
            scaled = pygame.transform.smoothscale(frame, target)
        except Exception:  # noqa: BLE001
            scaled = frame
    else:
        scaled = frame
    screen.blit(scaled, scaled.get_rect(center=(width // 2, height // 2)))


def draw_canvas(
    screen: Any,
    pygame: Any,
    logo: Any,
    *,
    scale: float = 1.0,
    background: tuple[int, int, int] = BACKGROUND_RGB,
) -> None:
    """Draw the static boot canvas centred at native size (shrunk only to fit)."""

    width, height = screen.get_size()
    screen.fill(background)
    base_scale = native_scale((logo.get_width(), logo.get_height()), (width, height))
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


def frame_index(
    elapsed: float,
    total_frames: int,
    animation_seconds: float = ANIMATION_SECONDS,
) -> int:
    """Frame to show ``elapsed`` seconds into the animation phase."""

    if total_frames <= 0:
        return 0
    ratio = max(0.0, min(1.0, elapsed / max(1e-9, animation_seconds)))
    return min(total_frames - 1, int(ratio * total_frames))


class IntroPhase(StrEnum):
    """Where an intro timeline is: animating, holding the last frame, or done."""

    ANIMATING = "animating"
    HOLDING = "holding"
    DONE = "done"


@dataclass(slots=True)
class IntroTimeline:
    """Duration-based intro sequencing with an explicit skip.

    Pure state: callers pass ``now`` from a monotonic clock. ``skip()`` ends the
    timeline immediately (the installer skips on any input; the launcher never
    calls it, its release UX always plays the full 5 + 2 seconds).
    """

    total_frames: int
    animation_seconds: float = ANIMATION_SECONDS
    hold_seconds: float = FINAL_FRAME_HOLD_SECONDS
    started_at: float | None = None
    skipped: bool = field(default=False)

    def start(self, now: float) -> None:
        self.started_at = float(now)

    def skip(self) -> None:
        self.skipped = True

    def phase(self, now: float) -> IntroPhase:
        if self.skipped or self.total_frames <= 0:
            return IntroPhase.DONE
        if self.started_at is None:
            return IntroPhase.ANIMATING
        elapsed = now - self.started_at
        if elapsed < self.animation_seconds:
            return IntroPhase.ANIMATING
        if elapsed < self.animation_seconds + self.hold_seconds:
            return IntroPhase.HOLDING
        return IntroPhase.DONE

    def frame(self, now: float) -> int:
        """Frame index for ``now``; the exact final frame once animation ends."""

        if self.started_at is None:
            return 0
        if self.phase(now) is not IntroPhase.ANIMATING:
            return max(0, self.total_frames - 1)
        return frame_index(now - self.started_at, self.total_frames, self.animation_seconds)
