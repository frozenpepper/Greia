"""Launcher-owned Greia boot handoff and frame-by-frame animation intro.

This module owns the first branded frame after X/Pygame acquires a real
graphical surface and the full-height branded sequential frame animation.

Key design invariants:
- the first launcher-owned frame redraws the canonical boot canvas;
- intro timing is driven by ``time.monotonic()``, never by a fake boot timer;
- the 52-frame animation intentionally lasts 5 seconds;
- the final animation frame then remains visible for an additional 2 seconds;
- plays the sequential animation frames (222x600) full-height and centered;
- the presentation background is a fixed pure-white core colour, never sampled
  from animation-frame corner pixels, so letterboxing stays white on every
  display regardless of resolution or aspect ratio;
- plays only when a one-shot boot marker is absent under ``/run/greia-os``;
- fail-soft: any asset/decode problem is ignored and boot proceeds.

Frame discovery, viewport fitting and duration-based frame selection are
shared with the live installer through :mod:`greia_platform.boot_animation`;
this module keeps the launcher-owned one-shot marker, boot KPIs and systemd
readiness. The timing literals below must equal the shared ones (pinned by
``tests/test_installer_boot_intro.py``).
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any

from greia_platform import boot_animation
from greia_platform.boot_markers import emit_boot_marker


ANIMATION_SECONDS = 5.0
FINAL_FRAME_HOLD_SECONDS = 2.0
TARGET_INTRO_SECONDS = ANIMATION_SECONDS
MAX_INTRO_SECONDS = ANIMATION_SECONDS + FINAL_FRAME_HOLD_SECONDS
_RENDER_INTERVAL_SECONDS = 1.0 / 60.0

_ONE_SHOT_MARKER = Path("/run/greia-os/boot-intro-played")
_DEFAULT_LOGO = Path("/opt/greia-os/assets/boot/static/greia-boot-logo.png")
_DEFAULT_FRAMES_DIR = boot_animation.DEFAULT_FRAMES_DIR


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
    return boot_animation.candidate_frame_directories()


def load_animation_frames(pygame: Any) -> list[Any]:
    """Load the sequential animation frames, or an empty list on failure."""
    return boot_animation.load_frames(pygame, _candidate_frames_dirs())


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
    """Return the fixed pure-white presentation background.

    The frames are 222x600 portrait art; the code relies on letterboxing that
    must stay white on every display. Sampling a corner pixel is wrong because
    frame borders are dark and differ per resolution. White is therefore hard
    coded, independent of any image content.
    """

    return boot_animation.BACKGROUND_RGB


def _draw_canvas(
    screen: Any,
    pygame: Any,
    logo: Any,
    *,
    scale: float = 1.0,
) -> None:
    boot_animation.draw_canvas(
        screen, pygame, logo, scale=scale, background=_background_rgb(logo)
    )


def _draw_frame(
    screen: Any,
    pygame: Any,
    frame: Any,
) -> None:
    """Draw one animation frame centered on screen at full height."""
    boot_animation.draw_frame(screen, pygame, frame, background=_background_rgb(frame))


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


def _drain_intro_motion(pygame: Any) -> None:
    """Discard stale pointer-motion events queued during the intro.

    Discard set is exactly ``{MOUSEMOTION}`` and nothing else: ``QUIT``,
    ``KEYDOWN``/``KEYUP``, ``TEXTINPUT``, ``MOUSEBUTTONDOWN``/``MOUSEBUTTONUP``,
    ``MOUSEWHEEL``, ``VIDEORESIZE`` and every other queued type stay queued
    for the post-intro interactive loop. ``pygame.event.get(type)`` already
    pumps SDL internally, so this keeps the display connection responsive
    exactly like the old ``pump()`` while preventing the 7 s accumulation
    from arriving as one stale burst in the hottest worker window.
    Fail-soft by design: any event-system problem is ignored.
    """

    try:
        event_mod = getattr(pygame, "event", None)
        if event_mod is None:
            return
        get = getattr(event_mod, "get", None)
        if get is None:
            try:
                event_mod.pump()
            except Exception:  # noqa: BLE001
                pass
            return
        motion_type = getattr(pygame, "MOUSEMOTION", 4)
        try:
            get(motion_type)
            return
        except TypeError:
            pass
        except Exception:  # noqa: BLE001
            return
        # Fallback for event stand-ins whose get() takes no filter argument:
        # consume everything, then re-post every non-motion event in order.
        try:
            pending = get()
        except Exception:  # noqa: BLE001
            return
        try:
            post = getattr(event_mod, "post", None)
            if post is None:
                return
            for queued_event in pending:
                try:
                    if int(getattr(queued_event, "type", -1)) == int(motion_type):
                        continue
                except Exception:  # noqa: BLE001
                    pass
                try:
                    post(queued_event)
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            pass
    except Exception:  # noqa: BLE001 - intro remains fail-soft
        pass


def _pump_display(pygame: Any) -> None:
    """Drain stale intro motion, then pace one ~1/60 s intro frame."""
    _drain_intro_motion(pygame)
    try:
        pygame.time.wait(max(1, int(_RENDER_INTERVAL_SECONDS * 1000)))
    except Exception:  # noqa: BLE001 - intro remains fail-soft
        pass


_FIRST_FRAME_FLIPPED_EMITTED = False

_SYSTEMD_NOTIFY_BIN = "/usr/bin/systemd-notify"
_SYSTEMD_READY_STATUS = "Greia first intro frame visible"
_SYSTEMD_READY_NOTIFIED = False


def _notify_systemd_ready_once() -> None:
    """Report systemd readiness exactly once, after the first visible flip.

    Runs ``/usr/bin/systemd-notify --ready`` with a stable status string so
    the P6-PARENT ordering change can rely on the payload. Fail-soft by
    design: tests and non-systemd sessions (no ``NOTIFY_SOCKET``) return
    silently, a missing binary is skipped, and any spawn failure is ignored.
    The sent flag is set before attempting so readiness is never duplicated.
    Argument array with ``shell=False`` semantics; no sleeps, no shell.
    """
    global _SYSTEMD_READY_NOTIFIED
    if _SYSTEMD_READY_NOTIFIED:
        return
    _SYSTEMD_READY_NOTIFIED = True
    try:
        if not os.environ.get("NOTIFY_SOCKET"):
            return
        if not os.path.isfile(_SYSTEMD_NOTIFY_BIN) or not os.access(
            _SYSTEMD_NOTIFY_BIN, os.X_OK
        ):
            return
        subprocess.run(
            [
                _SYSTEMD_NOTIFY_BIN,
                "--ready",
                f"--status={_SYSTEMD_READY_STATUS}",
            ],
            check=False,
            timeout=5,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:  # noqa: BLE001 - readiness must never fail boot
        pass


def _emit_first_frame_flipped_once() -> None:
    """Emit the first-frame KPI exactly once per process.

    Called immediately after the first successful ``flip()`` that makes the
    intro frame visible. Later flips never call this function, so the flag
    only suppresses repeats across separate ``run_intro()`` calls; a failed
    flip raises before reaching this call and therefore emits nothing.
    Systemd readiness is reported here as well, so ``READY=1`` can only
    follow the actual visible frame and never precedes it.
    """
    global _FIRST_FRAME_FLIPPED_EMITTED
    if _FIRST_FRAME_FLIPPED_EMITTED:
        return
    _FIRST_FRAME_FLIPPED_EMITTED = True
    emit_boot_marker("intro_first_frame_flipped")
    _notify_systemd_ready_once()


def run_intro(
    screen: Any,
    pygame: Any,
    *,
    marker: Path | None = None,
    on_first_frame: Any | None = None,
) -> None:
    """Publish the X handoff, animate for 5s, then hold the last frame for 2s.

    ``on_first_frame`` is the explicit Phase 4 handoff: it is invoked exactly
    once on the display thread immediately after the first successful
    ``flip()`` (and its ``intro_first_frame_flipped`` marker), before the
    skip/animation decision. The intro clock is never shortened by the
    callback; preparation completion never ends the animation early. The
    callback must not perform Pygame work or mutate UI state — it only
    submits non-Pygame preparation onto the single bounded worker.
    """
    emit_boot_marker("intro_enter")
    try:
        _run_intro_guarded(screen, pygame, marker=marker, on_first_frame=on_first_frame)
    finally:
        emit_boot_marker("intro_end")


def _run_intro_guarded(
    screen: Any,
    pygame: Any,
    *,
    marker: Path | None = None,
    on_first_frame: Any | None = None,
) -> None:
    """Existing intro sequence; first-frame KPI is guarded exactly-once below."""
    draw_boot_handoff_frame(screen, pygame, progress=92)
    pygame.display.flip()
    _emit_first_frame_flipped_once()
    if on_first_frame is not None:
        on_first_frame()

    if skip_intro():
        _drain_intro_motion(pygame)
        return

    frames = load_animation_frames(pygame)
    if not frames:
        logo = load_logo()
        if logo is not None:
            _draw_canvas(screen, pygame, logo, scale=1.0)
            pygame.display.flip()
        _drain_intro_motion(pygame)
        mark_boot_intro_played()
        return

    total_frames = len(frames)
    animation_start = time.monotonic()
    try:
        while True:
            elapsed = time.monotonic() - animation_start
            if elapsed >= ANIMATION_SECONDS:
                break
            frame_idx = boot_animation.frame_index(
                elapsed, total_frames, ANIMATION_SECONDS
            )
            _draw_frame(screen, pygame, frames[frame_idx])
            pygame.display.flip()
            _pump_display(pygame)

        # The intended sequence ends on the exact final full-fidelity frame.
        _draw_frame(screen, pygame, frames[-1])
        pygame.display.flip()

        hold_start = time.monotonic()
        while time.monotonic() - hold_start < FINAL_FRAME_HOLD_SECONDS:
            _pump_display(pygame)
    finally:
        # Intro-end handoff invariant: no stale MOUSEMOTION survives past
        # intro_end into the interactive run loop (FIX-MOTION coalescing
        # assumes this handoff). Only motion is discarded here.
        _drain_intro_motion(pygame)
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
