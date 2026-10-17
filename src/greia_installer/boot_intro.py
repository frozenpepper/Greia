"""Installer start-up Greia logo animation (skippable by any input).

The installed Shell greets every boot with the 52-frame Greia logo animation;
the live installer used to jump from the static early-boot splash straight to
the language screen. This plays the same animation at installer start through
the shared :mod:`greia_platform.boot_animation` (no copy of the launcher code
and no import across the launcher boundary), then hands the same display to
the language-first screen.

Sequence::

    static boot canvas (continues the framebuffer splash) → first flip
      → boot cover released (``on_first_frame``)
      → 5 s animation → 2 s hold on the exact final frame → chime
      → language screen

Differences from the Shell intro, all deliberate:

- **skippable**: a parent who has seen it presses any key, button, touch or
  controller button and goes straight on; the skipping input is consumed so
  it never also chooses a language;
- **once per boot** through its own marker under ``/run/greia-installer``
  (the installer's runtime directory, writable by its unprivileged user), so a
  restarted installer service does not replay it;
- **prepared frames**: each frame is converted to the display format and
  scaled to the viewport height once at load time; the loop only blits, and
  it only flips when the frame index actually changes.

Everything is fail-soft: no frames (the live image may not stage them), a
decode error or a missing audio device simply skips that part.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Sequence

from greia_platform import boot_animation
from greia_platform.boot_chime import OneShotChime
from greia_platform.boot_logo import canonical_boot_logo

DEFAULT_MARKER = Path("/run/greia-installer/intro-played")
DEFAULT_CHIME_MARKER = Path("/run/greia-installer/boot-chime-played")
_CHIME_RELATIVE = Path("assets/audio/system/greia-boot-chime.wav")
_POLL_MILLISECONDS = 16

#: Input that skips the intro. Motion and key/button *release* never skip.
_SKIP_EVENT_NAMES = (
    "KEYDOWN",
    "MOUSEBUTTONDOWN",
    "FINGERDOWN",
    "JOYBUTTONDOWN",
    "CONTROLLERBUTTONDOWN",
    "QUIT",
)


class IntroOutcome(StrEnum):
    """How the installer intro ended."""

    PLAYED = "played"
    SKIPPED = "skipped"
    ALREADY_PLAYED = "already-played"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"


def _env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value) if value else default


@dataclass(slots=True)
class InstallerIntro:
    """Owns one play of the installer start-up animation.

    ``root`` is the Greia OS root (``/opt/greia-os`` on the live image, the
    repository in demo runs). ``clock`` and ``frames_loader`` are injectable so
    sequencing and skip can be tested without real art or real time.
    """

    root: Path
    marker: Path = DEFAULT_MARKER
    chime: OneShotChime | None = None
    clock: Callable[[], float] = time.monotonic
    frames_loader: Callable[[Any, Callable[[Any], Any]], Sequence[Any]] | None = None
    animation_seconds: float = boot_animation.ANIMATION_SECONDS
    hold_seconds: float = boot_animation.FINAL_FRAME_HOLD_SECONDS

    @classmethod
    def for_root(cls, root: Path) -> "InstallerIntro":
        return cls(
            root=Path(root),
            marker=_env_path("GREIA_INSTALLER_INTRO_MARKER", DEFAULT_MARKER),
            chime=OneShotChime(
                path=_env_path("GREIA_BOOT_CHIME", Path(root) / _CHIME_RELATIVE),
                marker=_env_path("GREIA_INSTALLER_CHIME_MARKER", DEFAULT_CHIME_MARKER),
            ),
        )

    # -- policy ---------------------------------------------------------------

    def disabled(self) -> bool:
        return os.environ.get("GREIA_SKIP_BOOT_INTRO") == "1"

    def already_played(self) -> bool:
        return self.marker.exists()

    def _mark_played(self) -> None:
        try:
            self.marker.parent.mkdir(parents=True, exist_ok=True)
            self.marker.write_text("played\n", encoding="ascii")
        except OSError:
            pass

    # -- drawing --------------------------------------------------------------

    def _draw_static_canvas(self, screen: Any, pygame: Any) -> None:
        """First frame: the canonical boot canvas, continuing the fb splash."""

        path = canonical_boot_logo(self.root)
        try:
            if path is None:
                raise FileNotFoundError("no canonical boot art")
            logo = pygame.image.load(str(path))
            boot_animation.draw_canvas(screen, pygame, logo)
        except Exception:  # noqa: BLE001 - fail-soft presentation
            screen.fill(boot_animation.BACKGROUND_RGB)

    def _load_frames(self, screen: Any, pygame: Any) -> list[Any]:
        height = screen.get_height()

        def prepare(frame: Any) -> Any:
            # Scale to the viewport height and convert to the display format
            # once, so the loop never scales or converts per frame.
            size = boot_animation.fitted_size(frame.get_size(), height)
            if size != frame.get_size():
                frame = pygame.transform.smoothscale(frame, size)
            try:
                return frame.convert()
            except Exception:  # noqa: BLE001 - no display format (tests)
                return frame

        loader = self.frames_loader
        if loader is not None:
            return list(loader(pygame, prepare))
        return boot_animation.load_frames(
            pygame, boot_animation.candidate_frame_directories(self.root), prepare=prepare
        )

    @staticmethod
    def _blit_frame(screen: Any, frame: Any) -> None:
        width, height = screen.get_size()
        screen.fill(boot_animation.BACKGROUND_RGB)
        screen.blit(frame, frame.get_rect(center=(width // 2, height // 2)))

    # -- events ---------------------------------------------------------------

    @staticmethod
    def _skip_types(pygame: Any) -> set[int]:
        return {
            int(getattr(pygame, name))
            for name in _SKIP_EVENT_NAMES
            if hasattr(pygame, name)
        }

    def _skip_requested(self, pygame: Any, skip_types: set[int]) -> bool:
        try:
            events = pygame.event.get()
        except Exception:  # noqa: BLE001
            return False
        return any(int(getattr(event, "type", -1)) in skip_types for event in events)

    # -- run ------------------------------------------------------------------

    def run(
        self,
        screen: Any,
        pygame: Any,
        *,
        on_first_frame: Callable[[], None] | None = None,
    ) -> IntroOutcome:
        """Play the intro on ``screen``; always calls ``on_first_frame`` once."""

        self._draw_static_canvas(screen, pygame)
        pygame.display.flip()
        if on_first_frame is not None:
            try:
                on_first_frame()
            except Exception:  # noqa: BLE001 - cover release is best effort
                pass
        if self.disabled():
            return IntroOutcome.DISABLED
        if self.already_played():
            return IntroOutcome.ALREADY_PLAYED

        frames = self._load_frames(screen, pygame)
        if not frames:
            self._mark_played()
            return IntroOutcome.UNAVAILABLE

        skip_types = self._skip_types(pygame)
        timeline = boot_animation.IntroTimeline(
            total_frames=len(frames),
            animation_seconds=self.animation_seconds,
            hold_seconds=self.hold_seconds,
        )
        shown = -1
        timeline.start(self.clock())
        try:
            while True:
                if self._skip_requested(pygame, skip_types):
                    timeline.skip()
                now = self.clock()
                if timeline.phase(now) is boot_animation.IntroPhase.DONE:
                    break
                index = timeline.frame(now)
                if index != shown:
                    self._blit_frame(screen, frames[index])
                    pygame.display.flip()
                    shown = index
                try:
                    pygame.time.wait(_POLL_MILLISECONDS)
                except Exception:  # noqa: BLE001
                    pass
        finally:
            frames.clear()
            self._mark_played()
            # The skipping press (and its release) must never reach the
            # language screen, and stale pointer motion is meaningless there.
            try:
                pygame.event.clear()
            except Exception:  # noqa: BLE001
                pass
        if self.chime is not None:
            self.chime.play(skip=os.environ.get("GREIA_SKIP_BOOT_CHIME") == "1")
        return IntroOutcome.SKIPPED if timeline.skipped else IntroOutcome.PLAYED
