from __future__ import annotations

import json
import os
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:  # Avoid a runtime cycle: display_metrics imports DisplayMode.
    from .display_metrics import DisplayMetrics


class HardwareSettingsError(ValueError):
    """Raised when a requested hardware preference is outside platform policy."""


@dataclass(frozen=True, slots=True)
class DisplayMode:
    width: int
    height: int
    refresh_hz: float | None = None
    preferred: bool = False
    current: bool = False

    @property
    def mode_id(self) -> str:
        return f"{self.width}x{self.height}"

    def as_json_dict(self) -> dict[str, object]:
        return {
            "id": self.mode_id,
            "width": self.width,
            "height": self.height,
            "refresh_hz": self.refresh_hz,
            "preferred": self.preferred,
            "current": self.current,
        }


@dataclass(frozen=True, slots=True)
class HardwareDefaults:
    schema_version: int
    touchpad_tap: bool
    touchpad_speed: float
    mouse_speed: float
    natural_scrolling: bool
    resolution: str
    keyboard_layout: str
    minimum_speed: float
    maximum_speed: float
    mic_gain: float = 2.0
    minimum_mic_gain: float = 0.5
    maximum_mic_gain: float = 2.0
    disable_while_typing: bool = False

    @classmethod
    def default_safe(cls) -> "HardwareDefaults":
        """Built-in immutable fallback policy for hardware settings."""
        return cls(
            schema_version=2,
            touchpad_tap=False,
            touchpad_speed=0.35,
            mouse_speed=0.0,
            natural_scrolling=False,
            resolution="auto",
            keyboard_layout="us",
            minimum_speed=-1.0,
            maximum_speed=1.0,
            mic_gain=2.0,
            minimum_mic_gain=0.5,
            maximum_mic_gain=2.0,
            disable_while_typing=False,
        )

    @classmethod
    def load(cls, path: Path) -> "HardwareDefaults":
        if not path.is_file() or path.stat().st_size == 0:
            return cls.default_safe()
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            return cls.default_safe()
        defaults = data.get("defaults")
        limits = data.get("limits")
        if not isinstance(defaults, dict) or not isinstance(limits, dict):
            return cls.default_safe()
        try:
            loaded = cls(
                schema_version=int(data.get("schema_version", 2)),
                touchpad_tap=_strict_bool(defaults.get("touchpad_tap", False), "touchpad_tap"),
                touchpad_speed=float(defaults.get("touchpad_speed", 0.35)),
                mouse_speed=float(defaults.get("mouse_speed", 0.0)),
                natural_scrolling=_strict_bool(
                    defaults.get("natural_scrolling", False), "natural_scrolling"
                ),
                resolution=str(defaults.get("resolution", "auto")),
                # Older target payloads predate the keyboard_layout setting;
                # default it to "us" so installs still work against them.
                keyboard_layout=str(defaults.get("keyboard_layout", "us")),
                minimum_speed=float(limits.get("minimum_speed", -1.0)),
                maximum_speed=float(limits.get("maximum_speed", 1.0)),
                mic_gain=float(defaults.get("mic_gain", 2.0)),
                minimum_mic_gain=float(limits.get("minimum_mic_gain", 0.5)),
                maximum_mic_gain=float(limits.get("maximum_mic_gain", 2.0)),
                disable_while_typing=_strict_bool(
                    defaults.get("disable_while_typing", False),
                    "disable_while_typing",
                ),
            )
        except (KeyError, TypeError, ValueError):
            return cls.default_safe()
        if loaded.schema_version not in (1, 2):
            return cls.default_safe()
        if loaded.schema_version == 1:
            # Migrate v1 platform defaults: preserve all valid values,
            # upgrade the version marker and default the new field to False
            # (pre-tranche hard-coded backend behavior).
            loaded = cls(
                schema_version=2,
                touchpad_tap=loaded.touchpad_tap,
                touchpad_speed=loaded.touchpad_speed,
                mouse_speed=loaded.mouse_speed,
                natural_scrolling=loaded.natural_scrolling,
                resolution=loaded.resolution,
                keyboard_layout=loaded.keyboard_layout,
                minimum_speed=loaded.minimum_speed,
                maximum_speed=loaded.maximum_speed,
                mic_gain=loaded.mic_gain,
                minimum_mic_gain=loaded.minimum_mic_gain,
                maximum_mic_gain=loaded.maximum_mic_gain,
                disable_while_typing=False,
            )
        try:
            loaded.validate_keyboard_layout(loaded.keyboard_layout)
        except HardwareSettingsError:
            loaded = cls(
                schema_version=loaded.schema_version,
                touchpad_tap=loaded.touchpad_tap,
                touchpad_speed=loaded.touchpad_speed,
                mouse_speed=loaded.mouse_speed,
                natural_scrolling=loaded.natural_scrolling,
                resolution=loaded.resolution,
                keyboard_layout="us",
                minimum_speed=loaded.minimum_speed,
                maximum_speed=loaded.maximum_speed,
                mic_gain=loaded.mic_gain,
                minimum_mic_gain=loaded.minimum_mic_gain,
                maximum_mic_gain=loaded.maximum_mic_gain,
                disable_while_typing=loaded.disable_while_typing,
            )
        if loaded.minimum_speed < -1.0 or loaded.maximum_speed > 1.0 or loaded.minimum_speed >= loaded.maximum_speed:
            return cls.default_safe()
        if loaded.minimum_mic_gain <= 0.0 or loaded.minimum_mic_gain >= loaded.maximum_mic_gain:
            return cls.default_safe()
        return loaded

    def validate_speed(self, value: float, name: str) -> float:
        value = round(float(value), 2)
        if not self.minimum_speed <= value <= self.maximum_speed:
            raise HardwareSettingsError(
                f"{name} must be between {self.minimum_speed} and {self.maximum_speed}"
            )
        return value

    def validate_mic_gain(self, value: float) -> float:
        value = round(float(value), 2)
        if not self.minimum_mic_gain <= value <= self.maximum_mic_gain:
            raise HardwareSettingsError(
                f"mic_gain must be between {self.minimum_mic_gain} and {self.maximum_mic_gain}"
            )
        return value

    def validate_keyboard_layout(self, value: str) -> str:
        from .keyboard_layout import layout_by_id

        try:
            layout_by_id(value)
        except LookupError as exc:
            raise HardwareSettingsError(f"unsupported keyboard layout: {value}") from exc
        return value


@dataclass(frozen=True, slots=True)
class HardwareSettings:
    schema_version: int
    touchpad_tap: bool
    touchpad_speed: float
    mouse_speed: float
    natural_scrolling: bool
    resolution: str
    keyboard_layout: str
    mic_gain: float = 2.0
    disable_while_typing: bool = False

    def as_json_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PointerDeviceStatus:
    """Bounded backend-neutral description of one pointer in status output.

    ``kind`` is a short semantic token (``touchpad``/``mouse``/
    ``other_relative``/``touchscreen``); ``label`` is a generic kind-derived
    display label, never a backend device name. Numeric backend ids never
    persist here. Bounds: at most ``MAX_STATUS_POINTER_DEVICES`` entries per
    status payload, each string truncated to ``MAX_STATUS_LABEL_CHARS``.
    """

    kind: str
    label: str
    supports_tap: bool = False
    supports_natural_scrolling: bool = False
    supports_disable_while_typing: bool = False
    supports_speed: bool = False

    def as_json_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "label": self.label,
            "supports_tap": self.supports_tap,
            "supports_natural_scrolling": self.supports_natural_scrolling,
            "supports_disable_while_typing": self.supports_disable_while_typing,
            "supports_speed": self.supports_speed,
        }


# Bounds for the pointer-capability summary in status output. Small enough
# for the Acer reference floor; no per-device or per-metric caches exist.
MAX_STATUS_POINTER_DEVICES = 8
MAX_STATUS_LABEL_CHARS = 32

# Reader-side sanity bounds mirroring the T01 ``sanitize_display_metrics``
# gate (pixels 1..16384, physical 20..3000mm). The reader re-checks them so
# a hand-edited status file cannot inject absurd dimensions; it never
# invents dimensions (out-of-range physical becomes unknown, bad pixels
# become "no metrics").
_STATUS_MAX_PIXEL_DIMENSION = 16384
_STATUS_MIN_PHYSICAL_MM = 20.0
_STATUS_MAX_PHYSICAL_MM = 3000.0


@dataclass(frozen=True, slots=True)
class HardwareApplyStatus:
    settings: HardwareSettings
    applied: bool
    display_output: str | None
    display_modes: tuple[DisplayMode, ...]
    message: str
    display_metrics: DisplayMetrics | None = None
    pointer_devices: tuple[PointerDeviceStatus, ...] = ()

    def as_json_dict(self) -> dict[str, object]:
        from .display_metrics import DisplayMetrics as _Metrics

        metrics_payload: dict[str, object] | None = None
        metrics = self.display_metrics
        if isinstance(metrics, _Metrics):
            metrics_payload = _metrics_to_json_dict(metrics)
        return {
            "settings": self.settings.as_json_dict(),
            "applied": self.applied,
            "display_output": self.display_output,
            "display_modes": [mode.as_json_dict() for mode in self.display_modes],
            "message": self.message,
            "display_metrics": metrics_payload,
            "pointer_devices": [device.as_json_dict() for device in self.pointer_devices],
        }


class HardwareSettingsStore:
    """Bounded parent-owned desired state for input and display behavior."""

    SETTINGS_NAME = "settings.json"

    def __init__(self, defaults: HardwareDefaults, state_dir: Path):
        self.defaults = defaults
        self.state_dir = state_dir.resolve()

    @classmethod
    def load(cls, defaults_path: Path, state_dir: Path) -> "HardwareSettingsStore":
        return cls(HardwareDefaults.load(defaults_path), state_dir)

    @property
    def settings_path(self) -> Path:
        return self.state_dir / self.SETTINGS_NAME

    def default_settings(self) -> HardwareSettings:
        return HardwareSettings(
            schema_version=self.defaults.schema_version,
            touchpad_tap=self.defaults.touchpad_tap,
            touchpad_speed=self.defaults.touchpad_speed,
            mouse_speed=self.defaults.mouse_speed,
            natural_scrolling=self.defaults.natural_scrolling,
            resolution=self.defaults.resolution,
            keyboard_layout=self.defaults.keyboard_layout,
            mic_gain=self.defaults.mic_gain,
            disable_while_typing=self.defaults.disable_while_typing,
        )

    def read(self) -> HardwareSettings:
        default = self.default_settings()
        try:
            raw = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return default
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return default
        if not isinstance(raw, dict):
            return default
        try:
            version = _strict_int(
                raw.get("schema_version", self.defaults.schema_version),
                "schema_version",
            )
        except (HardwareSettingsError, TypeError, ValueError):
            return default
        try:
            if version == 1 and self.defaults.schema_version == 2:
                # Explicit v1 → v2 migration: preserve every valid stored
                # value; only the version marker changes and the new field
                # defaults to False (pre-tranche backend behavior).
                settings = HardwareSettings(
                    schema_version=2,
                    touchpad_tap=_strict_bool(
                        raw.get("touchpad_tap", default.touchpad_tap),
                        "touchpad_tap",
                    ),
                    touchpad_speed=self.defaults.validate_speed(
                        float(raw.get("touchpad_speed", default.touchpad_speed)),
                        "touchpad_speed",
                    ),
                    mouse_speed=self.defaults.validate_speed(
                        float(raw.get("mouse_speed", default.mouse_speed)),
                        "mouse_speed",
                    ),
                    natural_scrolling=_strict_bool(
                        raw.get("natural_scrolling", default.natural_scrolling),
                        "natural_scrolling",
                    ),
                    resolution=str(raw.get("resolution", default.resolution)),
                    keyboard_layout=str(
                        raw.get("keyboard_layout", default.keyboard_layout)
                    ),
                    mic_gain=self.defaults.validate_mic_gain(
                        float(raw.get("mic_gain", default.mic_gain))
                    ),
                    disable_while_typing=False,
                )
            elif version == self.defaults.schema_version:
                settings = HardwareSettings(
                    schema_version=version,
                    touchpad_tap=_strict_bool(
                        raw.get("touchpad_tap", default.touchpad_tap), "touchpad_tap"
                    ),
                    touchpad_speed=self.defaults.validate_speed(
                        float(raw.get("touchpad_speed", default.touchpad_speed)),
                        "touchpad_speed",
                    ),
                    mouse_speed=self.defaults.validate_speed(
                        float(raw.get("mouse_speed", default.mouse_speed)), "mouse_speed"
                    ),
                    natural_scrolling=_strict_bool(
                        raw.get("natural_scrolling", default.natural_scrolling),
                        "natural_scrolling",
                    ),
                    resolution=str(raw.get("resolution", default.resolution)),
                    keyboard_layout=str(
                        raw.get("keyboard_layout", default.keyboard_layout)
                    ),
                    mic_gain=self.defaults.validate_mic_gain(
                        float(raw.get("mic_gain", default.mic_gain))
                    ),
                    disable_while_typing=_strict_bool(
                        raw.get(
                            "disable_while_typing",
                            default.disable_while_typing,
                        ),
                        "disable_while_typing",
                    ),
                )
            else:
                return default
            self.validate(settings)
            return settings
        except (HardwareSettingsError, TypeError, ValueError):
            return default

    def update(
        self,
        *,
        touchpad_tap: bool | None = None,
        touchpad_speed: float | None = None,
        mouse_speed: float | None = None,
        natural_scrolling: bool | None = None,
        resolution: str | None = None,
        keyboard_layout: str | None = None,
        mic_gain: float | None = None,
        disable_while_typing: bool | None = None,
        allowed_resolutions: Iterable[str] | None = None,
    ) -> HardwareSettings:
        current = self.read()
        updated = HardwareSettings(
            schema_version=self.defaults.schema_version,
            touchpad_tap=current.touchpad_tap if touchpad_tap is None else touchpad_tap,
            touchpad_speed=(
                current.touchpad_speed
                if touchpad_speed is None
                else self.defaults.validate_speed(touchpad_speed, "touchpad_speed")
            ),
            mouse_speed=(
                current.mouse_speed
                if mouse_speed is None
                else self.defaults.validate_speed(mouse_speed, "mouse_speed")
            ),
            natural_scrolling=(
                current.natural_scrolling
                if natural_scrolling is None
                else natural_scrolling
            ),
            resolution=current.resolution if resolution is None else resolution,
            keyboard_layout=(
                current.keyboard_layout
                if keyboard_layout is None
                else self.defaults.validate_keyboard_layout(keyboard_layout)
            ),
            mic_gain=(
                current.mic_gain
                if mic_gain is None
                else self.defaults.validate_mic_gain(mic_gain)
            ),
            disable_while_typing=(
                current.disable_while_typing
                if disable_while_typing is None
                else disable_while_typing
            ),
        )
        self.validate(updated, allowed_resolutions=allowed_resolutions)
        self._write(updated)
        return updated

    def replace(
        self,
        settings: HardwareSettings,
        *,
        allowed_resolutions: Iterable[str] | None = None,
    ) -> HardwareSettings:
        self.validate(settings, allowed_resolutions=allowed_resolutions)
        self._write(settings)
        return settings

    def reset(self) -> HardwareSettings:
        try:
            self.settings_path.unlink()
        except FileNotFoundError:
            pass
        return self.default_settings()

    def validate(
        self,
        settings: HardwareSettings,
        *,
        allowed_resolutions: Iterable[str] | None = None,
    ) -> None:
        if settings.schema_version != self.defaults.schema_version:
            raise HardwareSettingsError("hardware settings schema does not match platform")
        if not isinstance(settings.touchpad_tap, bool):
            raise HardwareSettingsError("touchpad_tap must be boolean")
        if not isinstance(settings.natural_scrolling, bool):
            raise HardwareSettingsError("natural_scrolling must be boolean")
        if not isinstance(settings.disable_while_typing, bool):
            raise HardwareSettingsError("disable_while_typing must be boolean")
        self.defaults.validate_speed(settings.touchpad_speed, "touchpad_speed")
        self.defaults.validate_speed(settings.mouse_speed, "mouse_speed")
        _validate_resolution_id(settings.resolution)
        self.defaults.validate_keyboard_layout(settings.keyboard_layout)
        self.defaults.validate_mic_gain(settings.mic_gain)
        if allowed_resolutions is not None:
            allowed = {"auto", *allowed_resolutions}
            if settings.resolution not in allowed:
                raise HardwareSettingsError("requested resolution is not supported by this display")

    def version_token(self) -> int:
        try:
            return self.settings_path.stat().st_mtime_ns
        except FileNotFoundError:
            return 0

    def _write(self, settings: HardwareSettings) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            settings.as_json_dict(), sort_keys=True, separators=(",", ":")
        ) + "\n"
        _atomic_write_text(self.settings_path, payload, mode=0o664)


def read_apply_status(path: Path, fallback: HardwareSettings) -> HardwareApplyStatus:
    """Read the watcher status file with backward tolerance.

    Old payloads without ``display_metrics``/``pointer_devices`` parse with
    those fields defaulted (``None``/``()``). Missing, unreadable, corrupt,
    or old-format (non-object) payloads fail soft to the existing
    "not reported yet" status so the Parent health path keeps working.
    Malformed new-field entries degrade to ``None``/``()`` individually and
    never break the rest of the payload. No suitability verdict is read or
    stored here: product policy stays above this layer.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        return HardwareApplyStatus(
            settings=fallback,
            applied=False,
            display_output=None,
            display_modes=(),
            message="Hardware session has not reported yet.",
        )
    if not isinstance(raw, dict):
        return HardwareApplyStatus(
            settings=fallback,
            applied=False,
            display_output=None,
            display_modes=(),
            message="Hardware session has not reported yet.",
        )
    modes: list[DisplayMode] = []
    raw_modes = raw.get("display_modes", [])
    if isinstance(raw_modes, list):
        for raw_mode in raw_modes:
            if not isinstance(raw_mode, dict):
                continue
            try:
                modes.append(
                    DisplayMode(
                        width=int(raw_mode["width"]),
                        height=int(raw_mode["height"]),
                        refresh_hz=(
                            None
                            if raw_mode.get("refresh_hz") is None
                            else float(raw_mode["refresh_hz"])
                        ),
                        preferred=bool(raw_mode.get("preferred", False)),
                        current=bool(raw_mode.get("current", False)),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
    return HardwareApplyStatus(
        settings=fallback,
        applied=bool(raw.get("applied", False)),
        display_output=(
            str(raw["display_output"]) if raw.get("display_output") else None
        ),
        display_modes=tuple(modes),
        message=str(raw.get("message", "")),
        display_metrics=_metrics_from_json_dict(raw.get("display_metrics")),
        pointer_devices=_pointer_devices_from_json(raw.get("pointer_devices")),
    )


def _metrics_to_json_dict(metrics: object) -> dict[str, object] | None:
    """Serialize display metrics to the bounded status shape (T09 contract).

    Shape: ``{"pixel_width": int, "pixel_height": int,
    "physical_size_known": bool, "orientation": str, "source": str,
    "physical_width_mm": float | omitted, "physical_height_mm": float |
    omitted}``. Physical mm appear only when ``physical_size_known`` is
    true. Returns ``None`` when given a non-metrics object.
    """
    pixel_width = getattr(metrics, "pixel_width", None)
    pixel_height = getattr(metrics, "pixel_height", None)
    if (
        isinstance(pixel_width, bool)
        or isinstance(pixel_height, bool)
        or not isinstance(pixel_width, int)
        or not isinstance(pixel_height, int)
    ):
        return None
    known = bool(getattr(metrics, "physical_size_known", False))
    orientation = getattr(metrics, "orientation", "landscape")
    source = getattr(getattr(metrics, "source", None), "value", "unknown")
    payload: dict[str, object] = {
        "pixel_width": pixel_width,
        "pixel_height": pixel_height,
        "physical_size_known": known,
        "orientation": str(orientation),
        "source": str(source),
    }
    if known:
        width_mm = getattr(metrics, "physical_width_mm", None)
        height_mm = getattr(metrics, "physical_height_mm", None)
        if isinstance(width_mm, (int, float)) and isinstance(height_mm, (int, float)):
            payload["physical_width_mm"] = float(width_mm)
            payload["physical_height_mm"] = float(height_mm)
    return payload


def _metrics_from_json_dict(raw: object) -> DisplayMetrics | None:
    """Parse ``display_metrics`` tolerantly; ``None`` when absent/malformed."""
    if not isinstance(raw, dict):
        return None
    pixel_width = raw.get("pixel_width")
    pixel_height = raw.get("pixel_height")
    if (
        isinstance(pixel_width, bool)
        or isinstance(pixel_height, bool)
        or not isinstance(pixel_width, int)
        or not isinstance(pixel_height, int)
        or not 1 <= pixel_width <= _STATUS_MAX_PIXEL_DIMENSION
        or not 1 <= pixel_height <= _STATUS_MAX_PIXEL_DIMENSION
    ):
        return None
    try:
        from .display_metrics import DisplayMetrics, DisplayMetricsSource
    except ImportError:
        return None
    source = DisplayMetricsSource.UNKNOWN
    raw_source = raw.get("source")
    if isinstance(raw_source, str):
        for candidate in DisplayMetricsSource:
            if candidate.value == raw_source:
                source = candidate
                break
    width_mm: float | None = None
    height_mm: float | None = None
    raw_width = raw.get("physical_width_mm")
    raw_height = raw.get("physical_height_mm")
    if isinstance(raw_width, (int, float)) and isinstance(raw_height, (int, float)):
        candidate_width = float(raw_width)
        candidate_height = float(raw_height)
        if (
            _STATUS_MIN_PHYSICAL_MM <= candidate_width <= _STATUS_MAX_PHYSICAL_MM
            and _STATUS_MIN_PHYSICAL_MM <= candidate_height <= _STATUS_MAX_PHYSICAL_MM
        ):
            width_mm = candidate_width
            height_mm = candidate_height
    if width_mm is None or height_mm is None:
        # Never invent dimensions: partial/out-of-range physical degrades
        # to unknown physical size instead of failing the whole payload.
        try:
            return DisplayMetrics(pixel_width, pixel_height)
        except (TypeError, ValueError):
            return None
    try:
        metrics = DisplayMetrics(
            pixel_width,
            pixel_height,
            physical_width_mm=width_mm,
            physical_height_mm=height_mm,
            source=source,
        )
    except (TypeError, ValueError):
        try:
            return DisplayMetrics(pixel_width, pixel_height)
        except (TypeError, ValueError):
            return None
    if not metrics.physical_size_known:
        # A stored UNKNOWN source with physical mm is inconsistent; keep
        # the pixel facts and drop the physical size rather than failing.
        try:
            return DisplayMetrics(pixel_width, pixel_height)
        except (TypeError, ValueError):
            return None
    return metrics


def _pointer_devices_from_json(raw: object) -> tuple[PointerDeviceStatus, ...]:
    """Parse ``pointer_devices`` tolerantly; ``()`` when absent/malformed."""
    if not isinstance(raw, list):
        return ()
    devices: list[PointerDeviceStatus] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        kind = entry.get("kind")
        label = entry.get("label")
        if not isinstance(kind, str) or not isinstance(label, str):
            continue
        kind = kind.strip()[:MAX_STATUS_LABEL_CHARS] or "unknown"
        label = label.strip()[:MAX_STATUS_LABEL_CHARS] or kind.title()
        capabilities = entry.get("capabilities")
        if isinstance(capabilities, dict):
            supports_tap = bool(capabilities.get("supports_tap", False))
            supports_natural = bool(capabilities.get("supports_natural_scrolling", False))
            supports_dwt = bool(capabilities.get("supports_disable_while_typing", False))
            supports_speed = bool(capabilities.get("supports_speed", False))
        else:
            supports_tap = bool(entry.get("supports_tap", False))
            supports_natural = bool(entry.get("supports_natural_scrolling", False))
            supports_dwt = bool(entry.get("supports_disable_while_typing", False))
            supports_speed = bool(entry.get("supports_speed", False))
        devices.append(
            PointerDeviceStatus(
                kind=kind,
                label=label,
                supports_tap=supports_tap,
                supports_natural_scrolling=supports_natural,
                supports_disable_while_typing=supports_dwt,
                supports_speed=supports_speed,
            )
        )
        if len(devices) >= MAX_STATUS_POINTER_DEVICES:
            break
    return tuple(devices)


def _strict_bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise HardwareSettingsError(f"{name} must be boolean")
    return value


def _strict_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise HardwareSettingsError(f"{name} must be integer")
    return value


def _validate_resolution_id(value: str) -> None:
    if value == "auto":
        return
    parts = value.lower().split("x")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise HardwareSettingsError("resolution must be 'auto' or WIDTHxHEIGHT")
    width, height = (int(part) for part in parts)
    if width < 320 or height < 240 or width > 7680 or height > 4320:
        raise HardwareSettingsError("resolution is outside the supported safety range")


def _atomic_write_text(path: Path, payload: str, *, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        temporary.replace(path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
