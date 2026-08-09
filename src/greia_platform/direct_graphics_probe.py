from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import importlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping


SCHEMA_VERSION = 1


class GraphicsProbeError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ProbeInputs:
    root: Path
    environment: Mapping[str, str]


class DirectGraphicsProbe:
    """Passive R7 probe for image/runtime direct-graphics capability.

    The probe deliberately does not initialize a video backend, open DRM/input
    devices, acquire DRM master, or change display state. It only inventories
    compiled/runtime facts. Active KMSDRM acceptance belongs in a controlled VM
    or physical-hardware harness.
    """

    def __init__(
        self,
        inputs: ProbeInputs,
        *,
        library_finder: Callable[[str], str | None] = ctypes.util.find_library,
        sdl_driver_probe: Callable[[], tuple[str, ...]] | None = None,
        pygame_probe: Callable[[], dict[str, object]] | None = None,
    ):
        self.inputs = inputs
        self._library_finder = library_finder
        self._sdl_driver_probe = sdl_driver_probe or _compiled_sdl_video_drivers
        self._pygame_probe = pygame_probe or _pygame_metadata

    def snapshot(self) -> dict[str, object]:
        drivers = self._safe_sdl_drivers()
        drm = self._drm_snapshot()
        libraries = {
            name: bool(self._library_finder(name))
            for name in ("drm", "gbm", "EGL", "input", "seat")
        }
        scanout_connector_visible = _has_connected_connector_with_mode(drm["connectors"])
        return {
            "schema_version": SCHEMA_VERSION,
            "passive": True,
            "pygame": self._safe_pygame_metadata(),
            "sdl": {
                "video_drivers": list(drivers),
                "kmsdrm_compiled": "kmsdrm" in drivers,
            },
            "libraries": libraries,
            "drm": drm,
            "session": self._session_snapshot(),
            "assessment": {
                # This is intentionally only a prerequisite classification. A
                # successful active KMSDRM window/frame test is still mandatory.
                # A DRM card without a connected connector/mode is not enough to
                # establish a scanout path and should be diagnosed as topology.
                "scanout_connector_visible": scanout_connector_visible,
                "kmsdrm_prerequisites_visible": bool(
                    "kmsdrm" in drivers
                    and drm["card_nodes"]
                    and scanout_connector_visible
                    and libraries["drm"]
                    and libraries["gbm"]
                ),
                "active_kmsdrm_test_required": True,
            },
        }

    def _safe_sdl_drivers(self) -> tuple[str, ...]:
        try:
            values = self._sdl_driver_probe()
        except Exception:
            return ()
        return tuple(dict.fromkeys(value for value in values if value))

    def _safe_pygame_metadata(self) -> dict[str, object]:
        try:
            value = self._pygame_probe()
        except Exception as exc:
            return {"available": False, "error": type(exc).__name__}
        return value

    def _drm_snapshot(self) -> dict[str, object]:
        root = self.inputs.root
        dri_root = root / "dev" / "dri"
        card_nodes = _relative_names(dri_root, "card*")
        render_nodes = _relative_names(dri_root, "renderD*")

        connectors: list[dict[str, object]] = []
        drm_sysfs = root / "sys" / "class" / "drm"
        if drm_sysfs.is_dir():
            for entry in sorted(drm_sysfs.iterdir(), key=lambda item: item.name):
                if "-" not in entry.name:
                    continue
                status_path = entry / "status"
                modes_path = entry / "modes"
                status = _read_small_text(status_path)
                modes = tuple(
                    line.strip()
                    for line in _read_small_text(modes_path).splitlines()
                    if line.strip()
                )
                if status or modes:
                    connectors.append(
                        {
                            "name": entry.name,
                            "status": status,
                            "modes": list(modes[:64]),
                        }
                    )
        return {
            "card_nodes": list(card_nodes),
            "render_nodes": list(render_nodes),
            "connectors": connectors,
        }

    def _session_snapshot(self) -> dict[str, object]:
        env = self.inputs.environment
        # Presence rather than values avoids leaking display/session tokens into
        # diagnostics while still showing which transport the current image uses.
        return {
            "display_present": bool(env.get("DISPLAY")),
            "wayland_display_present": bool(env.get("WAYLAND_DISPLAY")),
            "sdl_videodriver": _bounded_env_value(env.get("SDL_VIDEODRIVER")),
            "xdg_session_id_present": bool(env.get("XDG_SESSION_ID")),
            "xdg_seat": _bounded_env_value(env.get("XDG_SEAT")),
            "xdg_vtnr": _bounded_env_value(env.get("XDG_VTNR")),
        }


def _has_connected_connector_with_mode(connectors: object) -> bool:
    if not isinstance(connectors, list):
        return False
    for connector in connectors:
        if not isinstance(connector, Mapping):
            continue
        status = connector.get("status")
        modes = connector.get("modes")
        if (
            isinstance(status, str)
            and status.strip().lower() == "connected"
            and isinstance(modes, list)
            and any(isinstance(mode, str) and mode.strip() for mode in modes)
        ):
            return True
    return False


def _compiled_sdl_video_drivers() -> tuple[str, ...]:
    library_name = ctypes.util.find_library("SDL2-2.0") or ctypes.util.find_library("SDL2")
    if not library_name:
        return ()
    library = ctypes.CDLL(library_name)
    get_count = library.SDL_GetNumVideoDrivers
    get_count.argtypes = []
    get_count.restype = ctypes.c_int
    get_driver = library.SDL_GetVideoDriver
    get_driver.argtypes = [ctypes.c_int]
    get_driver.restype = ctypes.c_char_p
    count = get_count()
    if count < 0 or count > 128:
        raise GraphicsProbeError("SDL returned an invalid video-driver count")
    drivers: list[str] = []
    for index in range(count):
        raw = get_driver(index)
        if raw:
            drivers.append(raw.decode("ascii", errors="strict"))
    return tuple(drivers)


def _pygame_metadata() -> dict[str, object]:
    previous_prompt_setting = os.environ.get("PYGAME_HIDE_SUPPORT_PROMPT")
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    try:
        pygame = importlib.import_module("pygame")
    finally:
        if previous_prompt_setting is None:
            os.environ.pop("PYGAME_HIDE_SUPPORT_PROMPT", None)
        else:
            os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = previous_prompt_setting
    sdl_version = tuple(int(value) for value in pygame.get_sdl_version())
    return {
        "available": True,
        "version": str(pygame.version.ver),
        "sdl_version": list(sdl_version),
    }


def _relative_names(root: Path, pattern: str) -> tuple[str, ...]:
    try:
        return tuple(sorted(path.name for path in root.glob(pattern) if path.exists()))
    except OSError:
        return ()


def _read_small_text(path: Path, *, maximum_bytes: int = 16_384) -> str:
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    if len(data) > maximum_bytes:
        return ""
    return data.decode("utf-8", errors="replace").strip()


def _bounded_env_value(value: str | None, *, maximum: int = 128) -> str | None:
    if value is None or not value or len(value) > maximum or "\x00" in value:
        return None
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Passively inventory Greia direct-graphics prerequisites."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("/"),
        help="filesystem root to inspect (useful for mounted images/tests)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    probe = DirectGraphicsProbe(
        ProbeInputs(root=args.root.resolve(), environment=os.environ)
    )
    print(json.dumps(probe.snapshot(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
