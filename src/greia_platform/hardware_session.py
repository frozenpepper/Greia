from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from threading import Event
from typing import Protocol

from .display_metrics import DisplayMetrics
from .hardware import (
    MAX_STATUS_LABEL_CHARS,
    MAX_STATUS_POINTER_DEVICES,
    DisplayMode,
    HardwareSettings,
    HardwareSettingsStore,
)


class PointerKind(Enum):
    """Semantic pointer classification shared by backends and UI.

    Values describe Greia interaction semantics, never backend device
    names or numeric device ids. ``OTHER_RELATIVE`` covers relative
    pointers that are neither touchpad nor mouse (e.g. trackballs and
    other relative locators); ``TOUCHSCREEN`` covers direct-touch
    panels, which expose no tap-to-click/speed semantics.
    """

    TOUCHPAD = "touchpad"
    MOUSE = "mouse"
    OTHER_RELATIVE = "other_relative"
    TOUCHSCREEN = "touchscreen"


@dataclass(frozen=True, slots=True)
class PointerCapabilities:
    """Semantic per-pointer controls a backend actually supports.

    Every flag defaults to ``False``: a missing optional backend
    property means unsupported/not-applicable, never fatal.
    """

    supports_tap: bool = False
    supports_natural_scrolling: bool = False
    supports_disable_while_typing: bool = False
    supports_speed: bool = False


@dataclass(frozen=True, slots=True)
class PointerDeviceInfo:
    """Backend-neutral description of one pointer for preview/UI.

    Contains no backend device names and no numeric device ids; ids
    never persist and never leave the owning adapter. ``label`` is a
    generic kind-derived display label (e.g. ``"Touchpad"``), never an
    exact backend device name, so classification never requires one.
    """

    kind: PointerKind
    label: str
    capabilities: PointerCapabilities


@dataclass(frozen=True, slots=True)
class DisplayProbe:
    """Semantic display facts used to validate bounded parent settings.

    ``metrics`` contract (single consistent rule): ``None`` means there
    is nothing to describe — no connected output or no mode flagged
    current. A non-``None`` value always carries the current-mode pixel
    size; when physical panel data was absent/malformed the metrics
    report unknown physical size (``physical_size_known`` is ``False``,
    densities are ``None``) and no fallback density is ever assumed.
    """

    output_name: str | None
    modes: tuple[DisplayMode, ...]
    metrics: DisplayMetrics | None = None

    @property
    def allowed_mode_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(mode.mode_id for mode in self.modes))


@dataclass(frozen=True, slots=True)
class ApplyResult:
    applied: bool
    display: DisplayProbe
    messages: tuple[str, ...]


class HardwareSessionController(Protocol):
    """Backend-neutral display/input settings controller used by the watcher.

    Implementations translate Greia's bounded HardwareSettings into one concrete
    display/input backend. The generic watcher never selects a backend or knows
    backend-specific commands/property names.
    """

    @property
    def backend_id(self) -> str: ...

    def topology_token(self) -> tuple[str, ...]: ...

    def probe_display(self) -> DisplayProbe: ...

    def apply(self, settings: HardwareSettings) -> ApplyResult: ...


class PointerSettingsController(Protocol):
    """Pointer-only preview seam for installer/parent settings UI.

    ``probe_pointers`` lists the currently attached pointers in
    backend-neutral terms; ``apply_pointer_settings`` applies only the
    pointer subset of ``settings`` (no display/keyboard/audio commands)
    so a preview step never changes the screen mode. The generic
    ``HardwareSessionController.apply`` stays the watcher entry point.
    """

    def probe_pointers(self) -> tuple[PointerDeviceInfo, ...]: ...

    def apply_pointer_settings(
        self, settings: HardwareSettings
    ) -> ApplyResult: ...


# --- Shared pointer-speed presets -------------------------------------------
# Single location mapping UI-friendly preset names to libinput-style
# ``-1.0..1.0`` speeds. Installer/parent UI (T07/T08) consume these names
# and never formats raw floats itself.

SPEED_PRESETS: tuple[tuple[str, float], ...] = (
    ("very slow", -0.8),
    ("slow", -0.4),
    ("medium", 0.0),
    ("fast", 0.4),
    ("very fast", 0.8),
)


def speed_preset_names() -> tuple[str, ...]:
    """Return the friendly speed preset names in display order."""
    return tuple(name for name, _ in SPEED_PRESETS)


def preset_to_speed(name: str) -> float:
    """Map a friendly preset name to its ``-1.0..1.0`` speed value."""
    for preset_name, value in SPEED_PRESETS:
        if preset_name == name:
            return value
    raise KeyError(f"unknown pointer speed preset: {name!r}")


def speed_to_preset(value: float) -> str:
    """Map a ``-1.0..1.0`` speed to the nearest friendly preset name."""
    candidate = float(value)
    best_name, best_value = SPEED_PRESETS[0]
    for preset_name, preset_value in SPEED_PRESETS:
        if abs(preset_value - candidate) < abs(best_value - candidate):
            best_name, best_value = preset_name, preset_value
    return best_name


def run_watcher(
    store: HardwareSettingsStore,
    status_path: Path,
    *,
    controller: HardwareSessionController,
    interval_seconds: float = 0.5,
    once: bool = False,
    stop_event: Event | None = None,
) -> int:
    """Apply desired settings through the explicitly selected backend adapter.

    ``stop_event`` lets a concrete session compose this watcher with other
    platform-owned hardware services without creating an unowned background
    process or a second hardware daemon.

    Cadence is unchanged: topology is probed at most every 2 s and settings
    are reapplied only on settings/topology/retry transitions. Display
    metrics are never recomputed here; the status writer reuses the
    ``DisplayProbe.metrics`` facts already produced for the apply cycle.
    Pointer facts come from the optional ``probe_pointers`` seam at most
    once per status write (same apply cadence) and degrade to ``()``.
    """

    backend_id = _backend_id(controller)
    stopper = stop_event or Event()
    last_settings_token: int | None = None
    last_topology_token: tuple[str, ...] | None = None
    next_topology_probe = 0.0
    retry_at = 0.0
    last_apply_succeeded = False
    while not stopper.is_set():
        now = time.monotonic()
        settings_token = store.version_token()
        topology_token = last_topology_token
        if topology_token is None or now >= next_topology_probe:
            topology_token = controller.topology_token()
            next_topology_probe = now + 2.0
        should_apply = (
            settings_token != last_settings_token
            or topology_token != last_topology_token
            or (not last_apply_succeeded and now >= retry_at)
        )
        if should_apply:
            last_settings_token = settings_token
            last_topology_token = topology_token
            settings = store.read()
            display = controller.probe_display()
            try:
                store.validate(settings, allowed_resolutions=display.allowed_mode_ids)
                result = controller.apply(settings)
                last_apply_succeeded = result.applied
                retry_at = now + 2.0
                message = " ".join(result.messages)
                _write_status(
                    status_path,
                    settings,
                    result,
                    message,
                    backend_id=backend_id,
                    pointer_infos=_probe_pointer_infos(controller),
                )
            except Exception as exc:  # keep the child session alive on driver errors
                last_apply_succeeded = False
                retry_at = now + 2.0
                failed = ApplyResult(False, display, (_bounded_error(exc),))
                _write_status(
                    status_path,
                    settings,
                    failed,
                    _bounded_error(exc),
                    backend_id=backend_id,
                    pointer_infos=_probe_pointer_infos(controller),
                )
        if once:
            return 0
        stopper.wait(interval_seconds)
    return 0


def _backend_id(controller: HardwareSessionController) -> str:
    value = controller.backend_id
    if not isinstance(value, str):
        raise TypeError("hardware settings backend_id must be text")
    value = value.strip()
    if not value or len(value) > 64:
        raise ValueError("hardware settings backend_id must contain 1..64 characters")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")
    if any(character not in allowed for character in value):
        raise ValueError("hardware settings backend_id contains unsupported characters")
    return value


def _write_status(
    path: Path,
    settings: HardwareSettings,
    result: ApplyResult,
    message: str,
    *,
    backend_id: str,
    pointer_infos: tuple[PointerDeviceInfo, ...] = (),
) -> None:
    """Write the atomic watcher status file (T09 consumer contract).

    JSON shape (keys stable; new keys are additive and optional on read)::

        {
          "settings": {...HardwareSettings...},
          "applied": bool,
          "backend": str,                      # 1..64 chars, backend id
          "display_output": str | null,
          "display_modes": [{"id","width","height","refresh_hz",
                             "preferred","current"}],
          "display_metrics": null | {"pixel_width": int,
            "pixel_height": int, "physical_size_known": bool,
            "orientation": "landscape"|"portrait"|"square",
            "source": str, "physical_width_mm": float (only when known),
            "physical_height_mm": float (only when known)},
          "pointer_devices": [{"kind": str, "label": str,
            "supports_tap": bool, "supports_natural_scrolling": bool,
            "supports_disable_while_typing": bool, "supports_speed": bool}],
          "message": str                       # bounded to 240 chars per entry
        }

    The ``pointer_devices`` entry shape matches
    ``PointerDeviceStatus.as_json_dict`` exactly so the file shape and the
    ``read_apply_status(...).as_json_dict()`` shape consumed by T09 are the
    same. Bounds: ``display_metrics`` reuses the ``DisplayProbe.metrics`` facts
    already produced by the controller for this apply cycle (no recompute,
    no per-frame polling, no new subprocess). ``pointer_devices`` holds at
    most ``MAX_STATUS_POINTER_DEVICES`` generic entries with labels
    truncated to ``MAX_STATUS_LABEL_CHARS``; numeric backend ids and raw
    ``xrandr``/``xinput`` output never persist. No suitability verdict is
    stored: ``DisplayPolicy`` evaluation stays above this layer. Writes stay
    atomic (temp file + rename, mode 0o640). Readers (``read_apply_status``)
    treat ``display_metrics``/``pointer_devices`` as optional so old payloads
    parse unchanged.
    """
    payload = {
        "settings": settings.as_json_dict(),
        "applied": result.applied,
        "backend": backend_id,
        "display_output": result.display.output_name,
        "display_modes": [mode.as_json_dict() for mode in result.display.modes],
        "display_metrics": _display_metrics_payload(result.display.metrics),
        "pointer_devices": _pointer_devices_payload(pointer_infos),
        "message": message,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o640)
    temporary.replace(path)


def _display_metrics_payload(metrics: DisplayMetrics | None) -> dict[str, object] | None:
    """Serialize probe metrics to the bounded status shape (or ``None``)."""
    if metrics is None or not isinstance(metrics, DisplayMetrics):
        return None
    payload: dict[str, object] = {
        "pixel_width": metrics.pixel_width,
        "pixel_height": metrics.pixel_height,
        "physical_size_known": metrics.physical_size_known,
        "orientation": metrics.orientation,
        "source": metrics.source.value,
    }
    if metrics.physical_size_known:
        assert metrics.physical_width_mm is not None
        assert metrics.physical_height_mm is not None
        payload["physical_width_mm"] = float(metrics.physical_width_mm)
        payload["physical_height_mm"] = float(metrics.physical_height_mm)
    return payload


def _pointer_devices_payload(
    infos: tuple[PointerDeviceInfo, ...] | list[PointerDeviceInfo] | object,
) -> list[dict[str, object]]:
    """Serialize pointer infos to the bounded generic summary shape.

    Entry shape matches ``PointerDeviceStatus.as_json_dict`` (flat
    ``supports_*`` flags) so the file and the reader output agree.
    """
    if not isinstance(infos, (tuple, list)):
        return []
    payload: list[dict[str, object]] = []
    for info in infos:
        if not isinstance(info, PointerDeviceInfo):
            continue
        kind = info.kind.value if isinstance(info.kind, PointerKind) else str(info.kind)
        label = str(getattr(info, "label", kind))[:MAX_STATUS_LABEL_CHARS] or kind
        capabilities = getattr(info, "capabilities", None)
        payload.append(
            {
                "kind": str(kind)[:MAX_STATUS_LABEL_CHARS],
                "label": label,
                "supports_tap": bool(getattr(capabilities, "supports_tap", False)),
                "supports_natural_scrolling": bool(
                    getattr(capabilities, "supports_natural_scrolling", False)
                ),
                "supports_disable_while_typing": bool(
                    getattr(capabilities, "supports_disable_while_typing", False)
                ),
                "supports_speed": bool(getattr(capabilities, "supports_speed", False)),
            }
        )
        if len(payload) >= MAX_STATUS_POINTER_DEVICES:
            break
    return payload


def _probe_pointer_infos(
    controller: HardwareSessionController,
) -> tuple[PointerDeviceInfo, ...]:
    """Best-effort pointer summary for one status write (same apply cadence).

    Calls the optional ``probe_pointers`` preview seam when the controller
    provides it; controllers without it simply contribute ``()``. Runs at
    most once per status write (which happens only on settings/topology/
    retry apply), so it adds no new polling loop, daemon, or per-frame
    subprocess. Any probe failure degrades to ``()`` and never breaks the
    watcher or the status write.
    """
    probe = getattr(controller, "probe_pointers", None)
    if not callable(probe):
        return ()
    try:
        infos = probe()
    except Exception:
        return ()
    if not isinstance(infos, (tuple, list)):
        return ()
    return tuple(info for info in infos if isinstance(info, PointerDeviceInfo))[
        :MAX_STATUS_POINTER_DEVICES
    ]


def _bounded_error(exc: Exception, maximum: int = 240) -> str:
    text = " ".join(str(exc).split())
    return (text or exc.__class__.__name__)[:maximum]
