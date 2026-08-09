from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Protocol, Sequence


SCHEMA_VERSION = 1
_REQUIRED_VIDEO_DRIVER = "kmsdrm"
_CRASH_CHILD_EXIT = 23


class KMSDRMSerialHandoffError(RuntimeError):
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


class ChildRunner(Protocol):
    def run_clean(
        self, output_path: Path, *, frame_count: int
    ) -> subprocess.CompletedProcess[str]: ...

    def run_crash(self, marker_path: Path) -> subprocess.CompletedProcess[str]: ...


@dataclass(frozen=True, slots=True)
class SerialHandoffConfig:
    output_path: Path
    acknowledge_display_takeover: bool
    child_timeout_seconds: float = 15.0
    clean_child_frames: int = 3


class SubprocessChildRunner:
    def __init__(
        self,
        *,
        environment: Mapping[str, str],
        timeout_seconds: float,
        python_executable: str = sys.executable,
    ):
        self._environment = dict(environment)
        self._timeout_seconds = timeout_seconds
        self._python = python_executable

    def run_clean(
        self, output_path: Path, *, frame_count: int
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                self._python,
                "-m",
                "greia_platform.kmsdrm_acceptance",
                "--output",
                str(output_path),
                "--acknowledge-display-takeover",
                "--frames",
                str(frame_count),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=self._timeout_seconds,
            env=self._environment,
        )

    def run_crash(self, marker_path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                self._python,
                "-m",
                "greia_platform.kmsdrm_serial_handoff",
                "--crash-child",
                "--crash-marker",
                str(marker_path),
                "--acknowledge-display-takeover",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=self._timeout_seconds,
            env=self._environment,
        )


class KMSDRMSerialHandoffRunner:
    """Measure the serial DRM-ownership design from R7-D without adopting it.

    The parent acts as the Greia Shell: acquire KMSDRM, release it, allow a
    separate child process to acquire it, then reacquire after both a clean
    child exit and an abrupt child death. This is evidence tooling only; it is
    not the production shell/Activity session architecture.
    """

    def __init__(
        self,
        config: SerialHandoffConfig,
        *,
        environment: Mapping[str, str] = os.environ,
        pygame_module: _PygameModule | None = None,
        child_runner: ChildRunner | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.config = config
        self.environment = environment
        self._pygame = pygame_module
        self._clock = clock
        self._child_runner = child_runner or SubprocessChildRunner(
            environment=environment,
            timeout_seconds=config.child_timeout_seconds,
        )

    def run(self) -> dict[str, object]:
        self._validate_preconditions()
        pygame = self._pygame or _import_pygame()
        work_root = self.config.output_path.parent
        clean_path = work_root / "clean-child.json"
        crash_path = work_root / "crash-child.json"
        clean_path.unlink(missing_ok=True)
        crash_path.unlink(missing_ok=True)

        try:
            shell_initial = self._shell_phase(pygame, "shell-initial", 0)

            clean_started = self._clock()
            clean_process = self._child_runner.run_clean(
                clean_path, frame_count=self.config.clean_child_frames
            )
            clean_duration = _duration(self._clock() - clean_started)
            if clean_process.returncode != 0:
                raise KMSDRMSerialHandoffError(
                    "clean child KMSDRM acquisition did not exit successfully"
                )
            clean_child = _read_json_object(clean_path)
            _validate_clean_child(clean_child, self.config.clean_child_frames)

            shell_after_clean = self._shell_phase(pygame, "shell-after-clean", 1)

            crash_started = self._clock()
            crash_process = self._child_runner.run_crash(crash_path)
            crash_duration = _duration(self._clock() - crash_started)
            if crash_process.returncode != _CRASH_CHILD_EXIT:
                raise KMSDRMSerialHandoffError(
                    "crash child did not terminate through the intentional abrupt-exit path"
                )
            crash_child = _read_json_object(crash_path)
            _validate_crash_child(crash_child)

            shell_after_crash = self._shell_phase(pygame, "shell-after-crash", 2)
            shell_hashes = {
                shell_initial["frame_sha256"],
                shell_after_clean["frame_sha256"],
                shell_after_crash["frame_sha256"],
            }
            if len(shell_hashes) < 2:
                raise KMSDRMSerialHandoffError(
                    "serial handoff shell phases did not produce distinct rendered buffers"
                )

            result = {
                "schema_version": SCHEMA_VERSION,
                "ok": True,
                "requested_video_driver": _REQUIRED_VIDEO_DRIVER,
                "shell_initial": shell_initial,
                "clean_child": {
                    "return_code": clean_process.returncode,
                    "duration_seconds": clean_duration,
                    "result": clean_child,
                },
                "shell_after_clean": shell_after_clean,
                "crash_child": {
                    "return_code": crash_process.returncode,
                    "duration_seconds": crash_duration,
                    "result": crash_child,
                },
                "shell_after_crash": shell_after_crash,
                "recovery": {
                    "clean_child_reacquired": True,
                    "crash_child_reacquired": True,
                },
                "pygame_version": str(pygame.version.ver),
                "sdl_version": [int(value) for value in pygame.get_sdl_version()],
                "limitations": [
                    "proves serial SDL/Pygame KMSDRM release and reacquisition between processes",
                    "does not prove Activity sandbox input, shell UI continuity, or physical scanout",
                    "does not authorize serial DRM ownership as the production Greia session design",
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
            if isinstance(exc, KMSDRMSerialHandoffError):
                raise
            if isinstance(exc, subprocess.TimeoutExpired):
                raise KMSDRMSerialHandoffError(
                    "serial KMSDRM child acquisition timed out"
                ) from exc
            raise KMSDRMSerialHandoffError(
                "serial KMSDRM handoff acceptance failed"
            ) from exc

    def _shell_phase(
        self, pygame: _PygameModule, label: str, color_index: int
    ) -> dict[str, object]:
        started = self._clock()
        initialized = False
        try:
            pygame.display.init()
            initialized = True
            surface = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            driver = pygame.display.get_driver()
            if driver != _REQUIRED_VIDEO_DRIVER:
                raise KMSDRMSerialHandoffError(
                    f"SDL selected {driver!r}, expected {_REQUIRED_VIDEO_DRIVER!r}"
                )
            width, height = _surface_size(surface)
            surface.fill(_frame_color(color_index))
            pygame.display.flip()
            pygame.event.pump()
            raw = pygame.image.tostring(surface, "RGB")
            return {
                "label": label,
                "actual_video_driver": driver,
                "surface": {"width": width, "height": height},
                "frame_sha256": hashlib.sha256(raw).hexdigest(),
                "duration_seconds": _duration(self._clock() - started),
            }
        finally:
            if initialized:
                pygame.display.quit()

    def _validate_preconditions(self) -> None:
        if not self.config.acknowledge_display_takeover:
            raise KMSDRMSerialHandoffError(
                "serial KMSDRM handoff requires explicit display-takeover acknowledgement"
            )
        if (
            self.config.child_timeout_seconds <= 0
            or self.config.child_timeout_seconds > 120
        ):
            raise KMSDRMSerialHandoffError(
                "child timeout must be greater than 0 and at most 120 seconds"
            )
        if self.config.clean_child_frames < 1 or self.config.clean_child_frames > 16:
            raise KMSDRMSerialHandoffError(
                "clean child frame count must be between 1 and 16"
            )
        _validate_environment(self.environment)

    def _write_result(self, result: Mapping[str, object]) -> None:
        _write_json(self.config.output_path, result, durable=False)


def _run_crash_child(
    marker_path: Path,
    *,
    acknowledge_display_takeover: bool,
    environment: Mapping[str, str] = os.environ,
    pygame_module: _PygameModule | None = None,
) -> int:
    if not acknowledge_display_takeover:
        raise KMSDRMSerialHandoffError(
            "crash child requires explicit display-takeover acknowledgement"
        )
    _validate_environment(environment)
    pygame = pygame_module or _import_pygame()
    pygame.display.init()
    surface = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    driver = pygame.display.get_driver()
    if driver != _REQUIRED_VIDEO_DRIVER:
        pygame.display.quit()
        raise KMSDRMSerialHandoffError(
            f"crash child SDL selected {driver!r}, expected {_REQUIRED_VIDEO_DRIVER!r}"
        )
    width, height = _surface_size(surface)
    surface.fill(_frame_color(3))
    pygame.display.flip()
    pygame.event.pump()
    raw = pygame.image.tostring(surface, "RGB")
    _write_json(
        marker_path,
        {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "actual_video_driver": driver,
            "surface": {"width": width, "height": height},
            "frame_sha256": hashlib.sha256(raw).hexdigest(),
            "intentional_abrupt_exit": True,
        },
        durable=True,
    )
    # Intentionally do not call pygame.display.quit(). This proves whether the
    # parent can reacquire KMSDRM after an Activity-like process dies uncleanly.
    os._exit(_CRASH_CHILD_EXIT)


def _validate_environment(environment: Mapping[str, str]) -> None:
    if environment.get("SDL_VIDEODRIVER") != _REQUIRED_VIDEO_DRIVER:
        raise KMSDRMSerialHandoffError(
            "SDL_VIDEODRIVER must be explicitly set to kmsdrm"
        )
    if environment.get("DISPLAY") or environment.get("WAYLAND_DISPLAY"):
        raise KMSDRMSerialHandoffError(
            "serial KMSDRM handoff refuses X11/Wayland transport variables"
        )


def _validate_clean_child(payload: Mapping[str, object], minimum_frames: int) -> None:
    if payload.get("schema_version") != 1 or payload.get("ok") is not True:
        raise KMSDRMSerialHandoffError("clean child result did not pass")
    if (
        payload.get("requested_video_driver") != _REQUIRED_VIDEO_DRIVER
        or payload.get("actual_video_driver") != _REQUIRED_VIDEO_DRIVER
    ):
        raise KMSDRMSerialHandoffError("clean child did not actively select kmsdrm")
    frame_count = payload.get("frame_count")
    hashes = payload.get("frame_sha256")
    if (
        not isinstance(frame_count, int)
        or isinstance(frame_count, bool)
        or frame_count < minimum_frames
        or not isinstance(hashes, list)
        or len(hashes) != frame_count
    ):
        raise KMSDRMSerialHandoffError("clean child rendered-frame evidence is invalid")


def _validate_crash_child(payload: Mapping[str, object]) -> None:
    if (
        payload.get("schema_version") != 1
        or payload.get("ok") is not True
        or payload.get("actual_video_driver") != _REQUIRED_VIDEO_DRIVER
        or payload.get("intentional_abrupt_exit") is not True
    ):
        raise KMSDRMSerialHandoffError("crash child acquisition evidence is invalid")
    digest = payload.get("frame_sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise KMSDRMSerialHandoffError("crash child frame hash is invalid")
    _validate_surface_mapping(payload.get("surface"))


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
        raise KMSDRMSerialHandoffError("SDL returned an invalid display surface size")
    return width, height


def _validate_surface_mapping(value: object) -> None:
    if not isinstance(value, Mapping):
        raise KMSDRMSerialHandoffError("child evidence has no surface metadata")
    for key in ("width", "height"):
        dimension = value.get(key)
        if (
            not isinstance(dimension, int)
            or isinstance(dimension, bool)
            or dimension <= 0
            or dimension > 32_768
        ):
            raise KMSDRMSerialHandoffError("child evidence has invalid surface dimensions")


def _frame_color(index: int) -> tuple[int, int, int]:
    palette = (
        (24, 32, 48),
        (224, 216, 168),
        (84, 152, 112),
        (184, 72, 88),
    )
    return palette[index % len(palette)]


def _duration(value: float) -> float:
    duration = max(0.0, float(value))
    if not math.isfinite(duration):
        raise KMSDRMSerialHandoffError("acceptance duration is not finite")
    return round(duration, 6)


def _read_json_object(path: Path) -> Mapping[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise KMSDRMSerialHandoffError(
            f"missing or invalid child evidence: {path.name}"
        ) from exc
    if not isinstance(payload, dict):
        raise KMSDRMSerialHandoffError(
            f"child evidence is not a JSON object: {path.name}"
        )
    return payload


def _write_json(path: Path, payload: Mapping[str, object], *, durable: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    data = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    with temporary.open("wb") as stream:
        stream.write(data)
        stream.flush()
        if durable:
            os.fsync(stream.fileno())
    os.chmod(temporary, 0o644)
    os.replace(temporary, path)
    if durable:
        directory_fd = os.open(
            path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        )
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)


def _bounded_error(exc: Exception, maximum: int = 300) -> str:
    return " ".join(str(exc).split())[:maximum]


def _import_pygame():
    try:
        import pygame
    except ImportError as exc:
        raise KMSDRMSerialHandoffError("pygame is unavailable") from exc
    return pygame


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Measure serial SDL/Pygame KMSDRM ownership transfer and shell recovery."
        )
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--acknowledge-display-takeover", action="store_true")
    parser.add_argument("--child-timeout-seconds", type=float, default=15.0)
    parser.add_argument("--clean-child-frames", type=int, default=3)
    parser.add_argument("--crash-child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--crash-marker", type=Path, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.crash_child:
        if args.crash_marker is None:
            print("FAIL: --crash-marker is required for crash child", file=sys.stderr)
            return 2
        try:
            return _run_crash_child(
                args.crash_marker,
                acknowledge_display_takeover=args.acknowledge_display_takeover,
            )
        except KMSDRMSerialHandoffError as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1

    if args.output is None:
        print("FAIL: --output is required", file=sys.stderr)
        return 2
    runner = KMSDRMSerialHandoffRunner(
        SerialHandoffConfig(
            output_path=args.output,
            acknowledge_display_takeover=args.acknowledge_display_takeover,
            child_timeout_seconds=args.child_timeout_seconds,
            clean_child_frames=args.clean_child_frames,
        )
    )
    try:
        report = runner.run()
    except KMSDRMSerialHandoffError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
