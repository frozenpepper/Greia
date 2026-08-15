from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Protocol


SCHEMA_VERSION = 1
_REQUIRED_VIDEO_DRIVER = "kmsdrm"


class KMSDRMAcceptanceError(RuntimeError):
    pass


class _DisplayModule(Protocol):
    def init(self) -> None: ...

    def quit(self) -> None: ...

    def set_mode(self, size: tuple[int, int], flags: int = 0): ...

    def get_driver(self) -> str: ...

    def flip(self) -> None: ...


class _EventModule(Protocol):
    def pump(self) -> None: ...


class _ImageModule(Protocol):
    def tostring(self, surface, format_name: str) -> bytes: ...


class _PygameModule(Protocol):
    FULLSCREEN: int
    display: _DisplayModule
    event: _EventModule
    image: _ImageModule
    version: object

    def get_sdl_version(self) -> tuple[int, ...]: ...


@dataclass(frozen=True, slots=True)
class KMSDRMAcceptanceConfig:
    output_path: Path
    acknowledge_display_takeover: bool
    frame_count: int = 3


class KMSDRMAcceptanceRunner:
    """Controlled active proof that Pygame is truly using SDL KMSDRM.

    This class is intentionally separate from the passive image/runtime probe.
    It acquires a real display through SDL and therefore must only run in a
    dedicated R7 VM/physical acceptance session, never normal boot diagnostics.
    """

    def __init__(
        self,
        config: KMSDRMAcceptanceConfig,
        *,
        environment: Mapping[str, str] = os.environ,
        pygame_module: _PygameModule | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.config = config
        self.environment = environment
        self._pygame = pygame_module
        self._clock = clock

    def run(self) -> dict[str, object]:
        self._validate_preconditions()
        pygame = self._pygame or _import_pygame()
        started = self._clock()
        display_initialized = False
        try:
            pygame.display.init()
            display_initialized = True
            surface = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            driver = pygame.display.get_driver()
            if driver != _REQUIRED_VIDEO_DRIVER:
                raise KMSDRMAcceptanceError(
                    f"SDL selected {driver!r}, expected {_REQUIRED_VIDEO_DRIVER!r}"
                )
            width, height = _surface_size(surface)
            frame_hashes: list[str] = []
            for index in range(self.config.frame_count):
                # High-contrast deterministic frames make stale/no-op surfaces
                # detectable without depending on Greia UI/theme assets.
                color = _frame_color(index)
                surface.fill(color)
                pygame.display.flip()
                pygame.event.pump()
                raw = pygame.image.tostring(surface, "RGB")
                frame_hashes.append(hashlib.sha256(raw).hexdigest())
            _require_expected_frame_diversity(frame_hashes, self.config.frame_count)
            ended = self._clock()
            duration = max(0.0, float(ended - started))
            if not math.isfinite(duration):
                raise KMSDRMAcceptanceError("acceptance duration is not finite")
            result = {
                "schema_version": SCHEMA_VERSION,
                "ok": True,
                "requested_video_driver": _REQUIRED_VIDEO_DRIVER,
                "actual_video_driver": driver,
                "surface": {"width": width, "height": height},
                "frame_count": self.config.frame_count,
                "frame_sha256": frame_hashes,
                "duration_seconds": round(duration, 6),
                "pygame_version": str(pygame.version.ver),
                "sdl_version": [int(value) for value in pygame.get_sdl_version()],
                "limitations": [
                    "proves SDL/Pygame active KMSDRM display creation and changing rendered buffers",
                    "does not by itself prove physical scanout continuity, input routing, or shell-Activity ownership",
                ],
            }
            self._write_result(result)
            return result
        except Exception as exc:
            failure = {
                "schema_version": SCHEMA_VERSION,
                "ok": False,
                "requested_video_driver": _REQUIRED_VIDEO_DRIVER,
                "error_type": type(exc).__name__,
                "error": _bounded_error(exc),
            }
            self._write_result(failure)
            if isinstance(exc, KMSDRMAcceptanceError):
                raise
            raise KMSDRMAcceptanceError("active KMSDRM acceptance failed") from exc
        finally:
            if display_initialized:
                try:
                    pygame.display.quit()
                except Exception:
                    pass

    def _validate_preconditions(self) -> None:
        if not self.config.acknowledge_display_takeover:
            raise KMSDRMAcceptanceError(
                "active KMSDRM acceptance requires explicit display-takeover acknowledgement"
            )
        if (
            isinstance(self.config.frame_count, bool)
            or not isinstance(self.config.frame_count, int)
            or self.config.frame_count < 1
            or self.config.frame_count > 16
        ):
            raise KMSDRMAcceptanceError("frame_count must be an integer between 1 and 16")
        if self.environment.get("SDL_VIDEODRIVER") != _REQUIRED_VIDEO_DRIVER:
            raise KMSDRMAcceptanceError(
                "SDL_VIDEODRIVER must be explicitly set to kmsdrm"
            )
        if any(
            self.environment.get(name)
            for name in ("DISPLAY", "XAUTHORITY", "WAYLAND_DISPLAY")
        ):
            raise KMSDRMAcceptanceError(
                "active KMSDRM acceptance refuses X11/Wayland transport authority"
            )

    def _write_result(self, result: Mapping[str, object]) -> None:
        target = self.config.output_path
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".tmp")
        payload = json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ) + "\n"
        temporary.write_text(payload, encoding="utf-8")
        os.chmod(temporary, 0o644)
        os.replace(temporary, target)


def _require_expected_frame_diversity(frame_hashes: list[str], frame_count: int) -> None:
    expected_unique = min(frame_count, len(_FRAME_PALETTE))
    if len(frame_hashes) != frame_count or len(set(frame_hashes)) < expected_unique:
        raise KMSDRMAcceptanceError(
            "active KMSDRM rendered-frame evidence did not change as expected"
        )


def _surface_size(surface) -> tuple[int, int]:
    width, height = surface.get_size()
    if (
        isinstance(width, bool)
        or isinstance(height, bool)
        or not isinstance(width, int)
        or not isinstance(height, int)
        or width <= 0
        or height <= 0
        or width > 32_768
        or height > 32_768
    ):
        raise KMSDRMAcceptanceError("SDL returned an invalid display surface size")
    return width, height


_FRAME_PALETTE = ((16, 16, 16), (238, 238, 224), (96, 128, 160))


def _frame_color(index: int) -> tuple[int, int, int]:
    return _FRAME_PALETTE[index % len(_FRAME_PALETTE)]


def _bounded_error(exc: Exception, maximum: int = 300) -> str:
    text = " ".join(str(exc).split())
    return text[:maximum]


def _import_pygame():
    try:
        import pygame
    except ImportError as exc:
        raise KMSDRMAcceptanceError("pygame is unavailable") from exc
    return pygame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an explicit active Pygame/SDL KMSDRM acceptance test."
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--acknowledge-display-takeover", action="store_true")
    parser.add_argument("--frames", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runner = KMSDRMAcceptanceRunner(
        KMSDRMAcceptanceConfig(
            output_path=args.output,
            acknowledge_display_takeover=args.acknowledge_display_takeover,
            frame_count=args.frames,
        )
    )
    try:
        runner.run()
    except KMSDRMAcceptanceError as exc:
        print(f"FAIL: {exc}", file=os.sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
